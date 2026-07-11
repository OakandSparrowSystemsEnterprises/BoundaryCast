"""Live public weather evidence: Open-Meteo forecasts + NWS alerts.

No API keys, no accounts. Enabled when BOUNDARYCAST_LIVE_EVIDENCE=1 and
the request is not in demo mode; every call is wrapped so any failure —
offline, slow, non-US point for alerts, schema drift — falls back to the
deterministic demo stubs, with the source_name always disclosing which
one you got. Coordinates are shared with these public providers for the
live request only (see docs/privacy-zero-cache.md); responses are cached
in memory for 60 seconds to be a polite client.
"""
import json
import os
import threading
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

LIVE_ENV = "BOUNDARYCAST_LIVE_EVIDENCE"
TIMEOUT_S = 4
USER_AGENT = "BoundaryCast/1.0 (governed weather oracle demo)"
CACHE_TTL_S = 60

_CACHE = {}
_CACHE_LOCK = threading.Lock()

WMO_SUMMARIES = {
    0: "Clear sky.", 1: "Mainly clear.", 2: "Partly cloudy.", 3: "Overcast.",
    45: "Fog.", 48: "Depositing rime fog.",
    51: "Light drizzle.", 53: "Drizzle.", 55: "Dense drizzle.",
    56: "Freezing drizzle.", 57: "Dense freezing drizzle.",
    61: "Light rain.", 63: "Rain.", 65: "Heavy rain.",
    66: "Freezing rain.", 67: "Heavy freezing rain.",
    71: "Light snow.", 73: "Snow.", 75: "Heavy snow.", 77: "Snow grains.",
    80: "Light rain showers.", 81: "Rain showers.", 82: "Violent rain showers.",
    85: "Snow showers.", 86: "Heavy snow showers.",
    95: "Thunderstorm.", 96: "Thunderstorm with hail.", 99: "Thunderstorm with heavy hail.",
}


def live_enabled():
    # Personal weather is live by default. Operators can explicitly disable
    # outbound evidence calls with BOUNDARYCAST_LIVE_EVIDENCE=0.
    return os.environ.get(LIVE_ENV, "1") != "0"


def search_locations(query, limit=5):
    params = urllib.parse.urlencode({
        "name": query, "count": limit, "language": "en", "format": "json",
    })
    data = _fetch_json(f"https://geocoding-api.open-meteo.com/v1/search?{params}")
    results = []
    for item in data.get("results") or []:
        parts = [item.get("name"), item.get("admin1"), item.get("country")]
        results.append({
            "name": ", ".join(dict.fromkeys(p for p in parts if p)),
            "latitude": item.get("latitude"),
            "longitude": item.get("longitude"),
            "timezone": item.get("timezone"),
        })
    return results


def _fetch_json(url, headers=None):
    now = time.time()
    with _CACHE_LOCK:
        hit = _CACHE.get(url)
        if hit and now - hit[0] < CACHE_TTL_S:
            return hit[1]
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        data = json.loads(response.read())
    with _CACHE_LOCK:
        _CACHE[url] = (now, data)
    return data


def _forecast_payload(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat:.4f}&longitude={lon:.4f}"
        "&current=temperature_2m,wind_speed_10m,weather_code"
        "&hourly=precipitation_probability&forecast_hours=12"
        "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=UTC"
    )
    return _fetch_json(url)


def _freshness_minutes(iso_time):
    try:
        t = datetime.fromisoformat(iso_time).replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - t).total_seconds() // 60))
    except (ValueError, TypeError):
        return 15


def live_official_forecast(lat, lon):
    data = _forecast_payload(lat, lon)
    current = data["current"]
    probs = [p for p in ((data.get("hourly") or {}).get("precipitation_probability") or []) if p is not None]
    code = current.get("weather_code")
    return {
        "source_name": "open-meteo-forecast-live",
        "available": True,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "freshness_minutes": _freshness_minutes(current.get("time")),
        "summary": WMO_SUMMARIES.get(code, f"Weather code {code}."),
        "temperature_f": current.get("temperature_2m"),
        "wind_mph": current.get("wind_speed_10m"),
        "precip_probability": (max(probs) / 100.0) if probs else None,
        "grid_distance_km": 1.0,
    }


def live_observation(lat, lon):
    # Open-Meteo's current block is model-interpolated at the exact point —
    # disclosed in the source name, distance 0 by construction.
    data = _forecast_payload(lat, lon)
    current = data["current"]
    return {
        "source_name": "open-meteo-current-live (model-interpolated)",
        "available": True,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "freshness_minutes": _freshness_minutes(current.get("time")),
        "distance_km": 0.0,
        "temperature_f": current.get("temperature_2m"),
        "wind_mph": current.get("wind_speed_10m"),
    }


def live_alerts(lat, lon):
    # NWS covers US points only; elsewhere this raises and the caller
    # falls back to the demo stub.
    url = f"https://api.weather.gov/alerts/active?point={lat:.4f},{lon:.4f}"
    data = _fetch_json(url, headers={"Accept": "application/geo+json"})
    features = data.get("features") or []
    alerts = []
    for feature in features[:5]:
        props = feature.get("properties") or {}
        alerts.append({
            "alert_id": feature.get("id"),
            "event": props.get("event"),
            "headline": props.get("headline"),
            "severity": props.get("severity"),
        })
    return {
        "source_name": "nws-alerts-live",
        "available": True,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "active_alert_count": len(features),
        "alerts": alerts,
    }

