from datetime import datetime, timezone

def get_alerts_stub(req):
    return {
        "source_name": "official_alerts_stub",
        "available": True,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "active_alert_count": 0,
        "alerts": [],
    }
