from datetime import datetime, timezone

def get_observation_stub(req):
    return {
        "source_name": "nearest_public_observation_stub",
        "available": True,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "freshness_minutes": 12,
        "distance_km": 4.8,
        "temperature_f": 87,
        "wind_mph": 6,
    }
