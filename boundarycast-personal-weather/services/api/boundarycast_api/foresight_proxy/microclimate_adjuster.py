from .provider import foresight
from .uncertainty_band import uncertainty_band

SCOPE_EXPLANATIONS = {
    "exact_location": "Your location is precise, official forecast is fresh, nearby observation support is acceptable, microclimate context is sufficient, and uncertainty is bounded.",
    "microclimate_adjusted": "There is enough microclimate context to responsibly qualify the official forecast for your location, but the claim is not absolute.",
    "nearby_observation_area": "Nearby observation support exists, but not enough exact-location or microclimate context. Showing a nearby-area forecast with caution.",
    "official_forecast_area": "I do not have enough exact-location or microclimate evidence to responsibly personalize this forecast. Showing the general forecast for your area instead.",
    "official_alert_only": "An official weather alert governs this area. BoundaryCast does not override official alerts.",
    "unsupported_specific_claim": "The system does not have enough evidence to make that specific personal weather claim.",
}

CLAIM_TYPES = {
    "exact_location": "exact_location_forecast",
    "microclimate_adjusted": "microclimate_adjusted_forecast",
    "nearby_observation_area": "nearby_observation_area_forecast",
    "official_forecast_area": "official_forecast_area_forecast",
    "official_alert_only": "official_alert_notice",
    "unsupported_specific_claim": "withheld_specific_claim",
}


def _public_message(claim_scope, summary, alerts):
    if claim_scope == "official_alert_only":
        active = alerts.get("alerts") or []
        headline = active[0].get("headline") if active else "An official weather alert is active."
        return f"{headline} {SCOPE_EXPLANATIONS['official_alert_only']}"
    if claim_scope == "unsupported_specific_claim":
        return SCOPE_EXPLANATIONS["unsupported_specific_claim"]
    return f"{summary} {SCOPE_EXPLANATIONS[claim_scope]}"


def build_forecast_claim(req, evidence, epistemology, scope_decision):
    official = evidence["official_forecast"]
    mcx = evidence["microclimate_context"]
    alerts = evidence["alerts"]
    claim_scope = scope_decision["claim_scope"]
    summary = official.get("summary") or "No official forecast available."
    if mcx.get("microclimate_confidence") in ["low", "unsupported"]:
        micro_note = "Microclimate adjustment is not asserted; confidence is low."
    else:
        micro_note = "Limited microclimate adjustment may be shown with caution."
    return {
        "claim_id": f"claim_{req.tenant_id}",
        "claim_type": CLAIM_TYPES[claim_scope],
        "tenant_id": req.tenant_id,
        "requested_scope": scope_decision["requested_scope"],
        "claim_scope": claim_scope,
        "scope_reason_codes": scope_decision["scope_reason_codes"],
        "fallback_applied": scope_decision["fallback_applied"],
        "public_message": _public_message(claim_scope, summary, alerts),
        "summary": summary,
        "temperature_f": official.get("temperature_f"),
        "wind_mph": official.get("wind_mph"),
        "precip_probability": official.get("precip_probability"),
        "microclimate_confidence": mcx.get("microclimate_confidence"),
        "microclimate_note": micro_note,
        "uncertainty_interval": uncertainty_band(evidence, epistemology),
        "knowledge_state": epistemology.get("knowledge_state"),
        "uncertainty_label": epistemology.get("uncertainty"),
        "evidence_score": epistemology.get("evidence_score"),
        "public_proxy": foresight(evidence),
    }
