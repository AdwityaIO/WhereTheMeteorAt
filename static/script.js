let currentLat = null, currentLon = null, currentPlaceData = null;
const charts = {};

async function searchLocation() {
  const q = document.getElementById('location-input').value.trim();
  if (!q) { showErr("Enter a location."); return; }
  clearErr(); setSt("Searching…");
  try {
    const r = await fetch(`/api/geocode?q=${encodeURIComponent(q)}`);
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || `HTTP ${r.status}`);
    setLoc(d.lat, d.lon, d.place_data);
    document.getElementById('location-input').value = d.name;
    setSt("Found.");
  } catch(e) { setSt(""); showErr(e.message); }
}

function autoDetect() {
  if (!navigator.geolocation) { showErr("Geolocation not supported."); return; }
  setSt("Locating…");
  navigator.geolocation.getCurrentPosition(
    p => { setLoc(p.coords.latitude, p.coords.longitude, null); setSt("Located."); },
    () => { setSt(""); showErr("Location access denied."); }
  );
}

function setLoc(lat, lon, pd) {
  currentLat = lat; currentLon = lon; currentPlaceData = pd || null;
  document.getElementById('lat-display').textContent = lat.toFixed(4);
  document.getElementById('lon-display').textContent = lon.toFixed(4);
  document.getElementById('coords-row').classList.add('on');
}

async function runPrediction() {
  if (currentLat === null) { showErr("Set a location first."); return; }
  clearErr(); setSt("Fetching satellite data + forecast…");
  document.getElementById('predict-btn').disabled = true;
  document.getElementById('sky-panel').classList.remove('on');
  try {
    const r = await fetch('/api/predict', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ lat: currentLat, lon: currentLon, place_data: currentPlaceData }),
    });
    if (!r.ok) { const e = await r.json(); throw new Error(e.error || `HTTP ${r.status}`); }
    const d = await r.json();
    renderSky(d.sky);
    setSt(`Bortle ${d.sky.bortle} · ${d.showers.length} showers`);
    renderShowers(d.showers);
  } catch(e) { setSt(""); showErr(e.message); }
  finally { document.getElementById('predict-btn').disabled = false; }
}

function renderSky(sky) {
  document.getElementById('sky-panel').classList.add('on');
  document.getElementById('sky-bortle').textContent = `Bortle ${sky.bortle} · SQM ${sky.sqm}`;
  document.getElementById('sky-desc').textContent   = sky.description;
  document.getElementById('sky-source').textContent = sky.source;
  const e = document.getElementById('sky-error');
  if (sky.error) { e.textContent = sky.error; e.style.display = 'block'; }
  else { e.style.display = 'none'; }
}

function renderShowers(showers) {
  const el = document.getElementById('content');
  el.innerHTML = '';
  Object.values(charts).forEach(c => c.destroy());
  for (const k in charts) delete charts[k];

  showers.forEach((s, i) => {
    const vzhr  = s.best_visible_zhr;
    const ncls  = vzhr >= 30 ? 'hot' : vzhr >= 8 ? 'warm' : 'cold';
    const peakIn = s.days_until_peak === 0 ? 'tonight'
                 : s.days_until_peak === 1 ? 'tomorrow'
                 : `in ${s.days_until_peak}d`;
    const aqiC  = aqiCol(s.current_aqi);

    const bwHtml = s.best_window
      ? `<div class="win-bar on">
           <div class="win-label">Clear viewing window</div>
           <div class="win-times">${s.best_window.start} → ${s.best_window.end}</div>
           <div class="win-meta">${s.best_window.duration_hrs}h · avg ${s.best_window.avg_zhr}/hr · ${s.best_window.avg_cloud}% cloud</div>
         </div>`
      : `<div class="no-win">No clear window in forecast range.</div>`;

    const row = document.createElement('div');
    row.className = 'shower-row';
    row.innerHTML = `
      <div class="row-head" onclick="toggleRow('${s.code}')">
        <div class="row-idx">${String(i+1).padStart(2,'0')}</div>
        <div>
          <div class="row-name">${s.name}</div>
          <div class="row-sub">Peak ${s.peak_date} · ${peakIn} · ${s.speed_kmps} km/s</div>
        </div>
        <div class="row-num-block">
          <div class="row-num ${ncls}">${vzhr}</div>
          <div class="row-num-sub">meteors/hr (you) · max ${s.max_zhr}</div>
        </div>
        <div class="row-badge">${s.rating.emoji} ${s.rating.text}</div>
      </div>
      <div class="row-detail" id="detail-${s.code}">
        <div class="data-tape">
          <div class="t-item">
            <div class="t-key">Best hour UTC</div>
            <div class="t-val">${s.best_hour}</div>
          </div>
          <div class="t-item">
            <div class="t-key">Radiant altitude</div>
            <div class="t-val">${s.best_radiant_alt}°</div>
          </div>
          <div class="t-item">
            <div class="t-key">Face direction</div>
            <div class="t-val">
              <div class="compass-wrap">
                <div class="compass">
                  <span class="c-lbl n">N</span><span class="c-lbl s">S</span>
                  <span class="c-lbl e">E</span><span class="c-lbl w">W</span>
                  <div class="c-needle" style="transform:translateX(-50%) rotate(${s.face_az}deg)"></div>
                  <div class="c-dot"></div>
                </div>
                <div class="c-dir">${s.face_dir} ${s.face_az}°</div>
              </div>
            </div>
          </div>
          <div class="t-item">
            <div class="t-key">AQI now</div>
            <div class="t-val">
              <span class="aqi-dot" style="background:${aqiC}"></span>
              ${s.current_aqi ?? '—'} <small>${s.current_aqi_label}</small>
            </div>
          </div>
          <div class="t-item">
            <div class="t-key">Parent body</div>
            <div class="t-val" style="font-size:12px;line-height:1.4;max-width:26ch">${s.parent_body}</div>
          </div>
        </div>
        ${bwHtml}
        <div class="chart-zone"><canvas id="chart-${s.code}"></canvas></div>
        <div class="row-notes">${s.notes}</div>
      </div>`;
    el.appendChild(row);
  });

  window._showers = {};
  showers.forEach(s => { window._showers[s.code] = s; });
  document.getElementById('cal-btn').style.display = 'block';
}

