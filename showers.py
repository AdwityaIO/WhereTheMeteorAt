"""
Meteor Shower Database
======================
Source: IMO Working List of Meteor Showers (https://www.imo.net/resources/calendar/)
        AMS (American Meteor Society) annual observer reports
        NASA Meteor Watch program data

Radiant coordinates (RA, Dec) are J2000.0 epoch, given for peak date.
These drift slightly day-to-day — negligible for planning purposes.

ZHR = Zenithal Hourly Rate: theoretical meteors/hour under *perfect* conditions
      (limiting magnitude 6.5, radiant exactly at zenith, zero cloud, zero moon,
       zero light pollution, perfect observer efficiency).
      Real observed rates are always lower. This app calculates the real number.

population_index (r): ratio of meteors of magnitude m+1 to magnitude m.
      Lower r = richer in bright meteors = better for naked eye.
      r=2.0 → lots of fireballs. r=3.5 → mostly faint specks.

speed: atmospheric entry velocity in km/s.
      Kinetic energy ∝ v², so 71 km/s Leonids are far brighter per gram than
      35 km/s Geminids, even though Geminids have higher ZHR.
"""

METEOR_SHOWERS = [
    {
        "name": "Quadrantids",
        "code": "QUA",
        "peak_month": 1,
        "peak_day": 3,
        "radiant_ra": 230.1,
        "radiant_dec": 48.5,
        "zhr": 120,
        "population_index": 2.1,
        "speed": 41,
        "parent_body": "Asteroid 2003 EH1 (likely extinct comet, possibly Machholz)",
        "notes": "Peak window is brutally narrow — about 6 hours. Miss it and you wait a year. Northern hemisphere only; declination 48.5° means poor visibility from southern latitudes.",
    },
    {
        "name": "Lyrids",
        "code": "LYR",
        "peak_month": 4,
        "peak_day": 22,
        "radiant_ra": 271.4,
        "radiant_dec": 33.6,
        "zhr": 18,
        "population_index": 2.1,
        "speed": 49,
        "parent_body": "Comet C/1861 G1 Thatcher (orbital period: ~415 years)",
        "notes": "Oldest recorded meteor shower in history. Chinese astronomers documented it in 687 BC. Occasional outburst years push ZHR to ~100, unpredictably.",
    },
    {
        "name": "Eta Aquariids",
        "code": "ETA",
        "peak_month": 5,
        "peak_day": 6,
        "radiant_ra": 338.0,
        "radiant_dec": -1.0,
        "zhr": 50,
        "population_index": 2.4,
        "speed": 66,
        "parent_body": "Comet 1P/Halley (outbound debris trail — Halley's first gift of the year)",
        "notes": "Best from southern hemisphere where radiant rises much higher. From northern latitudes the radiant stays low, cutting effective ZHR significantly.",
    },
    {
        "name": "Delta Aquariids",
        "code": "SDA",
        "peak_month": 7,
        "peak_day": 30,
        "radiant_ra": 333.0,
        "radiant_dec": -16.0,
        "zhr": 25,
        "population_index": 3.2,
        "speed": 41,
        "parent_body": "Possibly Comet 96P/Machholz (disputed since 2021 orbital analysis)",
        "notes": "Broad peak — good for several nights either side. Heavily confused with Perseids since the active periods overlap in late July.",
    },
    {
        "name": "Perseids",
        "code": "PER",
        "peak_month": 8,
        "peak_day": 12,
        "radiant_ra": 48.2,
        "radiant_dec": 58.1,
        "zhr": 100,
        "population_index": 2.2,
        "speed": 59,
        "parent_body": "Comet 109P/Swift-Tuttle (nucleus 26 km wide, orbital period 133 years)",
        "notes": "The crowd-pleaser. Warm August nights, high ZHR, reliable. If Swift-Tuttle ever hits Earth it would release ~1000× the energy of the Chicxulub impactor. It won't. Probably.",
    },
    {
        "name": "Orionids",
        "code": "ORI",
        "peak_month": 10,
        "peak_day": 21,
        "radiant_ra": 95.0,
        "radiant_dec": 16.0,
        "zhr": 20,
        "population_index": 2.5,
        "speed": 66,
        "parent_body": "Comet 1P/Halley (inbound debris trail — Halley's second gift)",
        "notes": "The other Halley shower. 66 km/s entry produces persistent glowing trains.",
    },
    {
        "name": "Leonids",
        "code": "LEO",
        "peak_month": 11,
        "peak_day": 17,
        "radiant_ra": 152.8,
        "radiant_dec": 22.0,
        "zhr": 15,
        "population_index": 2.5,
        "speed": 71,
        "parent_body": "Comet 55P/Tempel-Tuttle (orbital period 33.2 years)",
        "notes": "Fastest shower at 71 km/s. The 1833 storm produced an estimated 100,000 meteors/hour. We currently sit in the thin outer part of the debris trail.",
    },
    {
        "name": "Geminids",
        "code": "GEM",
        "peak_month": 12,
        "peak_day": 14,
        "radiant_ra": 112.3,
        "radiant_dec": 32.5,
        "zhr": 150,
        "population_index": 2.6,
        "speed": 35,
        "parent_body": "Asteroid 3200 Phaethon (not a comet — the anomaly that confuses dynamicists)",
        "notes": "Highest ZHR of any annual shower. Parent is a rocky asteroid, which shouldn't produce a debris trail at all. It does anyway. Physics is sometimes embarrassed by observation.",
    },
    {
        "name": "Ursids",
        "code": "URS",
        "peak_month": 12,
        "peak_day": 22,
        "radiant_ra": 217.0,
        "radiant_dec": 76.0,
        "zhr": 10,
        "population_index": 3.0,
        "speed": 33,
        "parent_body": "Comet 8P/Tuttle (orbital period 13.6 years)",
        "notes": "Peaks on December 22nd. Everyone is at Christmas dinner. The most consistently ignored annual shower.",
    },
]
