from datetime import datetime, timezone

from .live_sources import live_enabled, live_official_forecast

def get_official_forecast_stub(req):
    if req.simulate_no_official_forecast:
        # Source is known but no forecast product is available for the grid.
        return {
            "source_name": "official_forecast_stub",
            "available": False,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "freshness_minutes": None,
            "summary": None,
            "temperature_f": None,
            "wind_mph": None,
            "precip_probability": None,
            "grid_distance_km": None,
        }
    if live_enabled() and not req.demo_mode:
        try:
            return live_official_forecast(req.latitude, req.longitude)
        except Exception:
            return {
                "source_name": "live_forecast_unavailable",
                "available": False,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "freshness_minutes": None, "summary": None,
                "temperature_f": None, "wind_mph": None,
                "precip_probability": None, "grid_distance_km": None,
            }
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