function toggleRow(code) {
  const d = document.getElementById(`detail-${code}`);
  const opening = !d.classList.contains('open');
  d.classList.toggle('open');
  if (opening) renderChart(code);
}

function renderChart(code) {
  if (charts[code]) charts[code].destroy();
  const s = window._showers[code], h = s.hourly_data;
  const labels = h.map(x => x.hour_label.slice(-8));
  const vzhr   = h.map(x => x.visible_zhr);
  const cloud  = h.map(x => x.cloud_pct ?? 0);
  const aqi    = h.map(x => x.aqi ?? 0);
  const ctx    = document.getElementById(`chart-${code}`).getContext('2d');
  charts[code] = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets: [
      { label: 'Visible ZHR', data: vzhr,
        backgroundColor: vzhr.map(v => v>=30?'rgba(232,53,10,0.75)':v>=8?'rgba(176,112,16,0.65)':'rgba(13,13,13,0.18)'),
        borderColor: 'transparent', borderRadius: 0, yAxisID: 'y', order: 1 },
      { label: 'Cloud %', data: cloud, type: 'line',
        borderColor: 'rgba(13,13,13,0.25)', backgroundColor: 'rgba(13,13,13,0.04)',
        borderWidth: 1, borderDash: [3,3], pointRadius: 0, fill: true, yAxisID: 'y2', order: 0, tension: 0.3 },
      { label: 'AQI', data: aqi, type: 'line',
        borderColor: 'rgba(232,53,10,0.4)', backgroundColor: 'transparent',
        borderWidth: 1, pointRadius: 0, fill: false, yAxisID: 'y2', order: 0, tension: 0.3 },
    ]},
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color:'#6a6258', font:{size:11,family:'JetBrains Mono'}, boxWidth:10 } },
        tooltip: {
          backgroundColor:'#0d0d0d', borderColor:'rgba(13,13,13,0.2)', borderWidth:1,
          titleColor:'#f2ede4', bodyColor:'#c8c0b0',
          titleFont:{family:'JetBrains Mono',size:11}, bodyFont:{family:'JetBrains Mono',size:11},
          callbacks: { afterBody: items => {
            const x = h[items[0].dataIndex];
            return [`  radiant ${x.radiant_alt_deg}° · ${x.radiant_cardinal}`, `  moon ${x.moon_pct}% · lm ${x.eff_lm}`];
          }},
        },
      },
      scales: {
        x:  { ticks:{color:'#6a6258',font:{size:10,family:'JetBrains Mono'},maxRotation:45}, grid:{color:'rgba(13,13,13,0.07)'} },
        y:  { position:'left',  title:{display:true,text:'meteors/hr',color:'#6a6258',font:{size:10,family:'JetBrains Mono'}}, ticks:{color:'#6a6258',font:{family:'JetBrains Mono',size:10}}, grid:{color:'rgba(13,13,13,0.07)'}, min:0 },
        y2: { position:'right', title:{display:true,text:'cloud%/AQI',color:'#6a6258',font:{size:10,family:'JetBrains Mono'}}, ticks:{color:'#6a6258',font:{family:'JetBrains Mono',size:10}}, grid:{display:false}, min:0, max:100 },
      },
    },
  });
}

async function exportCalendar() {
  const showers = Object.values(window._showers || {});
  if (!showers.length) return;
  try {
    const r = await fetch('/api/calendar', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({showers}),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const blob = await r.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'meteor-showers-2026.ics';
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
    setSt("Calendar exported.");
  } catch(e) { showErr(e.message); }
}

function aqiCol(v) {
  if (!v)    return '#c8c0b0';
  if (v<=20) return '#2d8c4e';
  if (v<=40) return '#6aaa3a';
  if (v<=60) return '#d4a017';
  if (v<=80) return '#e07010';
  if (v<=100) return '#e8350a';
  return '#7a007a';
}

function setSt(m)   { document.getElementById('status').textContent  = m; }
function showErr(m) { const e=document.getElementById('err-msg'); e.textContent=m; e.style.display='block'; }
function clearErr() { document.getElementById('err-msg').style.display='none'; }

document.getElementById('location-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') searchLocation();
});
