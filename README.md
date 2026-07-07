# ☄️ Meteor Predictor

tell you how  many metoer  you'll actually see on a particular day, not the theoretical maximum.
it accounts for your sky bright, cloud cover, air quality , moon phase , and where the shower actually sits in your sky .

(it was built for Hack Club Stardance 2026)

**Live demo: [where-the-meteor-at.vercel.app](https://where-the-meteor-at.vercel.app)**

---

## how it works

most apps show ZHR- a number that assumes you're on the dark mountain with perfect skies , nobody ever sees it like that (not always) , this app run the IMO standard formula :

```
VisibleZHR= ZHR × sin(radiant_altitude) × r^(lm − 6.5) × (1 − cloud_fraction)
```

sky darkness is pulled automatically from the Falchi 2016 light pollution atlas via VIIRS satellite data(kinda outdated).

---

##setup

required Python 3.10+

```
pip install flask request Pillow
python app.py
```

then open 'http:localhost:5000',type your city , hit predict.

---

## deploy to vercel

1. push code to github or clone the repo
2. go to vercel.com, connect 
3. done - live url 

the `vercel.json` is alredy pre configured and flask will run on the server directly

---

##data source 


- meteor showers — [IMO Working List](https://www.imo.net/resources/calendar/)
- sky darkness — Falchi et al. (2016) via [lightpollutionmap.info](https://www.lightpollutionmap.info)
- weather + AQI — [Open-Meteo](https://open-meteo.com)
- geocoding — [Nominatim / OpenStreetMap](https://nominatim.openstreetmap.org)
- math — Meeus, *Astronomical Algorithms* (1998)

## ai usage

built with Claude (Anthropic) as a coding tool. concept, features, and direction were my own.