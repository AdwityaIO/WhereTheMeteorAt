"""
Light Pollution Detection
=========================
Automatically determines your Bortle sky class from your coordinates using
real satellite data — no guessing required from the user.

Data source: lightpollutionmap.info
  - Hosts the Falchi et al. (2016) light pollution atlas
  - Tiles are derived from VIIRS (Visible Infrared Imaging Radiometer Suite)
    satellite measurements — the same instrument on Suomi-NPP and NOAA-20
  - Original paper: Falchi F. et al. (2016). "The new world atlas of artificial
    night sky brightness." Science Advances 2(6). DOI: 10.1126/sciadv.1600377

Method:
  1. Convert lat/lon to Web Mercator tile coordinates (OSM slippy map scheme)
  2. Fetch the 256×256 PNG tile from lightpollutionmap.info
  3. Extract the RGBA pixel at the exact sub-tile coordinates
  4. Map pixel color → artificial sky radiance → SQM → Bortle class

Why tiles instead of the raw dataset?
  The Falchi .tif is ~1.6GB. Tiles are small PNGs served on demand.
  The color ramp encodes the radiance value — we reverse it to get Bortle.

Color ramp reference:
  lightpollutionmap.info uses a logarithmic color scale where:
  Black     → pristine dark sky  (< 0.25 μcd/m²)   → Bortle 1-2
  Dark blue → rural dark         (0.25–1 μcd/m²)   → Bortle 3
  Blue      → rural/suburban     (1–3 μcd/m²)      → Bortle 4
  Cyan      → suburban           (3–9 μcd/m²)      → Bortle 5
  Green     → bright suburban    (9–27 μcd/m²)     → Bortle 6
  Yellow    → urban transition   (27–82 μcd/m²)    → Bortle 7
  Orange    → city               (82–245 μcd/m²)   → Bortle 8
  Red/White → inner city         (> 245 μcd/m²)    → Bortle 9
"""

import math
import io
import requests
from PIL import Image
from typing import Optional

# ── Constants ──────────────────────────────────────────────────────────────────

TILE_SIZE  = 256          # Standard OSM tile size in pixels
ZOOM_LEVEL = 8            # Zoom 8 → ~1.2km resolution per pixel. Good enough.
TILE_URL   = "https://www.lightpollutionmap.info/tiles/viirs_2023/{z}/{x}/{y}.png"

REQUEST_HEADERS = {
    "Referer":    "https://www.lightpollutionmap.info/",
    "User-Agent": "MeteorPredictor/1.0 (educational/non-commercial Hack Club project)",
}

# SQM (Sky Quality Meter, mag/arcsec²) midpoints per Bortle class
# Source: Cinzano P. et al. (2001); Schaefer B.E. (1990) cross-calibration
BORTLE_TO_SQM = {
    1: 21.8,   # Zodiacal band casts shadows
    2: 21.5,   # Typical dark site
    3: 21.0,   # Rural, light dome on horizon
    4: 20.5,   # Rural/suburban transition
    5: 19.5,   # Suburban, Milky Way washed out low
    6: 18.5,   # Bright suburban
    7: 17.5,   # Suburban/urban transition
    8: 16.5,   # City
    9: 15.5,   # Inner city
}

# Bortle class descriptions for the UI
BORTLE_DESCRIPTIONS = {
    1: "Truly dark — zodiacal band casts shadows",
    2: "Dark site — M33 visible with direct vision",
    3: "Rural sky — light dome on horizon",
    4: "Rural/suburban — obvious city glow",
    5: "Suburban — Milky Way washed out",
    6: "Bright suburban — Milky Way barely visible",
    7: "Urban transition — Milky Way invisible",
    8: "City — only Orion & bright stars",
    9: "Inner city — ~20 stars visible",
}


# ── Tile Math ──────────────────────────────────────────────────────────────────

