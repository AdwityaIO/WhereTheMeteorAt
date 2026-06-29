"""
Meteor Shower Predictor — Flask Backend
=======================================
"For my confirmation, I did not need the comet."
— Napoleon Bonaparte (1769–1821)
He was wrong. You always need the comet.

Zero API keys required. All services used are free and open:
  Nominatim (OpenStreetMap)  — geocoding (text → lat/lon)
  Open-Meteo                 — cloud cover + precipitation forecast
  Open-Meteo Air Quality     — European AQI (PM2.5)
  lightpollutionmap.info     — VIIRS satellite Bortle detection

Routes:
  GET  /              → serve index.html
  GET  /api/geocode   → text query → { lat, lon, name, place_data }
  POST /api/predict   → shower predictions for lat/lon
  POST /api/calendar  → .ics calendar download
"""

from flask import Flask, render_template, request, jsonify, Response
from datetime import datetime, timedelta, timezone
import requests

from showers import METEOR_SHOWERS
from astro import (
    get_hourly_prediction,
    find_best_window,
)
from light_pollution import fetch_bortle, estimate_from_place

app = Flask(__name__)

# ── API Endpoints ──────────────────────────────────────────────────────────────
NOMINATIM_URL   = "https://nominatim.openstreetmap.org/search"
FORECAST_URL    = "https://api.open-meteo.com/v1/forecast"
AQI_URL         = "https://air-quality-api.open-meteo.com/v1/air-quality"
REQUEST_TIMEOUT = 10

# Nominatim requires a descriptive User-Agent per their usage policy
NOMINATIM_HEADERS = {
    "User-Agent": "MeteorPredictor/1.0 (Hack Club Stardance 2026; educational project)",
    "Accept-Language": "en",
}


# ── Fetchers ───────────────────────────────────────────────────────────────────

