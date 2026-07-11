from .evidence_score import evidence_score
from .uncertainty import uncertainty_label


def evaluate_knowledge_state(evidence, req):
    loc = evidence["location_context"]
    mcx = evidence["microclimate_context"]
    official = evidence["official_forecast"]
    obs = evidence["observation"]
    alerts = evidence["alerts"]

    checks = {
        "schema_valid": True,
        "location_known": bool(loc.get("location_known")),
        "location_precise_enough": bool(loc.get("personal_location_language_allowed")),
        "official_forecast_available": bool(official.get("available")),
        "observation_available": bool(obs.get("available")),
        "evidence_fresh": (official.get("freshness_minutes", 9999) <= 60 and obs.get("freshness_minutes", 9999) <= 90),
        "source_known": bool(official.get("source_name") and obs.get("source_name") and alerts.get("source_name")),
        "observation_distance_acceptable": obs.get("distance_km", 9999) <= 10,
        "forecast_grid_distance_known": official.get("grid_distance_km") is not None,
        "official_alert_checked": bool(alerts.get("available")),
        "microclimate_context_known": mcx.get("microclimate_confidence") not in [None, "unsupported"],
        "microclimate_confidence": mcx.get("microclimate_confidence", "low"),
        "uncertainty_bounded": bool(official.get("available") and obs.get("available")),
        "claim_inside_forecast_window": req.forecast_hours <= 72,
        "policy_pack_active": True,
        "verdict_replayable": True,
    }
    hard_required = ["schema_valid", "location_known", "official_forecast_available", "source_known", "official_alert_checked", "claim_inside_forecast_window"]
    if all(checks[k] for k in hard_required) and checks["evidence_fresh"] and checks["uncertainty_bounded"]:
        knowledge_state = "sufficient"
    elif checks["official_forecast_available"] and checks["source_known"]:
        knowledge_state = "partial"
    else:
        knowledge_state = "insufficient"

    checks["knowledge_state"] = knowledge_state
    checks["recommended_gatekeeper_state"] = "PERMIT" if knowledge_state == "sufficient" else "PERMIT_WITH_CAUTION" if knowledge_state == "partial" else "ABSTAIN"
    checks["evidence_score"] = evidence_score(checks)
    checks["uncertainty"] = uncertainty_label(checks)
    return checks
