// ── State ──────────────────────────────────────────────────────────────────────
let currentLat = null;
let currentLon = null;

// ── Location Search ────────────────────────────────────────────────────────────
async function searchLocation () {
  const query = document.getElementById('location-input').value.trim();
  if (!query) { showError("Enter a location to search."); return; }

  clearError();
  setStatus("🔍 Searching…");

  try {
    const resp = await fetch(`/api/geocode?q=${encodeURIComponent(query)}`);
    const data = await resp.json();

    if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);

    setLocation(data.lat, data.lon);
    document.getElementById('location-input').value = data.name;
    setStatus(`✓ Found: ${data.name}`);

  } catch (e) {
    setStatus("");
    showError(`Location search failed: ${e.message}`);
  }
}

function autoDetect () {
  if (!navigator.geolocation) { showError("Geolocation not supported."); return; }
  setStatus("📡 Locating…");
  navigator.geolocation.getCurrentPosition(
    pos => {
      setLocation(pos.coords.latitude, pos.coords.longitude);
      setStatus("✓ Location detected");
    },
    () => { setStatus(""); showError("Location access denied."); }
  );
}

function setLocation (lat, lon) {
  currentLat = lat;
  currentLon = lon;
  document.getElementById('lat-display').textContent = lat.toFixed(4);
  document.getElementById('lon-display').textContent = lon.toFixed(4);
  document.getElementById('coords-row').style.display = 'flex';
}

// ── Main Prediction ────────────────────────────────────────────────────────────
async function runPrediction () {
  if (currentLat === null || currentLon === null) {
    showError("Search for your location first.");
    return;
  }

  clearError();
  setStatus("⏳ Detecting sky darkness from satellite + fetching forecast…");
  document.getElementById('predict-btn').disabled = true;
  document.getElementById('sky-panel').style.display = 'none';

  try {
    const resp = await fetch('/api/predict', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ lat: currentLat, lon: currentLon }),
    });
    if (!resp.ok) { const e = await resp.json(); throw new Error(e.error || `HTTP ${resp.status}`); }

    const data = await resp.json();

    showSkyPanel(data.sky);
    setStatus(`✓ Bortle ${data.sky.bortle} detected · ${data.showers.length} showers calculated`);
    renderResults(data.showers);

  } catch (e) {
    setStatus("");
    showError(`Error: ${e.message}`);
  } finally {
    document.getElementById('predict-btn').disabled = false;
  }
}

// ── Sky Panel ──────────────────────────────────────────────────────────────────
function showSkyPanel (sky) {
  document.getElementById('sky-panel').style.display  = 'block';
  document.getElementById('sky-bortle').textContent   = `Bortle ${sky.bortle} · SQM ${sky.sqm} mag/arcsec²`;
  document.getElementById('sky-desc').textContent     = sky.description;
  document.getElementById('sky-source').textContent   = `Source: ${sky.source}`;

  const errEl = document.getElementById('sky-error');
  if (sky.error) {
    errEl.textContent   = `⚠️ ${sky.error} — using Bortle 5 default`;
    errEl.style.display = 'block';
  } else {
    errEl.style.display = 'none';
  }
}

// ── Render Cards ───────────────────────────────────────────────────────────────
const charts = {};

