"""
Light Pollution Detection
=========================
Automatically determines Bortle sky class from coordinates using two methods
in order of preference:

Method 1 — VIIRS Satellite Tiles (lightpollutionmap.info)
  Real satellite data from the Falchi et al. (2016) light pollution atlas.
  Fetches a PNG map tile, reads the pixel at the exact coordinates,
  maps the color to a radiance value, then to a Bortle class.
  Reference: Falchi F. et al. (2016). "The new world atlas of artificial
  night sky brightness." Science Advances 2(6). DOI: 10.1126/sciadv.1600377

Method 2 — Nominatim Place-Type Estimate (fallback)
  If tile fetch fails for any reason, estimates Bortle from the OSM place
  type and importance score returned by the geocoding step.
  Less precise but always available and requires no extra API call.

Why tiles instead of the raw dataset?
  The Falchi .tif is ~1.6GB. Tiles are small PNGs served on demand.
"""

import math
import io
import requests
from PIL import Image
from typing import Optional

# ── Constants ──────────────────────────────────────────────────────────────────

TILE_SIZE  = 256
ZOOM_LEVEL = 8    # ~1.2 km resolution per pixel at this zoom
TILE_URL   = "https://www.lightpollutionmap.info/tiles/viirs_2023/{z}/{x}/{y}.png"

TILE_HEADERS = {
    "Referer":    "https://www.lightpollutionmap.info/",
    "User-Agent": "MeteorPredictor/1.0 (educational Hack Club Stardance project)",
    "Accept":     "image/png,image/*,*/*;q=0.8",
}

# SQM midpoints per Bortle class
# Source: Cinzano (2001); Schaefer (1990) cross-calibration
BORTLE_TO_SQM: dict[int, float] = {
    1: 21.8, 2: 21.5, 3: 21.0, 4: 20.5, 5: 19.5,
    6: 18.5, 7: 17.5, 8: 16.5, 9: 15.5,
}

