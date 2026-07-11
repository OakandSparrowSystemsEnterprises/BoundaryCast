PERSONAL_SCOPES = ("exact_location", "microclimate_adjusted")
DEGRADED_SCOPES = ("nearby_observation_area", "official_forecast_area")
from ..epistemology.claim_scope import official_alert_governs


def evaluate_policy_rules(policy_packs, evidence, epistemology, scope_decision):
    reasons = []
    effects = []
    alerts = evidence["alerts"]
    claim_scope = scope_decision.get("claim_scope")

    if official_alert_governs(evidence):
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
        # Unbounded uncertainty forbids personal-scope claims outright, but a
        # gracefully degraded area claim may still publish with caution: the
        # claim being made is the official product, not a personal adjustment.
        if claim_scope in PERSONAL_SCOPES:
            effects.append("ABSTAIN")
            reasons.append("uncertainty_too_wide")
        elif claim_scope in DEGRADED_SCOPES:
            effects.append("PERMIT_WITH_CAUTION")
            reasons.append("uncertainty_partially_bounded")

    if claim_scope == "unsupported_specific_claim":
        effects.append("ABSTAIN")
        reasons.append("unsupported_specific_claim")

    if not epistemology.get("verdict_replayable"):
        effects.append("BLOCK")
        reasons.append("verdict_not_replayable")

    return {
        "policy_pack_versions": [p.get("policy_pack_id") for p in policy_packs],
        "effects": effects,
        "reason_codes": sorted(set(reasons)),
    }

