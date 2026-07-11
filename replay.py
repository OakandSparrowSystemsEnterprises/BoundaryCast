def evaluate_policy_rules(policy_packs, evidence, epistemology):
    reasons = []
    effects = []
    alerts = evidence["alerts"]

    if alerts.get("active_alert_count", 0) > 0:
        effects.append("PROTOCOL")
        reasons.append("official_alert_supremacy")

    if not epistemology.get("official_forecast_available"):
        effects.append("ABSTAIN")
        reasons.append("missing_official_forecast")

    if epistemology.get("knowledge_state") == "insufficient":
        effects.append("ABSTAIN")
        reasons.append("insufficient_evidence_for_publication")

    if not epistemology.get("evidence_fresh"):
        effects.append("PERMIT_WITH_CAUTION")
        reasons.append("observation_stale_or_missing")

    if epistemology.get("microclimate_confidence") in ["low", "unsupported"]:
        effects.append("PERMIT_WITH_CAUTION")
        reasons.append("low_microclimate_confidence")

    if not epistemology.get("uncertainty_bounded"):
        effects.append("ABSTAIN")
        reasons.append("uncertainty_too_wide")

    if not epistemology.get("verdict_replayable"):
        effects.append("BLOCK")
        reasons.append("verdict_not_replayable")

    return {
        "policy_pack_versions": [p.get("policy_pack_id") for p in policy_packs],
        "effects": effects,
        "reason_codes": sorted(set(reasons)),
    }
