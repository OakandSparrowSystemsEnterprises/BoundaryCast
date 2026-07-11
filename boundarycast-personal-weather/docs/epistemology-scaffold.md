# Epistemology

BoundaryCast asks whether it knows enough to speak — and *how specifically* it may speak. This document is the formal specification of that layer as implemented in `boundarycast_api/epistemology/` and expressed in OWL in `contracts/boundarycast-weather-ontology-v0.2.ttl`.

The epistemology is a function from an evidence bundle to a **check vector**, a **knowledge state**, an **evidence score**, an **uncertainty label**, and a set of **scope-support predicates**. It never mutates evidence and it is deterministic: identical evidence yields identical knowledge, which is what makes verdicts replayable.

## 1. Epistemic checks (the check vector)

Each check is a named boolean over the evidence bundle `E = (location, microclimate, official_forecast, observation, alerts)` and the request `R`.

| Check | Formal condition | Failure meaning |
| --- | --- | --- |
| `SchemaValid` | request passed schema validation (enforced upstream; requests failing bounds never reach the pipeline) | malformed input — BLOCK territory |
| `LocationKnown` | `R.latitude ≠ null ∧ R.longitude ≠ null` | no place to make a claim about |
| `LocationPreciseEnough` | `R.precision_meters ≤ 100` | personal-location language not permitted |
| `OfficialForecastAvailable` | `E.official.available = true` | no official product to anchor any claim |
| `ObservationAvailable` | `E.observation.available = true` | no nearby ground truth |
| `EvidenceFresh` | `E.official.freshness_minutes ≤ 60 ∧ E.observation.freshness_minutes ≤ 90` (null-valued freshness fails) | stale evidence cannot support present-tense claims |
| `SourceKnown` | all three sources carry a `source_name` | unattributable evidence is not evidence |
| `ObservationDistanceAcceptable` | `E.observation.distance_km ≤ 10` (null fails) | observation too far to speak for this location |
| `ForecastGridDistanceKnown` | `E.official.grid_distance_km ≠ null` | unknown grid displacement |
| `OfficialAlertChecked` | `E.alerts.available = true` | alerts were not consulted — never publish without checking |
| `MicroclimateContextKnown` | `microclimate_confidence ∉ {null, unsupported}` | no basis for local adjustment |
| `MicroclimateConfidenceBounded` | `microclimate_confidence ∈ {low, low-medium, medium, high}` (carried as the value itself) | confidence tier drives scope support |
| `UncertaintyBounded` | `OfficialForecastAvailable ∧ ObservationAvailable` | without both anchors, personal-scope uncertainty is unbounded |
| `ClaimInsideForecastWindow` | `R.forecast_hours ≤ 72` | beyond the window, no claim |
| `PolicyPackActive` | at least one policy pack loaded | ungoverned speech is not permitted |
| `VerdictReplayable` | artifact path writable and hash chain intact | unreplayable verdicts are blocked |

Microclimate confidence is derived in the adapter: `known` = count of non-null attributes among {surface, shade, elevation, wind, water, urban density}; `known ≥ 4 → medium`, `known ≥ 2 → low-medium`, else `low`.

## 2. Knowledge state (derivation rule)

Let `HardRequired = {SchemaValid, LocationKnown, OfficialForecastAvailable, SourceKnown, OfficialAlertChecked, ClaimInsideForecastWindow}`.

```
knowledge_state =
  sufficient    if ∀c ∈ HardRequired: c ∧ EvidenceFresh ∧ UncertaintyBounded
  partial       else if OfficialForecastAvailable ∧ SourceKnown
  insufficient  otherwise
```

Knowledge state maps to a *recommended* gatekeeper posture (`sufficient → PERMIT`, `partial → PERMIT_WITH_CAUTION`, `insufficient → ABSTAIN`). It is advisory tightening only: policy effects with stricter severity always win, and knowledge state can never loosen them (see `docs/deontics.md`).

## 3. Evidence score

`evidence_score = |{c : c is boolean check ∧ c = true}| / |boolean checks|`, rounded to 3 places. It is a transparency metric for the UI and artifact — never a decision input. Decisions use the named checks, not the aggregate, so a high score can never launder a failed hard requirement.

## 4. Uncertainty label

```
uncertainty =
  bounded             if knowledge_state = sufficient
  partially_bounded   if knowledge_state = partial
  unbounded           otherwise
```

## 5. Scope-support predicates (v3)

Claim scope is decided by predicates over the check vector (`epistemology/claim_scope.py`), ordered by specificity `exact_location > microclimate_adjusted > nearby_observation_area > official_forecast_area`:

```
exact_location_supported          ⟺ LocationPreciseEnough ∧ OfficialForecastAvailable
                                    ∧ ObservationAvailable ∧ EvidenceFresh
                                    ∧ microclimate_confidence ∈ {medium, high}
                                    ∧ UncertaintyBounded
microclimate_adjustment_supported ⟺ OfficialForecastAvailable
                                    ∧ microclimate_confidence ∈ {medium, high}
                                    ∧ UncertaintyBounded
nearby_observation_supported      ⟺ ObservationAvailable ∧ OfficialForecastAvailable
official_forecast_supported       ⟺ OfficialForecastAvailable
official_alert_governs            ⟺ E.alerts.active_alert_count > 0
unsupported_specific_claim(s)     ⟺ ¬supported(s)   for requested scope s
```

Decision procedure `determine_claim_scope(requested, checks, E)`:

1. If `official_alert_governs` → `official_alert_only` (alert supremacy; not a fallback).
2. Else if `supported(requested)` → grant `requested`.
3. Else → `fallback_scope(requested)` = the most specific supported scope *not more specific than requested*; grant it with `fallback_applied = true` and the `unsupported_specific_claim` reason code alongside the granted scope's support code.
4. Else (nothing supported) → `unsupported_specific_claim`; the rule engine converts this to an ABSTAIN effect.

Two invariants follow: **a granted scope always has a true support predicate behind it** (no scope is ever granted on vibes), and **degradation is monotone** (a fallback is never more specific than the request, and never less specific than the best supported scope below it).

## 6. Epistemic honesty principle

A claim may be true-looking but still not publishable if evidence is missing, stale, distant, over-specific, or not replayable. And a publishable claim may still not be publishable *at the requested specificity* — that is what the scope predicates decide. The system's obligation is not to answer; it is to answer exactly as specifically as it knows.