function renderResults (showers) {
  const container = document.getElementById('results');
  container.innerHTML = '';
  Object.values(charts).forEach(c => c.destroy());
  for (const k in charts) delete charts[k];

  showers.forEach(s => {
    const vzhr     = s.best_visible_zhr;
    const vClass   = vzhr >= 30 ? 'green' : vzhr >= 10 ? 'yellow' : 'red';
    const peakIn   = s.days_until_peak === 0 ? 'Tonight'
                   : s.days_until_peak === 1 ? 'Tomorrow'
                   : `${s.days_until_peak}d`;
    const aqiColor = aqiToColor(s.current_aqi);

    const bwHtml = s.best_window
      ? `<div class="best-window">
           <div class="bw-icon">🟢</div>
           <div>
             <div class="bw-title">Best clear viewing window</div>
             <div class="bw-times">${s.best_window.start} → ${s.best_window.end}</div>
             <div class="bw-meta">${s.best_window.duration_hrs}h · avg ${s.best_window.avg_zhr} meteors/hr · ~${s.best_window.avg_cloud}% cloud</div>
           </div>
         </div>`
      : `<div class="no-window">⚠️ No clear window in forecast range — check back closer to peak.</div>`;

    const card = document.createElement('div');
    card.className = 'shower-card';
    card.innerHTML = `
      <div class="card-header" onclick="toggleCard('${s.code}')">
        <div class="card-left">
          <span class="shower-code">${s.code}</span>
          <div>
            <div class="shower-name">${s.name}</div>
            <div class="shower-sub">Peak: ${s.peak_date} · ${peakIn}</div>
          </div>
        </div>
        <div class="card-right">
          <div class="stat">
            <div class="val ${vClass}">${vzhr}</div>
            <div class="unit">meteors/hr (you)</div>
          </div>
          <div class="stat">
            <div class="val" style="color:var(--Muted);font-size:14px">${s.max_zhr}</div>
            <div class="unit">theoretical max</div>
          </div>
          <div class="rating-badge">${s.rating.emoji} ${s.rating.text}</div>
          <span class="chevron" id="chev-${s.code}">▼</span>
        </div>
      </div>
      <div class="card-detail" id="detail-${s.code}">
        <div class="detail-meta">
          <div class="meta-item">
            <div class="label">Best hour (UTC)</div>
            <div class="value">${s.best_hour}</div>
          </div>
          <div class="meta-item">
            <div class="label">Radiant altitude</div>
            <div class="value">${s.best_radiant_alt}°</div>
          </div>
          <div class="meta-item">
            <div class="label">Which way to face</div>
            <div class="value">
              <div class="compass-wrap">
                <div class="compass">
                  <span class="c-lbl n">N</span>
                  <span class="c-lbl s">S</span>
                  <span class="c-lbl e">E</span>
                  <span class="c-lbl w">W</span>
                  <div class="c-needle" style="transform:translateX(-50%) rotate(${s.face_az}deg)"></div>
                  <div class="c-dot"></div>
                </div>
                <div class="compass-text">${s.face_dir} · ${s.face_az}°</div>
              </div>
            </div>
          </div>
          <div class="meta-item">
            <div class="label">Entry speed</div>
            <div class="value">${s.speed_kmps} km/s</div>
          </div>
          <div class="meta-item">
            <div class="label">AQI (now)</div>
            <div class="value">
              <span class="aqi-dot" style="background:${aqiColor}"></span>
              ${s.current_aqi ?? '—'} · ${s.current_aqi_label}
            </div>
          </div>
          <div class="meta-item">
            <div class="label">Parent body</div>
            <div class="value" style="font-size:11px;line-height:1.4">${s.parent_body}</div>
          </div>
        </div>
        <div class="window-wrap">${bwHtml}</div>
        <div class="chart-wrap">
          <canvas id="chart-${s.code}"></canvas>
        </div>
        <div class="shower-notes">${s.notes}</div>
      </div>
    `;
    container.appendChild(card);
  });

  window._showers = {};
  showers.forEach(s => { window._showers[s.code] = s; });
  document.getElementById('calendar-row').style.display = 'block';
}

function toggleCard (code) {
  const detail  = document.getElementById(`detail-${code}`);
  const chev    = document.getElementById(`chev-${code}`);
  const opening = !detail.classList.contains('open');
  detail.classList.toggle('open');
  chev.classList.toggle('open');
  if (opening) renderChart(code);
}

