"""Claim Scope: the forecast-specific graceful-degradation layer.

The Gatekeeper verdict answers "may the system speak?".
Claim Scope answers "how specific may the system be?".

An unsupported exact/personal request never means automatic total
abstention. It means "do not make that specific claim" — the system falls
back to the highest supported claim scope, and only abstains when no
supported scope exists at all.
"""

CLAIM_SCOPES = [
    "exact_location",
    "microclimate_adjusted",
    "nearby_observation_area",
    "official_forecast_area",
    "official_alert_only",
    "unsupported_specific_claim",
]

# Publishable scopes ordered from most to least specific.
SCOPE_SPECIFICITY = [
    "exact_location",
    "microclimate_adjusted",
    "nearby_observation_area",
    "official_forecast_area",
]

# Reason codes must match examples/policy-packs/claim-scope-policy.json.
SCOPE_SUPPORTED_REASON_CODES = {
    "exact_location": "exact_location_scope_supported",
    "microclimate_adjusted": "microclimate_scope_supported",
    "nearby_observation_area": "nearby_observation_scope_supported",
    "official_forecast_area": "official_area_scope_supported",
}
ALERT_SCOPE_REASON_CODE = "official_alert_scope_governs"
UNSUPPORTED_REASON_CODE = "unsupported_specific_claim"

ADEQUATE_MICROCLIMATE_CONFIDENCE = ["medium", "high"]


def official_alert_governs(evidence):
    return evidence["alerts"].get("active_alert_count", 0) > 0


def exact_location_supported(checks):
    return (
        checks.get("location_precise_enough")
        and checks.get("official_forecast_available")
        and checks.get("observation_available")
        and checks.get("evidence_fresh")
        and checks.get("microclimate_confidence") in ADEQUATE_MICROCLIMATE_CONFIDENCE
        and checks.get("uncertainty_bounded")
    )


def microclimate_adjustment_supported(checks):
    return (
        checks.get("official_forecast_available")
        and checks.get("microclimate_confidence") in ADEQUATE_MICROCLIMATE_CONFIDENCE
        and checks.get("uncertainty_bounded")
    )


def nearby_observation_supported(checks):
    return checks.get("observation_available") and checks.get("official_forecast_available")


def official_forecast_supported(checks):
    return checks.get("official_forecast_available")


_SUPPORT_CHECKS = {
    "exact_location": exact_location_supported,
    "microclimate_adjusted": microclimate_adjustment_supported,
    "nearby_observation_area": nearby_observation_supported,
    "official_forecast_area": official_forecast_supported,
}


def scope_supported(scope, checks):
    return bool(_SUPPORT_CHECKS[scope](checks))


def highest_supported_scope(checks):
    for scope in SCOPE_SPECIFICITY:
        if scope_supported(scope, checks):
            return scope
    return None


def fallback_scope(requested_scope, checks):
    """Most specific supported scope that is not more specific than requested."""
    started = False
    for scope in SCOPE_SPECIFICITY:
        if scope == requested_scope:
            started = True
        if started and scope_supported(scope, checks):
            return scope
    return None


def unsupported_specific_claim(requested_scope, checks):
    return not scope_supported(requested_scope, checks)


def determine_claim_scope(requested_scope, checks, evidence):
    """Return the ScopeDecision for this request.

    Precedence: an active official alert governs everything; otherwise grant
    the requested scope if supported, otherwise degrade gracefully to the
    highest supported scope below it; abstain only when nothing is supported.
    """
    if official_alert_governs(evidence):
        return {
            "requested_scope": requested_scope,
            "claim_scope": "official_alert_only",
            "scope_reason_codes": [ALERT_SCOPE_REASON_CODE],
            "fallback_applied": False,
        }

    if scope_supported(requested_scope, checks):
        return {
            "requested_scope": requested_scope,
            "claim_scope": requested_scope,
            "scope_reason_codes": [SCOPE_SUPPORTED_REASON_CODES[requested_scope]],
            "fallback_applied": False,
        }

    granted = fallback_scope(requested_scope, checks)
    if granted is not None:
        return {
            "requested_scope": requested_scope,
            "claim_scope": granted,
            "scope_reason_codes": [
                SCOPE_SUPPORTED_REASON_CODES[granted],
                UNSUPPORTED_REASON_CODE,
            ],
            "fallback_applied": True,
        }

    return {
        "requested_scope": requested_scope,
        "claim_scope": "unsupported_specific_claim",
        "scope_reason_codes": [UNSUPPORTED_REASON_CODE],
        "fallback_applied": False,
    }
