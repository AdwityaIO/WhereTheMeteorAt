# ☄️ Meteor Predictor

tells you how many meteors you'll actually see tonight — not the theoretical maximum. accounts for your sky brightness, cloud cover, air quality, moon phase, and where the shower actually sits in your sky.

built for Hack Club Stardance 2026.

🌐 **Live demo: [where-the-meteor-at.vercel.app](https://where-the-meteor-at.vercel.app/)**

---

## how it works

most apps show ZHR — a number that assumes you're on a dark mountain with perfect skies. nobody ever sees that. this app runs the IMO standard formula:

```
ZHR_visible = ZHR × sin(radiant_altitude) × r^(lm − 6.5) × (1 − cloud_fraction)
```

sky darkness is pulled automatically from the Falchi 2016 light pollution atlas via VIIRS satellite data. no manual input needed.

---

## setup

you need Python 3.10+

```bash
pip install flask requests Pillow
python app.py
```

then open `http://localhost:5000`, type your city, hit predict.

---

## deploy to vercel

1. push code to github
2. go to vercel.com, connect your repo, hit deploy
3. done — live url in about a minute

the `vercel.json` is already in the project so vercel knows what to do.

---

## data sources

- meteor showers — [IMO Working List](https://www.imo.net/resources/calendar/)
- sky darkness — Falchi et al. (2016) via [lightpollutionmap.info](https://www.lightpollutionmap.info)
- weather + AQI — [Open-Meteo](https://open-meteo.com)
- geocoding — [Nominatim / OpenStreetMap](https://nominatim.openstreetmap.org)
- math — Meeus, *Astronomical Algorithms* (1998)

zero API keys required.

---

## ai usage

built with Claude (Anthropic) as a coding tool. concept, features, and direction were my own.
