"""
Astronomical Calculations
=========================
"The nitrogen in our DNA, the calcium in our teeth, the iron in our blood,
the carbon in our apple pies were made in the interiors of collapsing stars."
— Carl Sagan, Cosmos (1980)

Pure math. No external astronomy libraries. Every formula is cited.

Primary reference : Jean Meeus, "Astronomical Algorithms" 2nd ed. (Willmann-Bell, 1998)
Secondary         : IMO Meteor Observation Manual v1.4
                    Schaefer B.E. (1990), "Telescopic Limiting Magnitudes", PASP 102
                    Bortle J. (2001), "Gauging Light Pollution", Sky & Telescope 101(2)

Coordinate epoch: J2000.0 throughout.
Convention: angles are degrees at API boundaries, radians internally.
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Optional


# ── Lookup Tables ──────────────────────────────────────────────────────────────

# Bortle Dark-Sky Scale → Naked-Eye Limiting Magnitude (NELM)
# Midpoint values. Actual per-class range is roughly ±0.25 mag.
BORTLE_TO_LM: dict[int, float] = {
    1: 7.8,   # Truly dark. Zodiacal band casts a faint shadow on the ground.
    2: 7.3,   # Typical dark site. M33 visible with direct vision.
    3: 6.8,   # Rural. Some light dome visible on horizon.
    4: 6.3,   # Rural/suburban transition. Obvious city glow in directions.
    5: 5.8,   # Suburban. Milky Way seen but washed out low.
    6: 5.3,   # Bright suburban. Milky Way barely visible at zenith.
    7: 4.7,   # Suburban/urban transition. Milky Way invisible.
    8: 4.2,   # City. Only Orion and a few dozen bright stars.
    9: 3.5,   # Inner city. ~20 stars visible. Why are you outside?
}

# European AQI → Atmospheric Transparency Factor (0–1)
# PM2.5 dominates above AQI 40 via Mie scattering at ~550 nm visual band.
AQI_TRANSPARENCY: list[tuple[float, float]] = [
    (20,           1.00),
    (40,           0.92),
    (60,           0.80),
    (80,           0.62),
    (100,          0.40),
    (float("inf"), 0.18),
]

# Moon illumination → effective limiting magnitude penalty (mag lost)
MOON_LM_PENALTY: list[tuple[float, float]] = [
    (0.00, 0.0),
    (0.15, 0.2),
    (0.25, 0.5),
    (0.50, 1.0),
    (0.75, 1.5),
    (0.90, 1.9),
    (1.00, 2.2),
]


# ── Utility ────────────────────────────────────────────────────────────────────

def _lerp(table: list[tuple[float, float]], x: float) -> float:
    """Linear interpolation through a sorted (x, y) lookup table. Clamps at edges."""
    if x <= table[0][0]:
        return table[0][1]
    for i in range(len(table) - 1):
        x0, y0 = table[i]
        x1, y1 = table[i + 1]
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return table[-1][1]


# ── Julian Date & Sidereal Time ────────────────────────────────────────────────

def julian_date(dt: datetime) -> float:
    """
    Convert UTC datetime to Julian Date.
    Algorithm: Meeus Chapter 7. Valid for all dates after 15 Oct 1582.
    J2000.0 = JD 2451545.0 = 2000 Jan 1.5 UTC
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    Y, M, D = dt.year, dt.month, dt.day
    if M <= 2:
        Y -= 1
        M += 12

    A = Y // 100
    B = 2 - A + A // 4
    day_frac = (dt.hour + dt.minute / 60.0 + dt.second / 3600.0) / 24.0
    jd = (int(365.25 * (Y + 4716))
          + int(30.6001 * (M + 1))
          + D + day_frac + B - 1524.5)
    return jd


def greenwich_mean_sidereal_time(dt: datetime) -> float:
    """
    GMST in degrees. Formula: Meeus eq. 12.4.
    Accurate to ~0.1 arcsec for dates near J2000.
    """
    jd = julian_date(dt)
    T  = (jd - 2451545.0) / 36525.0

    theta = (280.46061837
             + 360.98564736629 * (jd - 2451545.0)
             + 0.000387933 * T ** 2
             - T ** 3 / 38710000.0)
    return theta % 360.0


def local_sidereal_time(lon_deg: float, dt: datetime) -> float:
    """Local Sidereal Time in degrees. lon_deg is degrees East."""
    return (greenwich_mean_sidereal_time(dt) + lon_deg) % 360.0


# ── Radiant Geometry ───────────────────────────────────────────────────────────

