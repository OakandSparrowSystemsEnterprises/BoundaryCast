# BoundaryCast Personal Weather (v3)

BoundaryCast is your weather, checked before it speaks. It travels with you and gives the most specific forecast claim the evidence supports, from exact-location weather down to official-area guidance, without pretending and without storing your location history.

It does not try to out-Windy Windy. Instead, it improves on static weather pages by evaluating what can responsibly be said about the weather at an individual user's exact location: official forecasts, observations, alerts, microclimate context, evidence freshness, uncertainty, and policy rules are all checked before publishing a forecast verdict. Every decision is bound to a replayable artifact.

## What's new in v3

- **Claim Scope** — a graceful-degradation layer (`exact_location`, `microclimate_adjusted`, `nearby_observation_area`, `official_forecast_area`, `official_alert_only`, `unsupported_specific_claim`). The verdict answers *may the system speak?*; the scope answers *how specific may it be?* See `docs/v3-claim-scope-and-zero-cache.md`.
- **Zero-cache privacy** — no account, no identity, no location history; artifacts carry a minimized location binding, never raw real coordinates. See `docs/privacy-zero-cache.md`.
- **Oracle Recipe** — the same governed claim resolves weather-dependent prediction markets: `POST /api/v1/oracle/resolve` maps a market question (metric, operator, threshold, minimum claim scope) onto YES / NO / UNRESOLVED with an embedded replayable resolution artifact. Official alerts supersede; insufficient evidence escalates to arbitration instead of pretending. See `docs/oracle-recipe.md`.
- **Market Factory Lite** — a play-money parimutuel market board that settles exclusively through the oracle: create, stake, one-click "Resolve with BoundaryCast", payouts or arbitration refunds, artifact hash and replay status on every resolution. See `docs/demo-script.md`.
- **Formal layer** — full OWL ontology (`contracts/boundarycast-weather-ontology-v0.2.ttl`), formal deontics (`docs/deontics.md`), and the complete epistemology specification (`docs/epistemology-scaffold.md`). A private foresight provider seam (`BOUNDARYCAST_FORESIGHT_PROVIDER`) lets production load proprietary math at runtime without it ever entering this repository.

## Public boundary

This repository is public-safe. It does not include QTP, full Manifold equations, SIP constitutional derivations, production Gatekeeper invariants, claim-altitude math, universal corridor operators, private OASSE thresholds, enterprise policy-pack compiler internals, QuickOps labor/cash/safety policy packs, or consortium math.

## Stack

User Exact Location -> Microclimate Context -> Public Weather Evidence -> Weather Ontology -> Epistemology Scaffold -> Claim Scope Decision -> Policy Packs -> Gatekeeper-Lite -> Forecast Verdict -> Artifact Ledger -> Replay Verification.

## Run no Docker

```powershell
cd boundarycast-personal-weather
.\scripts\run_no_docker.ps1
```

Or on macOS/Linux:

```bash
cd boundarycast-personal-weather
bash scripts/run_no_docker.sh
```

Then open http://localhost:8787/ui

## Demo endpoints

- `GET /health`
- `POST /api/v1/personal-forecast`
- `GET /api/v1/oracle/recipe`
- `POST /api/v1/oracle/resolve`
- `POST /api/v1/markets` · `GET /api/v1/markets` · `POST /api/v1/markets/{id}/stake` · `POST /api/v1/markets/{id}/settle` · `POST /api/v1/markets/seed-demo`
- `GET /api/v1/replay`

## License

Proprietary source-available — Copyright (c) 2026 Oak & Sparrow Systems Enterprise LLC, all rights reserved; evaluation, demonstration, and hackathon judging permitted. See `LICENSE`. An open-source release is planned.

## Tests

```bash
cd services/api
pip install -r requirements-dev.txt
python -m pytest tests/
```

24 tests cover claim scope, graceful degradation, severity precedence, reason-code/pack alignment, artifact chain tamper detection, location minimization, and oracle market-resolution semantics.
