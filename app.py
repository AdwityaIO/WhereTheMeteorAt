"""
Meteor Shower Predictor — Flask Backend
=======================================
"For my confirmation, I did not need the comet."
— Napoleon Bonaparte (1769–1821)
He was wrong. You always need the comet.

Routes:
  GET  /              → serve index.html
  GET  /api/geocode   → text location → lat/lon (Google Geocoding API)
  POST /api/predict   → shower predictions (auto-detects Bortle from satellite)
  POST /api/calendar  → .ics calendar file download

Keys needed (.env file):
  GOOGLE_API_KEY  → for /api/geocode only
                    Enable "Geocoding API" in Google Cloud Console
                    Free tier: 40,000 requests/month

No key needed for:
  - Open-Meteo (weather + AQI)
  - lightpollutionmap.info (Bortle detection via VIIRS tiles)
"""

import os
from flask import Flask, render_template, request, jsonify, Response
from datetime import datetime, timedelta, timezone
import requests
from dotenv import load_dotenv

from showers import METEOR_SHOWERS
from astro import (
    compute_visible_zhr,
    moon_illumination,
    get_hourly_prediction,
    radiant_altitude,
    radiant_azimuth,
    az_to_cardinal,
    effective_limiting_magnitude,
    find_best_window,
)
from light_pollution import fetch_bortle

load_dotenv()

app = Flask(__name__)

GOOGLE_API_KEY  = os.environ.get("GOOGLE_API_KEY", "")
FORECAST_URL    = "https://api.open-meteo.com/v1/forecast"
AQI_URL         = "https://air-quality-api.open-meteo.com/v1/air-quality"
GEOCODING_URL   = "https://maps.googleapis.com/maps/api/geocode/json"
REQUEST_TIMEOUT = 10


# ── External Data Fetchers ─────────────────────────────────────────────────────

