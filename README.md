 ☄️ Meteor Predictor


>so basically this is not just a metoer calender ,it tells you the metoer trajectory (best viewing angle) ,visbilty according to proximity and best time of the day to watch the shower .

---

## why is it important

\most of the metoer calander dont take in parameter like pollution ,aqi and and opaqe sky 



This app calculaates your **actual visible ZHR** by combining:

- **Radiant geometry** — where the shower's origin point sits in *your* sky at *your* latitude
- **Sky darkness** — auto-detected from the Falchi 2016 light pollution atlas via VIIRS satellite data, no input needed
- **Cloud cover** — 7-day hourly forecast from Open-Meteo
- **Moon phase** — calculated from first principles (Meeus, *Astronomical Algorithms*)
- **Air quality (AQI)** — atmospheric transparency from Open-Meteo Air Quality
- **Best viewing window** — the consecutive hours where cloud cover drops and the radiant is above the horizon

The formula is the IMO (International Meteor Organization) standard:

```
ZHR_visible = ZHR × sin(radiant_altitude) × r^(lm − 6.5) × (1 − cloud_fraction)
```

Where `r` is the population index and `lm` is your effective limiting magnitude after accounting for light pollution, moonlight, and aerosols.

---

## Zero API keys required

| Service | Used for | Cost |
|---|---|---|
| [Nominatim (OpenStreetMap)](https://nominatim.openstreetmap.org) | Text → coordinates | Free, no key |
| [lightpollutionmap.info](https://www.lightpollutionmap.info) | Sky darkness from satellite | Free, no key |
| [Open-Meteo](https://open-meteo.com) | Cloud cover + AQI | Free, no key |

---

## Setup on your computer

**Requirements:** Python 3.10 or higher

**1. Download and unzip the project**

```
meteor-predictor/
├── app.py
├── astro.py
├── light_pollution.py
├── showers.py
├── requirements.txt
├── Procfile
├── vercel.json
└── templates/
    └── index.html
```

**2. Install dependencies**

```bash
pip install flask requests Pillow
```

**3. Run**

```bash
python app.py
```

**4. Open in browser**

```
http://localhost:5000
```

That's it. Type any city name, hit Search, then Predict.

---

## Deploy to Vercel (free hosting)

Vercel hosts Python/Flask apps for free with a public URL you can share.

**Step 1 — Push your code to GitHub**

```bash
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/meteor-predictor.git
git push -u origin main
```

> If you don't have a GitHub account, create one at [github.com](https://github.com). It's free.

**Step 2 — Connect to Vercel**

1. Go to [vercel.com](https://vercel.com) and sign up with your GitHub account
2. Click **Add New Project**
3. Select your `meteor-predictor` repository
4. Leave all settings as default — Vercel auto-detects Python
5. Click **Deploy**

**Step 3 — Get your live URL**

After ~1 minute, Vercel gives you a public URL like:

```
https://meteor-predictor-yourname.vercel.app
```

That's your live demo link. Share it anywhere.

**Step 4 — Update your deployment**

Whenever you make changes:

```bash
git add .
git commit -m "describe your change"
git push
```

Vercel auto-deploys on every push. No manual steps.

---

## File overview

| File | What it does |
|---|---|
| `app.py` | Flask server — all routes (`/api/geocode`, `/api/predict`, `/api/calendar`) |
| `astro.py` | Pure math — Julian dates, sidereal time, radiant altitude/azimuth, ZHR formula, moon phase |
| `light_pollution.py` | Fetches Bortle class from VIIRS satellite tiles. Falls back to place-type estimate if tiles unavailable |
| `showers.py` | Database of 9 major showers with IMO data — ZHR, population index, radiant coordinates, parent bodies |
| `templates/index.html` | Full frontend — search, sky panel, shower cards, compass, Chart.js hourly chart, calendar export |

---

## Data sources & references

- **Meteor shower data:** IMO Working List of Meteor Showers — [imo.net](https://www.imo.net/resources/calendar/)
- **ZHR formula:** IMO Meteor Observation Manual v1.4
- **Light pollution:** Falchi F. et al. (2016). *The new world atlas of artificial night sky brightness.* Science Advances 2(6). DOI: 10.1126/sciadv.1600377
- **Bortle scale:** Bortle J. (2001). *Gauging Light Pollution.* Sky & Telescope 101(2)
- **Astronomical algorithms:** Meeus J. (1998). *Astronomical Algorithms*, 2nd ed. Willmann-Bell
- **Limiting magnitude:** Schaefer B.E. (1990). *Telescopic Limiting Magnitudes.* PASP 102

---

## Built for Hack Club Stardance 2026

*"Space is big. Really big. You just won't believe how vastly, hugely, mind-bogglingly big it is."*  
— Douglas Adams
