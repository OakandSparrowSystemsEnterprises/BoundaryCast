"""Oracle recipe: resolve weather-dependent prediction markets.

Prediction markets fail when resolution is vague. BoundaryCast resolves a
market only from a governed forecast claim: the Gatekeeper verdict decides
whether the system may speak, the claim scope decides how specific the
resolution basis is, and the market creator's `minimum_scope` decides how
specific it must be. Anything less resolves to UNRESOLVED and escalates to
arbitration — the oracle never pretends.

Resolution semantics:
- PROTOCOL (official alert governs): `alert_active` markets resolve YES;
  condition markets go UNRESOLVED, because BoundaryCast does not read
  condition values from under an official alert it must not soften.
- ABSTAIN / BLOCK: UNRESOLVED, escalate to arbitration.
- PERMIT / PERMIT_WITH_CAUTION: the claim's granted scope must meet the
  market's minimum scope; then the condition is evaluated against the
  claim's published values.
"""
from ..epistemology.claim_scope import SCOPE_SPECIFICITY

OPERATORS = {
    "gt": lambda value, threshold: value > threshold,
    "gte": lambda value, threshold: value >= threshold,
    "lt": lambda value, threshold: value < threshold,
    "lte": lambda value, threshold: value <= threshold,
}

RESOLUTION_CONFIDENCE = {
    "publish": "firm",
    "publish_with_caution": "qualified",
    "official_alert_governs": "official",
}


def _scope_meets_minimum(claim_scope, minimum_scope):
    if claim_scope not in SCOPE_SPECIFICITY:
        return False
    return SCOPE_SPECIFICITY.index(claim_scope) <= SCOPE_SPECIFICITY.index(minimum_scope)


def _unresolved(req, forecast, reason, detail):
    return _record(req, forecast, resolution="UNRESOLVED", unresolved_reason=reason,
                   detail=detail, escalation="arbitration", observed_value=None)


def _record(req, forecast, resolution, detail, observed_value,
            unresolved_reason=None, escalation=None):
    verdict = forecast["verdict"]
    epistemology = forecast["epistemology"]
    return {
        "product": "BoundaryCast Oracle Recipe",
        "market_id": req.market_id,
        "question": req.question,
        "resolution": resolution,
        "resolution_confidence": RESOLUTION_CONFIDENCE.get(verdict["product_verdict"]) if resolution in ("YES", "NO") else None,
        "unresolved_reason": unresolved_reason,
        "escalation": escalation,
        "detail": detail,
        "condition": {
            "metric": req.metric,
            "operator": req.operator,
            "threshold": req.threshold,
            "observed_value": observed_value,
            "forecast_hours": req.forecast_hours,
        },
        "resolution_basis": {
            "claim_scope": verdict["claim_scope"],
            "requested_minimum_scope": req.minimum_scope,
            "fallback_applied": verdict["fallback_applied"],
            "gatekeeper_verdict": verdict["gatekeeper_verdict"],
            "product_verdict": verdict["product_verdict"],
            "scope_reason_codes": verdict["scope_reason_codes"],
            "reason_codes": verdict["reason_codes"],
            "evidence_score": epistemology["evidence_score"],
            "uncertainty": epistemology["uncertainty"],
            "microclimate_confidence": verdict["microclimate_confidence"],
        },
        "artifact": forecast["artifact"],
        "replay_endpoint": "/api/v1/replay",
    }


def resolve_market(req, forecast):
    """Map a governed forecast result onto a market resolution record."""
    verdict = forecast["verdict"]
    gk = verdict["gatekeeper_verdict"]

    if gk == "PROTOCOL":
        if req.metric == "alert_active":
            return _record(req, forecast, resolution="YES",
                           detail="An official weather alert is active for this location. Alert-first resolution.",
                           observed_value=True)
        return _unresolved(req, forecast, "official_alert_governs",
                           "An official alert governs this area. BoundaryCast does not resolve condition markets from under an official alert.")

    if gk in ("ABSTAIN", "BLOCK"):
        return _unresolved(req, forecast, "insufficient_evidence",
                           "The evidence does not support any publishable claim for this market. Escalate to the market's arbitration path.")

    if req.metric == "alert_active":
        return _record(req, forecast, resolution="NO",
                       detail="Official alerts were checked and none are active for this location.",
                       observed_value=False)

    claim_scope = verdict["claim_scope"]
    if not _scope_meets_minimum(claim_scope, req.minimum_scope):
        return _unresolved(req, forecast, "scope_below_market_minimum",
                           f"The evidence supports a '{claim_scope}' claim, but this market requires at least '{req.minimum_scope}'.")

    observed = forecast["claim"].get(req.metric)
    if observed is None:
        return _unresolved(req, forecast, "metric_unavailable",
                           f"The governed claim does not carry a value for '{req.metric}'.")

    holds = OPERATORS[req.operator](observed, req.threshold)
    outcome = "YES" if holds else "NO"
    return _record(req, forecast, resolution=outcome,
                   detail=f"{req.metric} = {observed} {req.operator} {req.threshold} is {str(holds).lower()} at claim scope '{claim_scope}'.",
                   observed_value=observed)
