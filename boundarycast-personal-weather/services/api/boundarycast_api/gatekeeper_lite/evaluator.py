from .verdicts import PRODUCT_VERDICTS

SEVERITY = ["PERMIT", "PERMIT_WITH_CAUTION", "ABSTAIN", "PROTOCOL", "BLOCK"]


def _strictest(candidates):
    return max(candidates, key=SEVERITY.index)


def evaluate_gatekeeper(evidence, epistemology, policy_result, claim, scope_decision):
    effects = policy_result.get("effects", [])

    # Start from policy effects. The strictest effect always wins;
    # a MUST rule is never downgraded by knowledge state.
    candidates = ["PERMIT"] + [e for e in effects if e in SEVERITY]

    # Knowledge state can only tighten the verdict, never loosen it.
    knowledge_state = epistemology.get("knowledge_state")
    if knowledge_state == "insufficient":
        candidates.append("ABSTAIN")
    elif knowledge_state == "partial":
        candidates.append("PERMIT_WITH_CAUTION")

    verdict = _strictest(candidates)

    # Verdict and scope are related but not the same: the verdict answers
    # "may the system speak?", the claim scope answers "how specific may it
    # be?". Keep the pairing coherent at the boundaries: an official alert
    # protocol always publishes alert-first, and a verdict that withholds
    # publication never carries a publishable scope.
    claim_scope = scope_decision.get("claim_scope")
    scope_reason_codes = list(scope_decision.get("scope_reason_codes", []))
    if verdict == "PROTOCOL":
        claim_scope = "official_alert_only"
        if "official_alert_scope_governs" not in scope_reason_codes:
            scope_reason_codes.append("official_alert_scope_governs")
    elif verdict in ("ABSTAIN", "BLOCK") and claim_scope != "unsupported_specific_claim":
        claim_scope = "unsupported_specific_claim"
        if "unsupported_specific_claim" not in scope_reason_codes:
            scope_reason_codes.append("unsupported_specific_claim")

    return {
        "gatekeeper_verdict": verdict,
        "product_verdict": PRODUCT_VERDICTS[verdict],
        "reason_codes": policy_result.get("reason_codes", []),
        "claim_scope": claim_scope,
        "requested_scope": scope_decision.get("requested_scope"),
        "scope_reason_codes": scope_reason_codes,
        "fallback_applied": bool(scope_decision.get("fallback_applied")),
        "microclimate_confidence": claim.get("microclimate_confidence"),
        "artifact_required": True,
    }
