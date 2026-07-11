# Architecture

BoundaryCast is a public-safe governed decision loop:

1. Exact user location
2. Microclimate context
3. Official forecast and observation evidence
4. Weather ontology
5. Epistemology checks
6. Claim scope decision
7. Policy packs
8. Gatekeeper-Lite verdict
9. Artifact creation (zero-cache, minimized location binding)
10. Replay verification

The system may publish, publish with caution, abstain, route to official-alert protocol, or block malformed/unsupported claims.

## Verdict and claim scope are separate

Gatekeeper-Lite governs **whether the system may speak**. Claim Scope governs **how specific the system may be**.

- The verdict answers: may the system speak? (`PERMIT`, `PERMIT_WITH_CAUTION`, `ABSTAIN`, `PROTOCOL`, `BLOCK`)
- The claim scope answers: how specific may the claim be? (`exact_location`, `microclimate_adjusted`, `nearby_observation_area`, `official_forecast_area`, `official_alert_only`, `unsupported_specific_claim`)

Typical pairings:

| Verdict | Claim scope |
| --- | --- |
| PERMIT | exact_location |
| PERMIT / PERMIT_WITH_CAUTION | microclimate_adjusted |
| PERMIT_WITH_CAUTION | nearby_observation_area |
| PERMIT_WITH_CAUTION | official_forecast_area |
| PROTOCOL | official_alert_only |
| ABSTAIN | unsupported_specific_claim |
| BLOCK | malformed/invalid request (rejected before the pipeline) |

Strict severity precedence remains: `BLOCK > PROTOCOL > ABSTAIN > PERMIT_WITH_CAUTION > PERMIT`. Knowledge state can tighten a verdict but never loosen a stricter policy result.

An unsupported exact/personal claim does not mean total abstention. It means "do not make that specific claim": the system falls back to the highest supported claim scope, and abstains only when no supported scope exists at all.
