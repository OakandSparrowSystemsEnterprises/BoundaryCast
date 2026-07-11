# BoundaryCast Oracle Recipe

BoundaryCast turns local weather into a governed, replayable oracle for prediction markets.

## The problem

Prediction markets fail when resolution is vague. "Will it rain at the event?" needs an answer that is specific about *where*, honest about *how much evidence supports it*, and auditable after the fact. Weather data is easy; **resolution integrity** is the hard part.

## The recipe

A market creator writes a resolution rule like:

> This market resolves using the BoundaryCast Oracle Recipe. Exact-location claim if supported; otherwise the market's minimum scope applies; official alerts supersede; unsupported claims go to arbitration.

At resolution time, anyone calls:

```
POST /api/v1/oracle/resolve
{
  "market_id": "market_demo_001",
  "question": "Will the temperature exceed 100°F at this job site today?",
  "metric": "temperature_f",         // temperature_f | wind_mph | precip_probability | alert_active
  "operator": "gt",                  // gt | gte | lt | lte
  "threshold": 100,
  "minimum_scope": "nearby_observation_area",
  "latitude": 37.7974,
  "longitude": -121.2161,
  "precision_meters": 25,
  "forecast_hours": 12
}
```

BoundaryCast runs its full governed pipeline — evidence, epistemology, claim scope, policy packs, Gatekeeper-Lite, hash-chained artifact — and returns a resolution record.

## Resolution semantics

| Pipeline outcome | Market resolution |
| --- | --- |
| `PROTOCOL` (official alert governs) + `alert_active` market | **YES** (alert-first, confidence `official`) |
| `PROTOCOL` + condition market | **UNRESOLVED** → arbitration (the oracle does not read condition values from under an official alert) |
| `ABSTAIN` / `BLOCK` | **UNRESOLVED** → arbitration (`insufficient_evidence`) |
| Claim scope below the market's `minimum_scope` | **UNRESOLVED** → arbitration (`scope_below_market_minimum`) |
| `PERMIT` / `PERMIT_WITH_CAUTION`, scope meets minimum | **YES** or **NO** from the claim's published value (confidence `firm` / `qualified`) |

The market creator's `minimum_scope` **is** the resolution rule: a hyperlocal event market can demand `exact_location` or `microclimate_adjusted`; a regional market can accept `official_forecast_area`. The oracle never silently substitutes a vaguer claim — if the evidence only supports a scope below the minimum, the market goes to its arbitration path, explicitly.

## Every resolution is a replayable record

Each resolution embeds the decision artifact: evidence root, claim root, policy pack versions, gatekeeper verdict, claim scope, scope reason codes, and hash chained to the previous artifact. `GET /api/v1/replay` (or `scripts/verify_artifacts.py`, which exits nonzero on tampering) verifies the chain. Disputes replay the record instead of re-arguing the weather.

Zero-cache applies to oracle calls too: artifacts carry a minimized location binding, never raw real coordinates (see `docs/privacy-zero-cache.md`).

## Example markets this resolves

- "Will it rain at this outdoor event between 2 and 5 PM?" — `precip_probability gt 0.5`, `minimum_scope: microclimate_adjusted`
- "Will wind exceed 25 mph at this delivery route checkpoint?" — `wind_mph gt 25`, `minimum_scope: nearby_observation_area`
- "Will the temperature at this job site exceed 100°F today?" — `temperature_f gt 100`, `minimum_scope: nearby_observation_area`
- "Will an official weather alert be active for this location?" — `alert_active`

## What this is not

This is not a price feed, not private forecasting math, and not a replacement for official alerts. The demo adapters are stubs; production would wire real NWS/observation adapters behind the same governance. The oracle's value is the governance: it states the most specific claim the evidence supports, and refuses — visibly, with reason codes — to state more.
