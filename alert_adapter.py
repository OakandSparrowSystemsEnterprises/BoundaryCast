from .verdicts import PRODUCT_VERDICTS

SEVERITY = ["PERMIT", "PERMIT_WITH_CAUTION", "ABSTAIN", "PROTOCOL", "BLOCK"]


def _strictest(candidates):
    return max(candidates, key=SEVERITY.index)


def evaluate_gatekeeper(evidence, epistemology, policy_result, claim):
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

    return {
        "gatekeeper_verdict": verdict,
        "product_verdict": PRODUCT_VERDICTS[verdict],
        "reason_codes": policy_result.get("reason_codes", []),
        "microclimate_confidence": claim.get("microclimate_confidence"),
        "artifact_required": True,
    }
