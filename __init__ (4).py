from .risk_window import risk_window
from .trend_detector import detect_trend


def build_forecast_claim(req, evidence, epistemology):
    official = evidence["official_forecast"]
    mcx = evidence["microclimate_context"]
    summary = official.get("summary", "No official forecast available.")
    if mcx.get("microclimate_confidence") in ["low", "unsupported"]:
        micro_note = "Microclimate adjustment is not asserted; confidence is low."
        claim_type = "personal_location_forecast_with_caution"
    else:
        micro_note = "Limited microclimate adjustment may be shown with caution."
        claim_type = "personal_location_forecast"
    return {
        "claim_id": f"claim_{req.tenant_id}",
        "claim_type": claim_type,
        "tenant_id": req.tenant_id,
        "summary": summary,
        "temperature_f": official.get("temperature_f"),
        "wind_mph": official.get("wind_mph"),
        "precip_probability": official.get("precip_probability"),
        "microclimate_confidence": mcx.get("microclimate_confidence"),
        "microclimate_note": micro_note,
        "knowledge_state": epistemology.get("knowledge_state"),
        "public_proxy": {
            "risk_window": risk_window(evidence),
            "trend": detect_trend(evidence),
        },
    }