def fetch_weather(lat: float, lon: float) -> dict:
    r = requests.get(FORECAST_URL, params={
        "latitude":      lat,
        "longitude":     lon,
        "hourly":        "cloudcover,visibility,precipitation_probability",
        "forecast_days": 7,
        "timezone":      "auto",
    }, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def fetch_aqi(lat: float, lon: float) -> dict:
    r = requests.get(AQI_URL, params={
        "latitude":      lat,
        "longitude":     lon,
        "hourly":        "european_aqi,pm2_5",
        "forecast_days": 5,
        "timezone":      "auto",
    }, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def build_lookup(times: list, values: list) -> dict:
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
def geocode():
    """
    Convert a location text query to lat/lon using Google Geocoding API.
    GET /api/geocode?q=Patna+Bihar

    Returns: { "lat": float, "lon": float, "name": str }
    Requires GOOGLE_API_KEY in .env
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing query parameter ?q="}), 400

    if not GOOGLE_API_KEY:
        return jsonify({"error": "GOOGLE_API_KEY not set in .env file"}), 503

    try:
        r = requests.get(GEOCODING_URL, params={
            "address": query,
            "key":     GOOGLE_API_KEY,
        }, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        if data.get("status") != "OK" or not data.get("results"):
            return jsonify({"error": f"Location not found: {query}"}), 404

        result   = data["results"][0]
        location = result["geometry"]["location"]
        name     = result["formatted_address"]

        return jsonify({
            "lat":  location["lat"],
            "lon":  location["lng"],
            "name": name,
        })

    except requests.RequestException as e:
        return jsonify({"error": f"Geocoding failed: {str(e)}"}), 503


@app.route("/api/predict", methods=["POST"])
def predict():
    """
    Main prediction endpoint.

    Expects JSON: { "lat": float, "lon": float }
    Bortle class is now auto-detected from satellite data — no longer a user input.

    Returns JSON list of showers sorted by days until peak.
    Each entry includes sky darkness data from Falchi 2016 / VIIRS satellite.
    """
    body = request.get_json(force=True)

    try:
        lat = float(body["lat"])
        lon = float(body["lon"])
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid input: {e}"}), 400

    lat = max(-90.0,  min(90.0,  lat))
    lon = max(-180.0, min(180.0, lon))

    # ── Step 1: Auto-detect sky darkness from satellite ────────────────────────
    sky_data = fetch_bortle(lat, lon)
    bortle   = sky_data["bortle"]

    # ── Step 2: Fetch weather and AQI ─────────────────────────────────────────
    try:
        weather_raw = fetch_weather(lat, lon)
        aqi_raw     = fetch_aqi(lat, lon)
    except requests.Timeout:
        return jsonify({"error": "Weather API timed out. Try again."}), 503
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to fetch forecast: {str(e)}"}), 503

    w_times      = weather_raw["hourly"]["time"]
    cloud_lookup = build_lookup(w_times, weather_raw["hourly"]["cloudcover"])

    a_times    = aqi_raw["hourly"]["time"]
    aqi_lookup = build_lookup(a_times, aqi_raw["hourly"]["european_aqi"])

    # ── Step 3: Compute predictions for each shower ────────────────────────────
    now     = datetime.now(timezone.utc)
    results = []

    for shower in METEOR_SHOWERS:
        peak_dt = datetime(now.year, shower["peak_month"], shower["peak_day"],
                           2, 0, 0, tzinfo=timezone.utc)
        if peak_dt < now - timedelta(days=1):
            peak_dt = datetime(now.year + 1, shower["peak_month"],
                               shower["peak_day"], 2, 0, 0, tzinfo=timezone.utc)

        days_until_peak = (peak_dt - now).days

        hourly      = get_hourly_prediction(shower, lat, lon, bortle,
                                             peak_dt, cloud_lookup, aqi_lookup)
        best        = max(hourly, key=lambda h: h["visible_zhr"])
        best_window = find_best_window(hourly)

        now_ts      = now.strftime("%Y-%m-%dT%H:%M")
        current_aqi = aqi_lookup.get(now_ts)
        if current_aqi is None and aqi_lookup:
            current_aqi = next(iter(aqi_lookup.values()))

        results.append({
            "name":              shower["name"],
            "code":              shower["code"],
            "peak_date":         peak_dt.strftime("%B %d, %Y"),
            "days_until_peak":   days_until_peak,
            "max_zhr":           shower["zhr"],
            "best_visible_zhr":  round(best["visible_zhr"], 1),
            "best_hour":         best["hour_label"],
            "best_radiant_alt":  best["radiant_alt_deg"],
            "face_dir":          best["radiant_cardinal"],
            "face_az":           best["radiant_az_deg"],
            "parent_body":       shower["parent_body"],
            "speed_kmps":        shower["speed"],
            "notes":             shower["notes"],
            "current_aqi":       round(current_aqi, 0) if current_aqi else None,
            "current_aqi_label": aqi_label(current_aqi),
            "rating":            rating_label(best["visible_zhr"]),
            "best_window":       best_window,
            "hourly_data":       hourly,
            # Sky data from satellite
            "sky": {
                "bortle":      sky_data["bortle"],
                "sqm":         sky_data["sqm"],
                "description": sky_data["description"],
                "source":      sky_data["source"],
                "error":       sky_data.get("error"),
            },
        })

    results.sort(key=lambda x: x["days_until_peak"] % 366)

    # Include sky data at top level for display in UI
    return jsonify({
        "showers": results,
        "sky":     sky_data,
    })


@app.route("/api/calendar", methods=["POST"])
def calendar():
    """
    Generate .ics calendar file for all shower peaks.
    Expects JSON: { "showers": [...] }
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
                           f"({w['duration_hrs']}h · avg {w['avg_zhr']} meteors/hr)")

        sky_note = ""
        if s.get("sky"):
            sk = s["sky"]
            sky_note = f"\\nSky darkness: Bortle {sk['bortle']} · SQM {sk['sqm']} · {sk['description']}"

        description = (
            f"Predicted: ~{s['best_visible_zhr']} meteors/hr from your location"
            f"\\nFace direction: {s['face_dir']} ({s['face_az']}°)"
            f"\\nTheoretical ZHR: {s['max_zhr']} (perfect conditions)"
            f"\\nParent body: {s['parent_body']}"
            f"{window_note}"
            f"{sky_note}"
            f"\\n\\nGenerated by Meteor Predictor (Hack Club Stardance 2026)"
        )

        lines += [
            "BEGIN:VEVENT",
            f"UID:{s['code']}-{peak.year}-meteorpredictor@stardance",
            f"DTSTART:{dtstart.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{dtend.strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:☄️ {s['name']} Peak ({s['code']}) — {s['rating']['text']}",
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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
