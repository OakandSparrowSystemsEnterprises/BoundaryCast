from datetime import datetime, timezone

def get_official_forecast_stub(req):
    if not req.demo_mode:
        # Real NWS API adapter can be added here.
        pass
    return {
        "source_name": "official_forecast_stub",
        "available": True,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "freshness_minutes": 5,
        "summary": "Clear and warm. Public demo data only.",
        "temperature_f": 88,
        "wind_mph": 7,
        "precip_probability": 0.05,
        "grid_distance_km": 3.2,
    }
