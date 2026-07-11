from datetime import datetime, timezone

def get_alerts_stub(req):
    if req.simulate_alert:
        return {
            "source_name": "official_alerts_stub",
            "available": True,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "active_alert_count": 1,
            "alerts": [
                {
                    "alert_id": "demo_alert_001",
                    "event": "Excessive Heat Warning",
                    "headline": "Excessive Heat Warning in effect for this area. Demo data only.",
                    "severity": "Severe",
                }
            ],
        }
    return {
        "source_name": "official_alerts_stub",
        "available": True,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "active_alert_count": 0,
        "alerts": [],
    }
