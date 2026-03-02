import math
import json
import os
import time
import requests

# Module-level geocode cache
_geocode_cache = {}
_cache_loaded = False

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {
    'User-Agent': 'RealityScraper/1.0 (Czech real estate aggregator)'
}


def haversine_km(lat1, lon1, lat2, lon2):
    """Distance in km between two GPS points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def geocode_cached(address, cache_path='geo_cache.json'):
    """Geocode an address via Nominatim, with JSON file caching.

    Returns (lat, lng) tuple or None on failure.
    """
    global _geocode_cache, _cache_loaded

    # Load cache from disk on first call
    if not _cache_loaded:
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    _geocode_cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                _geocode_cache = {}
        _cache_loaded = True

    # Cache hit
    if address in _geocode_cache:
        val = _geocode_cache[address]
        if val is None:
            return None
        return (val[0], val[1])

    # Cache miss — query Nominatim with retry
    result = None
    max_retries = 3
    for attempt in range(max_retries):
        try:
            params = {
                'q': f"{address}, Czech Republic",
                'format': 'json',
                'limit': 1,
            }
            resp = requests.get(NOMINATIM_URL, params=params, headers=NOMINATIM_HEADERS, timeout=30)
            resp.raise_for_status()
            results = resp.json()

            if results:
                lat = float(results[0]['lat'])
                lng = float(results[0]['lon'])
                _geocode_cache[address] = [lat, lng]
                result = (lat, lng)
            else:
                _geocode_cache[address] = None
            break  # success, stop retrying
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 * (attempt + 1)  # 2s, 4s backoff
                print(f"  Geocoding retry {attempt + 1}/{max_retries} for '{address}' (waiting {wait}s): {repr(e)}")
                time.sleep(wait)
            else:
                print(f"  Geocoding failed for '{address}' after {max_retries} attempts: {repr(e)}")
                # Don't cache failures — retry next run
    else:
        # All retries exhausted without break
        pass

    # Only cache successful results and confirmed empty results (not transient errors)
    if address in _geocode_cache:
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(_geocode_cache, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"  Warning: could not save geocode cache: {repr(e)}")

    # Rate limit: 1.5 req/sec for Nominatim
    time.sleep(1.5)

    return result