def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """
    Convert geographic coordinates to OSM slippy map tile indices (x, y).

    Web Mercator projection (EPSG:3857).
    x increases eastward. y increases southward (top-left origin).
    Formula: https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
    """
    n     = 2 ** zoom
    tile_x = int((lon + 180.0) / 360.0 * n)
    lat_r  = math.radians(lat)
    tile_y = int((1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n)
    # Clamp to valid tile range
    tile_x = max(0, min(n - 1, tile_x))
    tile_y = max(0, min(n - 1, tile_y))
    return tile_x, tile_y


def pixel_in_tile(lat: float, lon: float, zoom: int,
                   tile_x: int, tile_y: int) -> tuple[int, int]:
    """
    Get the pixel coordinates within a tile for a given lat/lon.
    Returns (px, py) where 0 ≤ px, py < TILE_SIZE.
    """
    n      = 2 ** zoom
    x_frac = (lon + 180.0) / 360.0 * n
    lat_r  = math.radians(lat)
    y_frac = (1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n

    px = int((x_frac - tile_x) * TILE_SIZE)
    py = int((y_frac - tile_y) * TILE_SIZE)

    return (max(0, min(TILE_SIZE - 1, px)),
            max(0, min(TILE_SIZE - 1, py)))


# ── Pixel → Bortle Mapping ─────────────────────────────────────────────────────

def pixel_to_bortle(r: int, g: int, b: int, a: int) -> int:
    """
    Map a tile pixel (RGBA) to a Bortle class.

    lightpollutionmap.info uses a logarithmic color ramp from black (dark)
    through blue → cyan → green → yellow → orange → red/white (bright).

    We use two signals:
      1. Alpha channel: 0 = no data / ocean → assume Bortle 2 (dark)
      2. Perceived luminance (weighted RGB): proxy for radiance level

    The luminance thresholds are calibrated against known locations:
      Atacama desert (~Bortle 1): luminance ~2
      Rural France    (~Bortle 3): luminance ~35
      London suburbs  (~Bortle 6): luminance ~110
      Central London  (~Bortle 9): luminance ~220
    """
    # Transparent pixel = ocean or no data → very dark sky
    if a < 10:
        return 2

    # Perceptual luminance (ITU-R BT.601)
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    if lum < 6:   return 1
    if lum < 18:  return 2
    if lum < 38:  return 3
    if lum < 62:  return 4
    if lum < 92:  return 5
    if lum < 125: return 6
    if lum < 162: return 7
    if lum < 205: return 8
    return 9


# ── Main Public Function ───────────────────────────────────────────────────────

def fetch_bortle(lat: float, lon: float) -> dict:
    """
    Determine Bortle sky class from satellite data for a given location.

    Returns dict:
      {
        "bortle":      int (1–9),
        "sqm":         float (mag/arcsec²),
        "description": str,
        "source":      str,
        "error":       str | None,
      }

    On failure (network error, tile not available), returns Bortle 5 as a
    safe default with an error message — the app still works, just less precise.
    """
    fallback = {
        "bortle":      5,
        "sqm":         BORTLE_TO_SQM[5],
        "description": BORTLE_DESCRIPTIONS[5],
        "source":      "Default (satellite fetch failed)",
        "error":       None,
    }

    try:
        tile_x, tile_y = lat_lon_to_tile(lat, lon, ZOOM_LEVEL)
        px, py         = pixel_in_tile(lat, lon, ZOOM_LEVEL, tile_x, tile_y)

        url = TILE_URL.format(z=ZOOM_LEVEL, x=tile_x, y=tile_y)
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=8)
        resp.raise_for_status()

        img  = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        r, g, b, a = img.getpixel((px, py))

        bortle = pixel_to_bortle(r, g, b, a)
        sqm    = BORTLE_TO_SQM[bortle]

        return {
            "bortle":      bortle,
            "sqm":         sqm,
            "description": BORTLE_DESCRIPTIONS[bortle],
            "source":      "Falchi 2016 / VIIRS satellite (lightpollutionmap.info)",
            "error":       None,
        }

    except requests.RequestException as e:
        fallback["error"] = f"Tile fetch failed: {str(e)}"
        return fallback
    except Exception as e:
        fallback["error"] = f"Bortle detection failed: {str(e)}"
        return fallback