def radiant_altitude(ra_deg: float, dec_deg: float,
                     lat_deg: float, lon_deg: float,
                     dt: datetime) -> float:
    """
    Altitude of the meteor shower radiant above the observer's horizon.
    Formula (Meeus Ch. 13): sin(alt) = sin(φ)·sin(δ) + cos(φ)·cos(δ)·cos(H)
    Returns degrees. Negative = below horizon.
    """
    lst   = local_sidereal_time(lon_deg, dt)
    H     = math.radians(lst - ra_deg)
    phi   = math.radians(lat_deg)
    delta = math.radians(dec_deg)

    sin_alt = (math.sin(phi) * math.sin(delta)
               + math.cos(phi) * math.cos(delta) * math.cos(H))

    return math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))


def radiant_azimuth(ra_deg: float, dec_deg: float,
                    lat_deg: float, lon_deg: float,
                    dt: datetime) -> float:
    """
    Azimuth of the radiant, clockwise from North.
    0°=N, 90°=E, 180°=S, 270°=W.
    Returns 0.0 if radiant is at or below horizon.
    """
    lst   = local_sidereal_time(lon_deg, dt)
    H     = math.radians(lst - ra_deg)
    phi   = math.radians(lat_deg)
    delta = math.radians(dec_deg)

    sin_alt = (math.sin(phi) * math.sin(delta)
               + math.cos(phi) * math.cos(delta) * math.cos(H))
    sin_alt = max(-1.0, min(1.0, sin_alt))

    if sin_alt <= 0.0:
        return 0.0

    cos_alt = math.sqrt(max(0.0, 1.0 - sin_alt ** 2))
    if cos_alt < 1e-10:
        return 0.0

    cos_az = (math.sin(delta) - math.sin(phi) * sin_alt) / (math.cos(phi) * cos_alt)
    az     = math.degrees(math.acos(max(-1.0, min(1.0, cos_az))))

    if math.sin(H) > 0:
        az = 360.0 - az

    return az % 360.0


def az_to_cardinal(az: float) -> str:
    """Azimuth degrees → 8-point compass cardinal."""
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(az / 45.0) % 8]


# ── Moon Phase ─────────────────────────────────────────────────────────────────

def moon_illumination(dt: datetime) -> float:
    """
    Fraction of Moon illuminated (0.0=new, 1.0=full).
    Synodic period approximation — accurate to ~1 day.
    Reference epoch: New Moon JD 2451549.259 (2000 Jan 6 18:14 UTC).
    """
    SYNODIC_PERIOD = 29.53058867
    NEW_MOON_EPOCH = 2451549.259

    jd             = julian_date(dt)
    days_since_new = (jd - NEW_MOON_EPOCH) % SYNODIC_PERIOD
    phase_angle    = (days_since_new / SYNODIC_PERIOD) * 2.0 * math.pi

    return (1.0 - math.cos(phase_angle)) / 2.0


# ── Limiting Magnitude ─────────────────────────────────────────────────────────

def aqi_transparency_factor(aqi: Optional[float]) -> float:
    """European AQI → atmospheric transparency (0–1). None → 0.90."""
    if aqi is None or (isinstance(aqi, float) and math.isnan(aqi)):
        return 0.90
    return _lerp(AQI_TRANSPARENCY, max(0.0, float(aqi)))


def effective_limiting_magnitude(bortle: int,
                                  moon_illum: float,
                                  aqi: Optional[float]) -> float:
    """
    Effective naked-eye limiting magnitude from three sources:
      1. Sky darkness  (Bortle scale)
      2. Moonlight     (magnitude penalty)
      3. Aerosols      (Beer-Lambert: Δmag = −2.5·log10(transparency))
    Clamped to [3.0, 8.5].
    """
    base_lm  = BORTLE_TO_LM.get(bortle, 5.8)
    moon_pen = _lerp(MOON_LM_PENALTY, moon_illum)
    aqi_t    = aqi_transparency_factor(aqi)
    aqi_pen  = -2.5 * math.log10(max(aqi_t, 1e-6))

    return max(3.0, min(8.5, base_lm - moon_pen - aqi_pen))


# ── Core ZHR Formula ───────────────────────────────────────────────────────────

def compute_visible_zhr(shower: dict,
                         lat: float,
                         lon: float,
                         bortle: int,
                         dt: datetime,
                         cloud_cover: float,
                         aqi: Optional[float]) -> float:
    """
    Expected visible meteors per hour. IMO Standard Formula:
      ZHR_obs = ZHR × sin(alt) × r^(lm − 6.5) × (1 − cloud_fraction)

    Returns 0.0 if radiant below horizon or sky fully overcast.
    """
    alt = radiant_altitude(shower["radiant_ra"], shower["radiant_dec"],
                            lat, lon, dt)
    if alt <= 0.0:
        return 0.0

    moon       = moon_illumination(dt)
    lm         = effective_limiting_magnitude(bortle, moon, aqi)
    r          = shower["population_index"]
    cloud_frac = max(0.0, min(100.0, cloud_cover or 0.0)) / 100.0

    if cloud_frac >= 1.0:
        return 0.0

    return max(0.0,
               shower["zhr"]
               * math.sin(math.radians(alt))
               * r ** (lm - 6.5)
               * (1.0 - cloud_frac))


