# Deontics

BoundaryCast's policy layer is deontic: every rule carries a normative force, an effect verdict, and a reason code. This document is the formal specification of that layer as implemented in `policy/rule_engine.py` + `gatekeeper_lite/evaluator.py`, published in `examples/policy-packs/*.json`, and expressed in OWL in `contracts/boundarycast-weather-ontology-v0.2.ttl`.

## Operators

| Operator | Force | On failure / satisfaction |
| --- | --- | --- |
| `MUST` | Obligation | Failure emits the rule's effect verdict (typically `ABSTAIN`, `PROTOCOL`, or `BLOCK`) with the rule's reason code. Cannot be loosened by anything downstream. |
| `MUST_NOT` | Prohibition | The condition may never hold in a published claim; violation emits the effect verdict. |
| `SHOULD` | Recommendation | Failure tightens to `PERMIT_WITH_CAUTION` with the rule's reason code. Never blocks alone. |
| `MAY` | Permission | Grants an allowance when the condition holds — claim-scope rules are `MAY` rules: they permit a specificity tier, they never force publication. |

## Severity precedence (the never-loosen invariant)

Verdict candidates from all fired rules combine by strict severity:

```
BLOCK(5) > PROTOCOL(4) > ABSTAIN(3) > PERMIT_WITH_CAUTION(2) > PERMIT(1)
```

The final verdict is the maximum severity among fired effects and the knowledge-state recommendation. Two invariants, both regression-tested:

1. **Knowledge state may tighten, never loosen.** `insufficient` adds `ABSTAIN`, `partial` adds `PERMIT_WITH_CAUTION` as candidates — but a friendlier knowledge state removes nothing.
2. **A MUST effect is never downgraded.** No heuristic, scope fallback, or score outranks a fired obligation.

## Deontic–scope interaction

Verdict and scope are separate judgments (may I speak? / how specifically?). The deontic layer binds them at two points:

- **Alert supremacy (`MUST`, official-alert-policy):** an active official alert forces `PROTOCOL` and claim scope `official_alert_only`. Nothing softens an alert.
- **Unsupported claim (`MUST_NOT`, claim-scope-policy rule 6):** the system must not publish a requested personal-scope claim the evidence does not support. Satisfaction is graceful: fall back to the highest supported scope (`MAY` rules 2–5); only when no scope is supported does the effect `ABSTAIN` fire with reason `unsupported_specific_claim`.

## Reason-code discipline

Every emitted reason code must be defined by a rule in an active policy pack — the engine is aligned to the packs, never the reverse (v2 fix #3, still regression-enforced). The artifact ledger records `policy_pack_versions`, so a replayed artifact cites the exact normative basis it was decided under.