// ── Chart ──────────────────────────────────────────────────────────────────────
function renderChart (code) {
  if (charts[code]) charts[code].destroy();

  const s      = window._showers[code];
  const hourly = s.hourly_data;
  const labels = hourly.map(h => h.hour_label.slice(-8));
  const vzhr   = hourly.map(h => h.visible_zhr);
  const cloud  = hourly.map(h => h.cloud_pct ?? 0);
  const aqi    = hourly.map(h => h.aqi ?? 0);

  const ctx = document.getElementById(`chart-${code}`).getContext('2d');

  charts[code] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Visible ZHR',
          data:  vzhr,
          backgroundColor: vzhr.map(v =>
            v >= 30 ? 'rgba(61,220,132,0.75)'
            : v >= 10 ? 'rgba(245,197,66,0.75)'
            : 'rgba(124,108,240,0.55)'
          ),
          borderColor: 'transparent', borderRadius: 4, yAxisID: 'y', order: 1,
        },
        {
          label: 'Cloud Cover %', data: cloud, type: 'line',
          borderColor: 'rgba(150,150,220,0.55)', backgroundColor: 'rgba(150,150,220,0.07)',
          borderWidth: 1.5, borderDash: [4,3], pointRadius: 0, fill: true,
          yAxisID: 'y2', order: 0, tension: 0.3,
        },
        {
          label: 'AQI', data: aqi, type: 'line',
          borderColor: 'rgba(255,140,80,0.65)', backgroundColor: 'transparent',
          borderWidth: 1.5, pointRadius: 0, fill: false,
          yAxisID: 'y2', order: 0, tension: 0.3,
        },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#7070a0', font: { size: 11 }, boxWidth: 10 } },
        tooltip: {
          backgroundColor: '#12121e', borderColor: '#2a2a3e', borderWidth: 1,
          titleColor: '#d8d8f0', bodyColor: '#7070a0',
          callbacks: {
            afterBody: (items) => {
              const h = hourly[items[0].dataIndex];
              return [
                `  Radiant: ${h.radiant_alt_deg}° alt · ${h.radiant_cardinal} (${h.radiant_az_deg}°)`,
                `  Moon:    ${h.moon_pct}% illuminated`,
                `  Eff. lm: ${h.eff_lm}`,
              ];
            },
          },
        },
      },
      scales: {
        x:  { ticks: { color: '#555580', font: { size: 10, family: 'Courier New' }, maxRotation: 45 }, grid: { color: '#181828' } },
        y:  { position: 'left',  title: { display: true, text: 'Meteors / hr',   color: '#555580', font: { size: 11 } }, ticks: { color: '#555580' }, grid: { color: '#181828' }, min: 0 },
        y2: { position: 'right', title: { display: true, text: 'Cloud % / AQI', color: '#555580', font: { size: 11 } }, ticks: { color: '#555580' }, grid: { display: false }, min: 0, max: 100 },
      },
    },
  });
}

// ── Calendar Export ────────────────────────────────────────────────────────────
async function exportCalendar () {
  const showers = Object.values(window._showers || {});
  if (!showers.length) { showError("Run a prediction first."); return; }

  try {
    const resp = await fetch('/api/calendar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ showers }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const blob = await resp.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'meteor-showers-2026.ics';
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
    setStatus("✓ Calendar exported");
  } catch (e) {
    showError(`Calendar export failed: ${e.message}`);
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function aqiToColor (aqi) {
  if (aqi == null) return '#606080';
  if (aqi <= 20)   return '#3ddc84';
  if (aqi <= 40)   return '#a8e063';
  if (aqi <= 60)   return '#f5c542';
  if (aqi <= 80)   return '#ff9966';
  if (aqi <= 100)  return '#ff5c5c';
  return '#cc44cc';
}

function setStatus  (msg) { document.getElementById('status').textContent = msg; }
function showError  (msg) { const e = document.getElementById('error-msg'); e.textContent = msg; e.style.display = 'block'; }
function clearError ()    { document.getElementById('error-msg').style.display = 'none'; }

// Enter key on search box
document.getElementById('location-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') searchLocation();
});
