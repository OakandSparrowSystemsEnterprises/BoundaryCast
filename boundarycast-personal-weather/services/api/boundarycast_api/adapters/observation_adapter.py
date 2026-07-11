from datetime import datetime, timezone

from .live_sources import live_enabled, live_observation

def get_observation_stub(req):
    if req.simulate_no_observation:
        # Source is known but no nearby observation is available.
        return {
            "source_name": "nearest_public_observation_stub",
            "available": False,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "freshness_minutes": None,
            "distance_km": None,
            "temperature_f": None,
            "wind_mph": None,
        }
    if live_enabled() and not req.demo_mode:
        try:
            return live_observation(req.latitude, req.longitude)
        except Exception:
            return {
                "source_name": "live_observation_unavailable",
                "available": False,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness_minutes": None, "distance_km": None,
                "temperature_f": None, "wind_mph": None,
            }
    return {
        "source_name": "nearest_public_observation_stub",
        "available": True,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "freshness_minutes": 12,
        "distance_km": 4.8,
        "temperature_f": 87,
        "wind_mph": 6,
    }