def geocode(query: str) -> dict:
    """
    Convert a text location to coordinates using Nominatim (OpenStreetMap).
    Free, no key required. Rate limit: 1 req/s — fine for interactive use.
    Returns: { lat, lon, name, place_data }
    Raises: ValueError if location not found, RequestException on network error.
    """
    resp = requests.get(NOMINATIM_URL, params={
        "q":              query,
        "format":         "json",
        "limit":          1,
        "addressdetails": 1,
    }, headers=NOMINATIM_HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    results = resp.json()
    if not results:
        raise ValueError(f"Location not found: {query}")

    r = results[0]
    return {
        "lat":        float(r["lat"]),
        "lon":        float(r["lon"]),
        "name":       r.get("display_name", query),
        "place_data": {
            "name":        r.get("name", ""),
            "addresstype": r.get("addresstype", ""),
            "type":        r.get("type", ""),
            "importance":  r.get("importance", 0.3),
            "display_name": r.get("display_name", ""),
        },
    }


def fetch_weather(lat: float, lon: float) -> dict:
    """7-day hourly cloud cover + precipitation from Open-Meteo."""
    resp = requests.get(FORECAST_URL, params={
        "latitude":      lat,
        "longitude":     lon,
        "hourly":        "cloudcover,precipitation_probability",
        "forecast_days": 7,
        "timezone":      "auto",
    }, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_aqi(lat: float, lon: float) -> dict:
    """5-day hourly European AQI from Open-Meteo Air Quality."""
    resp = requests.get(AQI_URL, params={
        "latitude":      lat,
        "longitude":     lon,
        "hourly":        "european_aqi,pm2_5",
        "forecast_days": 5,
        "timezone":      "auto",
    }, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def build_lookup(times: list, values: list) -> dict:
    """Zip Open-Meteo timestamps with values, skipping None entries."""
    return {t: v for t, v in zip(times, values) if v is not None}


# ── Label Helpers ──────────────────────────────────────────────────────────────

def rating_label(visible_zhr: float) -> dict:
    if visible_zhr >= 60: return {"emoji": "🌟", "text": "Exceptional"}
    if visible_zhr >= 30: return {"emoji": "✅", "text": "Great"}
    if visible_zhr >= 15: return {"emoji": "👍", "text": "Good"}
    if visible_zhr >= 5:  return {"emoji": "🟡", "text": "Moderate"}
    if visible_zhr >= 1:  return {"emoji": "🔴", "text": "Poor"}
    return                       {"emoji": "⚫", "text": "Nothing"}


def aqi_label(aqi) -> str:
    if aqi is None:  return "Unknown"
    if aqi <= 20:    return "Good"
    if aqi <= 40:    return "Fair"
    if aqi <= 60:    return "Moderate"
    if aqi <= 80:    return "Poor"
    if aqi <= 100:   return "Very Poor"
    return                  "Hazardous"


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/geocode")
def api_geocode():
    """
    GET /api/geocode?q=Patna+Bihar

    Converts a location text query to coordinates via Nominatim.
    No API key required.
    Returns: { lat, lon, name, place_data }
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing ?q= parameter"}), 400

    try:
        result = geocode(query)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except requests.Timeout:
        return jsonify({"error": "Geocoding timed out. Try again."}), 503
    except requests.RequestException as e:
        return jsonify({"error": f"Geocoding failed: {str(e)}"}), 503


@app.route("/api/predict", methods=["POST"])
def predict():
    """
    POST /api/predict
    Body: { "lat": float, "lon": float, "place_data": dict (optional) }

    Returns shower predictions with auto-detected Bortle sky class.
    """
    body = request.get_json(force=True)

    try:
        lat = float(body["lat"])
        lon = float(body["lon"])
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid input: {e}"}), 400

    lat        = max(-90.0,  min(90.0,  lat))
    lon        = max(-180.0, min(180.0, lon))
    place_data = body.get("place_data")

    # ── Step 1: Sky darkness from satellite (with fallback) ────────────────────
    sky_data = fetch_bortle(lat, lon, place_data)
    bortle   = sky_data["bortle"]

    # ── Step 2: Weather + AQI ──────────────────────────────────────────────────
    try:
        weather_raw = fetch_weather(lat, lon)
    except requests.Timeout:
        return jsonify({"error": "Weather API timed out. Try again."}), 503
    except requests.RequestException as e:
        return jsonify({"error": f"Weather fetch failed: {str(e)}"}), 503

    try:
        aqi_raw = fetch_aqi(lat, lon)
    except Exception:
        # AQI is non-critical — continue with empty data
        aqi_raw = {"hourly": {"time": [], "european_aqi": []}}

    w_times      = weather_raw["hourly"]["time"]
    cloud_lookup = build_lookup(w_times, weather_raw["hourly"]["cloudcover"])
    a_times      = aqi_raw["hourly"]["time"]
    aqi_lookup   = build_lookup(a_times, aqi_raw["hourly"]["european_aqi"])

    # ── Step 3: Compute shower predictions ────────────────────────────────────
    now     = datetime.now(timezone.utc)
    results = []

    for shower in METEOR_SHOWERS:
        # Next peak date (roll to next year if already passed)
        peak_dt = datetime(now.year, shower["peak_month"], shower["peak_day"],
                           2, 0, 0, tzinfo=timezone.utc)
        if peak_dt < now - timedelta(days=1):
            peak_dt = datetime(now.year + 1, shower["peak_month"],
                               shower["peak_day"], 2, 0, 0, tzinfo=timezone.utc)

        days_until = (peak_dt - now).days

        hourly      = get_hourly_prediction(shower, lat, lon, bortle,
                                             peak_dt, cloud_lookup, aqi_lookup)
        best        = max(hourly, key=lambda h: h["visible_zhr"])
        best_window = find_best_window(hourly)

        # Current AQI for display
        now_ts      = now.strftime("%Y-%m-%dT%H:%M")
        current_aqi = aqi_lookup.get(now_ts)
        if current_aqi is None and aqi_lookup:
            current_aqi = next(iter(aqi_lookup.values()))

        results.append({
            "name":              shower["name"],
            "code":              shower["code"],
            "peak_date":         peak_dt.strftime("%B %d, %Y"),
            "days_until_peak":   days_until,
            "max_zhr":           shower["zhr"],
            "best_visible_zhr":  round(best["visible_zhr"], 1),
            "best_hour":         best["hour_label"],
            "best_radiant_alt":  best["radiant_alt_deg"],
            "face_dir":          best["radiant_cardinal"],
            "face_az":           best["radiant_az_deg"],
            "parent_body":       shower["parent_body"],
            "speed_kmps":        shower["speed"],
            "notes":             shower["notes"],
            "current_aqi":       round(current_aqi, 0) if current_aqi is not None else None,
            "current_aqi_label": aqi_label(current_aqi),
            "rating":            rating_label(best["visible_zhr"]),
            "best_window":       best_window,
            "hourly_data":       hourly,
        })

    # Sort: soonest peak first
    results.sort(key=lambda x: x["days_until_peak"] % 366)

    return jsonify({
        "showers": results,
        "sky":     sky_data,
    })


@app.route("/api/calendar", methods=["POST"])
def calendar():
    """
    POST /api/calendar
    Body: { "showers": [...] }  — output from /api/predict

    Returns an .ics file importable into Google Calendar, Apple Calendar, Outlook.
    """
    body    = request.get_json(force=True)
    showers = body.get("showers", [])

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Meteor Predictor//Stardance 2026//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Meteor Showers 2026",
        "X-WR-CALDESC:Predicted viewing times from your exact location",
        "X-WR-TIMEZONE:UTC",
    ]

    for s in showers:
        try:
            peak = datetime.strptime(s["peak_date"], "%B %d, %Y").replace(tzinfo=timezone.utc)
        except (ValueError, KeyError):
            continue

        dtstart = peak.replace(hour=20, minute=0, second=0)
        dtend   = (peak + timedelta(days=1)).replace(hour=5, minute=0, second=0)

        window_note = ""
        if s.get("best_window"):
            w = s["best_window"]
            window_note = (f"\\nBest clear window: {w['start']} to {w['end']} "
                           f"({w['duration_hrs']}h, avg {w['avg_zhr']} meteors/hr)")

        description = (
            f"Predicted: ~{s['best_visible_zhr']} meteors/hr from your location"
            f"\\nFace direction: {s['face_dir']} ({s['face_az']}deg)"
            f"\\nTheoretical ZHR: {s['max_zhr']} (perfect conditions)"
            f"\\nParent body: {s['parent_body']}"
            f"{window_note}"
            f"\\nGenerated by Meteor Predictor (Hack Club Stardance 2026)"
        )

        lines += [
            "BEGIN:VEVENT",
            f"UID:{s['code']}-{peak.year}-meteorpredictor@stardance",
            f"DTSTART:{dtstart.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{dtend.strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:comet {s['name']} Peak ({s['code']}) - {s['rating']['text']}",
            f"DESCRIPTION:{description}",
            "TRANSP:TRANSPARENT",
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")

    return Response(
        "\r\n".join(lines),
        mimetype="text/calendar",
        headers={"Content-Disposition": "attachment; filename=meteor-showers-2026.ics"},
    )


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
