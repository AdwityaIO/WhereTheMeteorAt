// 1. Core Astronomical Database
const meteorDatabase = {
    "Orionids": {
        peak: "October 21–22",
        zhr: 20,
        origin: "Comet 1P/Halley",
        radiant: "Orion",
        desc: "Known for producing fast, bright meteors that leave persistent trains."
    },
    "Leonids": {
        peak: "November 17–18",
        zhr: 15,
        origin: "Comet 55P/Tempel-Tuttle",
        radiant: "Leo",
        desc: "Famous for historical meteor storms, though typical years are modest."
    },
    "Geminids": {
        peak: "December 13–14",
        zhr: 120,
        origin: "Asteroid 3200 Phaethon",
        radiant: "Gemini",
        desc: "One of the most reliable and intense annual showers, offering multicolored streaks."
    },
    "Ursids": {
        peak: "December 21–22",
        zhr: 10,
        origin: "Comet 8P/Tuttle",
        radiant: "Ursa Minor",
        desc: "A low-intensity winter shower surrounding the celestial north pole."
    },
    "Quadrantids": {
        peak: "January 3–4",
        zhr: 120,
        origin: "Asteroid 2003 EH1",
        radiant: "Boötes",
        desc: "Features bright fireballs but has an extremely sharp, short peak window."
    },
    "Lyrids": {
        peak: "April 21–22",
        zhr: 18,
        origin: "Comet Thatcher",
        radiant: "Lyra",
        desc: "One of the oldest recorded observations, active for over 2,500 years."
    },
    "Eta Aquariids": {
        peak: "May 5–6",
        zhr: 50,
        origin: "Comet 1P/Halley",
        radiant: "Aquarius",
        desc: "Best viewed from southern latitudes, creating long, sweeping trails."
    },
    "Delta Aquariids": {
        peak: "July 30–31",
        zhr: 20,
        origin: "Comet 96P/Machholz",
        radiant: "Aquarius",
        desc: "A steady shower that prepares observers for the peak summer season."
    },
    "Perseids": {
        peak: "August 12–13",
        zhr: 100,
        origin: "Comet 109P/Swift-Tuttle",
        radiant: "Perseus",
        desc: "Widely regarded as the best summer meteor shower due to warm night conditions."
    }
};

// 2. DOM Elements Selection Reference Variables
const cards = document.querySelectorAll('.info-card');
const previewDetails = document.getElementById('preview-details');
const previewTitle = document.getElementById('preview-title');
let meteorChartInstance = null; // Stores Chart.js reference to destroy/redraw properly

// 3. Attach Global Event Listeners to Layout Cards
cards.forEach(card => {
    card.addEventListener('click', () => {
        // Remove 'active' selection styling from all cards
        cards.forEach(c => c.classList.remove('active-card'));

        // Add selection styling highlight to clicked item
        card.classList.add('active-card');

        const meteorName = card.getAttribute('data-card');
        updateMeteorPreview(meteorName);
    });
});

// 4. Update Interface Elements & Graphic Displays
function updateMeteorPreview(meteorName) {
    const data = meteorDatabase[meteorName];

    if (data) {
        // Unhide the panel block container wrapper
        previewDetails.style.display = "block";

        // Inject plain text parameters safely into localized IDs
        previewTitle.innerText = meteorName;
        document.getElementById('meteor-peak').innerText = data.peak;
        document.getElementById('meteor-zhr').innerText = data.zhr;
        document.getElementById('meteor-origin').innerText = data.origin;
        document.getElementById('meteor-radiant').innerText = data.radiant;
        document.getElementById('meteor-desc').innerText = data.desc;

        // Render data visualization graph
        renderMeteorChart(meteorName, data.zhr);
    } else {
        previewTitle.innerText = "Select a meteor shower above";
        previewDetails.style.display = "none";
    }
}

// 5. Generate Dynamic Data Visualization via Chart.js
function renderMeteorChart(label, value) {
    const ctx = document.getElementById('meteorChart').getContext('2d');

    // Wipe old instances to prevent chart overlap artifact bugs during viewport updates
    if (meteorChartInstance) {
        meteorChartInstance.destroy();
    }

    // Draw a comparative single bar vs average max limit
    meteorChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [label, 'Benchmark Max'],
            datasets: [{
                label: 'ZHR Intensity Comparison',
                data: [value, 120],
                backgroundColor: ['rgba(84, 110, 238, 0.7)', 'rgba(255, 255, 255, 0.1)'],
                borderColor: ['#546eee', '#444'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 150,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#888' }
                },
                x: {
                    ticks: { color: '#eee' }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}
