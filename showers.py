"""
Meteor Shower Database
======================
Source: IMO Working List of Meteor Showers (https://www.imo.net/resources/calendar/)
        AMS (American Meteor Society) annual observer reports
        NASA Meteor Watch program data

ZHR = Zenithal Hourly Rate: theoretical meteors/hour under perfect conditions.
population_index (r): lower = more bright meteors.
speed: atmospheric entry velocity in km/s (KE ∝ v²).
"""

METEOR_SHOWERS = [
    {
        "name": "Quadrantids",
        "code": "QUA",
        "peak_month": 1, "peak_day": 3,
        "radiant_ra": 230.1, "radiant_dec": 48.5,
        "zhr": 120, "population_index": 2.1, "speed": 41,
        "parent_body": "Asteroid 2003 EH1 (likely extinct comet, possibly Machholz)",
        "notes": "Peak window is brutally narrow — about 6 hours. Miss it and you wait a year. Northern hemisphere only.",
    },
    {
        "name": "Lyrids",
        "code": "LYR",
        "peak_month": 4, "peak_day": 22,
        "radiant_ra": 271.4, "radiant_dec": 33.6,
        "zhr": 18, "population_index": 2.1, "speed": 49,
        "parent_body": "Comet C/1861 G1 Thatcher (orbital period: ~415 years)",
        "notes": "Oldest recorded meteor shower. Chinese astronomers documented it in 687 BC. Occasional outburst years push ZHR to ~100.",
    },
    {
        "name": "Eta Aquariids",
        "code": "ETA",
        "peak_month": 5, "peak_day": 6,
        "radiant_ra": 338.0, "radiant_dec": -1.0,
        "zhr": 50, "population_index": 2.4, "speed": 66,
        "parent_body": "Comet 1P/Halley (outbound debris trail — Halley's first gift of the year)",
        "notes": "Best from southern hemisphere where radiant rises much higher.",
    },
    {
        "name": "Delta Aquariids",
        "code": "SDA",
        "peak_month": 7, "peak_day": 30,
        "radiant_ra": 333.0, "radiant_dec": -16.0,
        "zhr": 25, "population_index": 3.2, "speed": 41,
        "parent_body": "Possibly Comet 96P/Machholz (disputed since 2021 orbital analysis)",
        "notes": "Broad peak — good for several nights either side. Often confused with Perseids since they overlap in late July.",
    },
    {
        "name": "Perseids",
        "code": "PER",
        "peak_month": 8, "peak_day": 12,
        "radiant_ra": 48.2, "radiant_dec": 58.1,
        "zhr": 100, "population_index": 2.2, "speed": 59,
        "parent_body": "Comet 109P/Swift-Tuttle (nucleus 26 km wide, orbital period 133 years)",
        "notes": "The crowd-pleaser. Warm August nights, high ZHR, reliable. Swift-Tuttle would release ~1000x Chicxulub energy if it hit Earth. It won't. Probably.",
    },
    {
        "name": "Orionids",
        "code": "ORI",
        "peak_month": 10, "peak_day": 21,
        "radiant_ra": 95.0, "radiant_dec": 16.0,
        "zhr": 20, "population_index": 2.5, "speed": 66,
        "parent_body": "Comet 1P/Halley (inbound debris trail — Halley's second gift)",
        "notes": "66 km/s entry produces persistent glowing trains.",
    },
    {
        "name": "Leonids",
        "code": "LEO",
        "peak_month": 11, "peak_day": 17,
        "radiant_ra": 152.8, "radiant_dec": 22.0,
        "zhr": 15, "population_index": 2.5, "speed": 71,
        "parent_body": "Comet 55P/Tempel-Tuttle (orbital period 33.2 years)",
        "notes": "Fastest shower at 71 km/s. The 1833 storm produced ~100,000 meteors/hour. We sit in the thin outer part of the trail now.",
    },
    {
        "name": "Geminids",
        "code": "GEM",
        "peak_month": 12, "peak_day": 14,
        "radiant_ra": 112.3, "radiant_dec": 32.5,
        "zhr": 150, "population_index": 2.6, "speed": 35,
        "parent_body": "Asteroid 3200 Phaethon (not a comet — the anomaly that confuses dynamicists)",
        "notes": "Highest ZHR of any annual shower. Parent is a rocky asteroid, which shouldn't produce a debris trail. It does anyway.",
    },
    {
        "name": "Ursids",
        "code": "URS",
        "peak_month": 12, "peak_day": 22,
        "radiant_ra": 217.0, "radiant_dec": 76.0,
        "zhr": 10, "population_index": 3.0, "speed": 33,
        "parent_body": "Comet 8P/Tuttle (orbital period 13.6 years)",
        "notes": "Peaks on December 22nd. Everyone is at Christmas dinner. The most consistently ignored annual shower.",
    },
]
