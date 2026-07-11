# BoundaryCast v3: Claim Scope and Zero-Cache

Date: July 11, 2026
Scope: v3 built on the verified v2-fixed base. Every change below is covered by the regression suite in `services/api/tests/` (13 tests, all passing against a live TestClient pipeline).

## Claim Scope added

A `claim_scope` enum now travels with every claim, verdict, and artifact:

- `exact_location` — precise location, fresh official forecast, adequate nearby observation support, sufficient microclimate context, bounded uncertainty.
- `microclimate_adjusted` — enough microclimate context to responsibly adjust/qualify the official forecast, but the claim is not absolute.
- `nearby_observation_area` — nearby observation support without enough exact-location/microclimate context; shown with caution.
- `official_forecast_area` — official forecast available but insufficient local evidence; the general grid/area forecast is shown with scope disclosure.
- `official_alert_only` — an official alert governs; alert-first information, never overridden or softened.
- `unsupported_specific_claim` — the requested specific claim is not evidence-supported and no supported scope exists.

Support checks live in `boundarycast_api/epistemology/claim_scope.py` (`determine_claim_scope`, `highest_supported_scope`, `fallback_scope`, `exact_location_supported`, `microclimate_adjustment_supported`, `nearby_observation_supported`, `official_forecast_supported`, `official_alert_governs`, `unsupported_specific_claim`). The rules are published in `examples/policy-packs/claim-scope-policy.json`.

## Graceful degradation added

An unsupported exact/personal request no longer implies total abstention. It means "do not make that specific claim": the system falls back to the highest supported claim scope and discloses the fallback (`fallback_applied: true`, with `unsupported_specific_claim` recorded in `scope_reason_codes`). The system abstains only when no supported scope exists at all.

The uncertainty policy was versioned to 1.1.0 to match: unbounded uncertainty still forbids personal-scope claims outright (`ABSTAIN`), but a gracefully degraded area claim may publish with caution (`uncertainty_partially_bounded`), because the claim being made is the official product, not a personal adjustment.

## Verdict/scope separation added

Gatekeeper-Lite still returns `PERMIT / PERMIT_WITH_CAUTION / ABSTAIN / PROTOCOL / BLOCK` and now also returns `claim_scope` and `scope_reason_codes`. The verdict answers "may the system speak?"; the claim scope answers "how specific may the system be?". Strict severity precedence is unchanged (`BLOCK > PROTOCOL > ABSTAIN > PERMIT_WITH_CAUTION > PERMIT`) and knowledge state can tighten but never loosen a policy result. See `docs/architecture.md`.

## Zero-cache privacy posture added

No account, no identity, no location history. Location is used for the live forecast request only. See `docs/privacy-zero-cache.md`.

## Location minimization added

Durable artifacts never store raw exact real-world coordinates. Every artifact carries `location_binding_type` (`synthetic` | `rounded` | `grid_hash` | `not_stored`), a minimized `location_binding_value`, `zero_cache: true`, and `privacy_notes`. Demo/synthetic coordinates may be stored as-is; real-mode requests are bound to ~1 km rounded coordinates plus a coarse grid hash (`boundarycast_api/artifacts/location_minimization.py`).

## Schema and ontology updates

- Claim now includes: `requested_scope`, `claim_scope`, `scope_reason_codes`, `fallback_applied`, `public_message`, `microclimate_confidence`, `uncertainty_label`, `evidence_score`.
- Artifact now includes: `claim_scope`, `requested_scope`, `fallback_applied`, `scope_reason_codes`, `location_binding_type`, `location_binding_value`, `zero_cache`, `privacy_notes`, plus the existing `evidence_root`, `claim_root`, `policy_pack_versions`, `gatekeeper_verdict`, `product_verdict`, `reason_codes`, `artifact_hash`, `previous_hash`.
- Ontology v0.2 adds: `ClaimScope`, `ScopeDecision`, `ScopeReasonCode`, `PersonalForecastContext`, `LocationMinimization`, `LocationHash`, `ZeroCachePolicy`.
- New contract: `contracts/scope-decision.schema.json`.

## UI updates

The UI says **YOUR WEATHER** and shows Forecast Verdict, Forecast Scope, Location Specificity, Microclimate Confidence, Evidence Score, Uncertainty, Official Alert, "Why this scope?", and Artifact Status, with explicit copy when a fallback was applied. Demo scenario switches make every scope tier reachable from the browser.

## Regression coverage

1. Invalid latitude/longitude returns a schema validation error, not a forecast.
2. Active official alert produces `PROTOCOL + official_alert_only`.
3. Strong exact evidence produces `PERMIT + exact_location`.
4. Medium microclimate evidence produces `PERMIT` or `PERMIT_WITH_CAUTION` + `microclimate_adjusted`.
5. Missing microclimate with an available official forecast produces `official_forecast_area`, not total abstention.
6. A requested exact forecast without sufficient exact evidence falls back to the highest supported scope.
7. No official forecast and no observation produces `ABSTAIN + unsupported_specific_claim`.
8. Gatekeeper severity precedence cannot be loosened.
9. Emitted reason codes all match codes defined in the policy packs.
10. The artifact chain verifies.
11. A tampered artifact chain exits nonzero.
12. Artifacts do not persist raw exact real lat/lon unless synthetic/demo mode is explicit.
13. The UI shows claim scope and the fallback explanation.

## No private stack added

No QTP, Manifold equations, SIP derivations, production Gatekeeper invariants, claim-altitude math, corridor operators, private OASSE thresholds, policy-pack compiler internals, artifact sufficiency proofs, QuickOps policy packs, or consortium math. The public boundary in `docs/public-boundary.md` and `docs/non-public-exclusions.md` is unchanged in intent and extended in wording. This repo is BoundaryCast only.