# ── Hourly Prediction ──────────────────────────────────────────────────────────

def get_hourly_prediction(shower: dict,
                           lat: float,
                           lon: float,
                           bortle: int,
                           peak_dt: datetime,
                           cloud_lookup: dict,
                           aqi_lookup: dict) -> list:
    """
    Hour-by-hour predictions for the 24h window centred on shower peak.
    Cloud defaults to 50% and AQI to None for hours beyond forecast coverage.
    """
    results      = []
    window_start = peak_dt - timedelta(hours=12)

    for h in range(24):
        dt = window_start + timedelta(hours=h)
        ts = dt.strftime("%Y-%m-%dT%H:%M")

        cloud = cloud_lookup.get(ts)
        aqi   = aqi_lookup.get(ts)

        if aqi is None:
            for offset in (-1, 1, -2, 2, -3, 3):
                adj = (dt + timedelta(hours=offset)).strftime("%Y-%m-%dT%H:%M")
                if adj in aqi_lookup:
                    aqi = aqi_lookup[adj]
                    break

        alt  = radiant_altitude(shower["radiant_ra"], shower["radiant_dec"], lat, lon, dt)
        az   = radiant_azimuth(shower["radiant_ra"], shower["radiant_dec"], lat, lon, dt)
        moon = moon_illumination(dt)
        lm   = effective_limiting_magnitude(bortle, moon, aqi)
        vzhr = compute_visible_zhr(shower, lat, lon, bortle, dt,
                                    cloud if cloud is not None else 50.0, aqi)

        results.append({
            "hour_label":       dt.strftime("%b %d %H:00 UTC"),
            "hour_iso":         dt.isoformat(),
            "visible_zhr":      round(vzhr, 2),
            "radiant_alt_deg":  round(alt, 1),
            "radiant_az_deg":   round(az, 1),
            "radiant_cardinal": az_to_cardinal(az) if alt > 0 else "—",
            "cloud_pct":        round(cloud, 0) if cloud is not None else None,
            "aqi":              round(aqi, 0) if aqi is not None else None,
            "moon_pct":         round(moon * 100.0, 0),
            "eff_lm":           round(lm, 2),
        })

    return results


# ── Best Clear Window ──────────────────────────────────────────────────────────

def find_best_window(hourly: list, min_hours: int = 2) -> Optional[dict]:
    """
    Best consecutive viewing window: cloud < 50% and radiant above horizon.
    Returns the window with the highest mean visible ZHR, or None.
    """
    CLOUD_MAX = 50.0

    def viable(h: dict) -> bool:
        return ((h["cloud_pct"] is None or h["cloud_pct"] < CLOUD_MAX)
                and h["visible_zhr"] > 0)

    best_window: Optional[list] = None
    best_avg    = -1.0
    start_idx   = None

    for i, h in enumerate(hourly):
        if viable(h):
            if start_idx is None:
                start_idx = i
        else:
            if start_idx is not None:
                window = hourly[start_idx:i]
                if len(window) >= min_hours:
                    avg = sum(x["visible_zhr"] for x in window) / len(window)
                    if avg > best_avg:
                        best_avg    = avg
                        best_window = window
                start_idx = None

    if start_idx is not None:
        window = hourly[start_idx:]
        if len(window) >= min_hours:
            avg = sum(x["visible_zhr"] for x in window) / len(window)
            if avg > best_avg:
                best_window = window

    if best_window is None:
        return None

    peak_hour = max(best_window, key=lambda h: h["visible_zhr"])

    return {
        "start":        best_window[0]["hour_label"],
        "end":          best_window[-1]["hour_label"],
        "duration_hrs": len(best_window),
        "avg_zhr":      round(sum(h["visible_zhr"] for h in best_window) / len(best_window), 1),
        "peak_zhr":     round(peak_hour["visible_zhr"], 1),
        "peak_hour":    peak_hour["hour_label"],
        "face_dir":     peak_hour["radiant_cardinal"],
        "face_az":      peak_hour["radiant_az_deg"],
        "avg_cloud":    round(sum(h["cloud_pct"] or 0 for h in best_window) / len(best_window), 0),
    }