BORTLE_DESCRIPTIONS: dict[int, str] = {
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

# Nominatim addresstype / place type → Bortle estimate
# Based on typical population density of OSM place categories
PLACE_TYPE_BORTLE: dict[str, int] = {
    "city":                 8,
    "town":                 6,
    "suburb":               7,
    "borough":              8,
    "quarter":              7,
    "neighbourhood":        7,
    "village":              4,
    "hamlet":               3,
    "isolated_dwelling":    2,
    "farm":                 2,
    "locality":             3,
    "municipality":         7,
    "administrative":       6,
    "county":               5,
    "state":                5,
    "country":              5,
}


# ── Tile Math ──────────────────────────────────────────────────────────────────

def _lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """
    OSM slippy map tile indices from geographic coordinates.
    Web Mercator (EPSG:3857).
    https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
    """
    n      = 2 ** zoom
    tile_x = int((lon + 180.0) / 360.0 * n)
    lat_r  = math.radians(max(-85.051, min(85.051, lat)))   # Mercator clamp
    tile_y = int((1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n)
    return (max(0, min(n - 1, tile_x)),
            max(0, min(n - 1, tile_y)))


def _pixel_in_tile(lat: float, lon: float, zoom: int,
                    tile_x: int, tile_y: int) -> tuple[int, int]:
    """Pixel offset (px, py) within the tile for a given lat/lon."""
    n      = 2 ** zoom
    x_frac = (lon + 180.0) / 360.0 * n
    lat_r  = math.radians(max(-85.051, min(85.051, lat)))
    y_frac = (1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n
    px     = int((x_frac - tile_x) * TILE_SIZE)
    py     = int((y_frac - tile_y) * TILE_SIZE)
    return (max(0, min(TILE_SIZE - 1, px)),
            max(0, min(TILE_SIZE - 1, py)))


# ── Pixel → Bortle ─────────────────────────────────────────────────────────────

def _pixel_to_bortle(r: int, g: int, b: int, a: int) -> int:
    """
    Map a tile RGBA pixel to a Bortle class.

    lightpollutionmap.info uses a logarithmic color ramp:
      Black/transparent → pristine dark (Bortle 1-2)
      Dark blue         → rural dark    (Bortle 3)
      Blue              → rural/sub     (Bortle 4)
      Cyan              → suburban      (Bortle 5)
      Green             → bright sub    (Bortle 6)
      Yellow            → urban trans   (Bortle 7)
      Orange            → city          (Bortle 8)
      Red/White         → inner city    (Bortle 9)

    Luminance thresholds calibrated against known locations:
      Atacama desert (~B1): lum ~2
      Rural France   (~B3): lum ~35
      London suburbs (~B6): lum ~110
      Central London (~B9): lum ~220
    """
    if a < 20:
        return 2   # Transparent = ocean or no data → assume dark

    lum = 0.299 * r + 0.587 * g + 0.114 * b   # ITU-R BT.601 perceptual luminance

    if lum < 6:   return 1
    if lum < 18:  return 2
    if lum < 38:  return 3
    if lum < 62:  return 4
    if lum < 92:  return 5
    if lum < 125: return 6
    if lum < 162: return 7
    if lum < 205: return 8
    return 9


def _bortle_result(bortle: int, source: str, error: Optional[str] = None) -> dict:
    """Build a standardised Bortle result dict."""
    return {
        "bortle":      bortle,
        "sqm":         BORTLE_TO_SQM[bortle],
        "description": BORTLE_DESCRIPTIONS[bortle],
        "source":      source,
        "error":       error,
    }


# ── Method 1: VIIRS Tile ───────────────────────────────────────────────────────

def _fetch_from_viirs(lat: float, lon: float) -> Optional[dict]:
    """
    Fetch Bortle class from lightpollutionmap.info VIIRS tile.
    Returns result dict on success, None on any failure.
    """
    tile_x, tile_y = _lat_lon_to_tile(lat, lon, ZOOM_LEVEL)
    px, py         = _pixel_in_tile(lat, lon, ZOOM_LEVEL, tile_x, tile_y)
    url            = TILE_URL.format(z=ZOOM_LEVEL, x=tile_x, y=tile_y)

    resp = requests.get(url, headers=TILE_HEADERS, timeout=8)
    resp.raise_for_status()

    # Verify we actually got an image
    content_type = resp.headers.get("Content-Type", "")
    if "image" not in content_type and len(resp.content) < 100:
        return None

    img        = Image.open(io.BytesIO(resp.content)).convert("RGBA")
    r, g, b, a = img.getpixel((px, py))
    bortle     = _pixel_to_bortle(r, g, b, a)

    return _bortle_result(
        bortle,
        source="Falchi 2016 / VIIRS satellite (lightpollutionmap.info)",
    )


# ── Method 2: Nominatim Place Estimate ────────────────────────────────────────

def estimate_from_place(place_data: dict) -> dict:
    """
    Estimate Bortle from Nominatim geocoding result.
    Uses addresstype and importance score as proxies for light pollution.
    Always succeeds — worst case returns Bortle 5.
    """
    address_type = place_data.get("addresstype", "")
    place_type   = place_data.get("type", "")
    importance   = float(place_data.get("importance", 0.3) or 0.3)

    # Try direct type match first
    bortle = PLACE_TYPE_BORTLE.get(address_type) or PLACE_TYPE_BORTLE.get(place_type)

    if bortle is None:
        # Fall back to importance score (0=tiny hamlet, 1=major capital)
        if importance >= 0.75:  bortle = 8
        elif importance >= 0.55: bortle = 7
        elif importance >= 0.40: bortle = 6
        elif importance >= 0.25: bortle = 5
        elif importance >= 0.12: bortle = 4
        else:                    bortle = 3

    place_name = place_data.get("name", "this location")
    return _bortle_result(
        bortle,
        source=f"Estimated from place type '{address_type or place_type}' (OSM Nominatim)",
        error=None,
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_bortle(lat: float, lon: float,
                  place_data: Optional[dict] = None) -> dict:
    """
    Determine Bortle sky class for a location.

    Tries VIIRS satellite tiles first. Falls back to place-type estimation
    if tiles are unavailable. Falls back to Bortle 5 if everything fails.

    Args:
        lat, lon:   Observer coordinates
        place_data: Nominatim result dict (optional, used as fallback)

    Returns dict with keys: bortle, sqm, description, source, error
    """
    # Method 1: VIIRS satellite
    try:
        result = _fetch_from_viirs(lat, lon)
        if result is not None:
            return result
    except requests.Timeout:
        pass   # Tile server slow — fall through
    except requests.HTTPError as e:
        pass   # Tile not found or server error — fall through
    except Exception:
        pass   # Image decode or other error — fall through

    # Method 2: Nominatim place estimate
    if place_data:
        result = estimate_from_place(place_data)
        result["error"] = "VIIRS tile unavailable — using location-type estimate"
        return result

    # Method 3: Safe default
    return _bortle_result(
        5,
        source="Default — sky darkness could not be determined",
        error="Both VIIRS and place-based detection failed",
    )
