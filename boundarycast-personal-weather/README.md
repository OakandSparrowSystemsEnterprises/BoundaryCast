# BoundaryCast Personal Weather

**Your weather, checked before it speaks.**

BoundaryCast is a governed forecast engine. Before it says anything, it checks the evidence — official forecast, nearby observations, active alerts, microclimate context, freshness, uncertainty, policy — and then makes the most specific claim that evidence supports, with a replayable proof attached.

## What it does

### The most specific forecast the evidence supports
Strong exact-location and microclimate evidence gets you an exact-location forecast. Weaker evidence never means silence — the claim degrades gracefully through explicit tiers (`exact_location → microclimate_adjusted → nearby_observation_area → official_forecast_area`) with full scope disclosure. An active official alert governs everything (`official_alert_only`); a claim nothing supports is refused (`unsupported_specific_claim`), never faked. The Gatekeeper verdict answers *may the system speak?*; the claim scope answers *how specific may it be?*

### A governed oracle recipe for prediction markets
Prediction markets fail when resolution is vague. BoundaryCast turns a market question — metric, operator, threshold, and the market creator's **minimum claim scope** — into YES / NO / UNRESOLVED backed by an evidence-bound artifact. Evidence below the market's minimum scope goes to arbitration with an explicit reason code instead of resolving on a guess. Official alerts supersede condition markets outright. Machine-readable manifest at `GET /api/v1/oracle/recipe`; full semantics in `docs/oracle-recipe.md`.

### Market Factory Lite
The smallest complete market factory around a governed oracle: create weather markets, stake play-money YES/NO into parimutuel pools, resolve with one click, and settle payouts (or arbitration refunds) against the artifact. Walkthrough in `docs/demo-script.md`.

### Zero-cache privacy
No account, no identity, no location history. Location feeds the live request only; artifacts store minimized bindings (synthetic / rounded / grid-hash / not stored) — never raw real coordinates. See `docs/privacy-zero-cache.md`.

### Replayable governance, formally specified
Every decision is a hash-chained artifact citing its evidence roots, policy pack versions, scope decision, and verdict; `scripts/verify_artifacts.py` exits nonzero on tampering. The governance layer is formalized: full OWL ontology (`contracts/boundarycast-weather-ontology-v0.2.ttl`), deontic policy semantics (`docs/deontics.md`), and a complete epistemology spec (`docs/epistemology-scaffold.md`). Proprietary production math loads through a private provider seam (`BOUNDARYCAST_FORESIGHT_PROVIDER`) and never enters this repository.

## Run it

```bash
cd boundarycast-personal-weather
bash scripts/run_no_docker.sh        # Windows: .\scripts\run_no_docker.ps1
```

Open http://localhost:8787/ui — the pitch deck is at `/ui/pitch.html`. Container deploys: see `Dockerfile` (repo root) and `docs/deploy.md`.

## API

| Endpoint | What it does |
| --- | --- |
| `POST /api/v1/personal-forecast` | Governed personal forecast with claim scope |
| `GET /api/v1/oracle/recipe` | Machine-readable oracle recipe manifest |
| `POST /api/v1/oracle/resolve` | Resolve a market question to YES / NO / UNRESOLVED + artifact |
| `POST /api/v1/markets` · `GET /api/v1/markets` | Create / list demo markets |
| `POST /api/v1/markets/{id}/stake` · `/settle` · `/seed-demo` | Stake, one-click oracle settlement, seed the board |
| `GET /api/v1/replay` | Verify the artifact hash chain |
| `GET /health` | Liveness |

## Tests

```bash
cd services/api
pip install -r requirements-dev.txt
python -m pytest tests/
```

45 tests: claim scope and graceful degradation, verdict severity precedence, reason-code/policy-pack alignment, artifact tamper detection, location minimization, oracle resolution semantics, market lifecycle and payouts, plus adversarial hardening (concurrency races, hostile numeric input, oversized payloads, UI injection).

## Honest scope

The weather adapters are deterministic demo stubs; production wires real NWS/observation feeds behind identical governance. The governance itself — epistemology, claim scope, deontic policy, gatekeeper, artifact chain — is fully real and tested.

## Public boundary & license

This repository is public-safe: no QTP, Manifold equations, SIP derivations, production Gatekeeper invariants, claim-altitude math, corridor operators, private OASSE thresholds, policy-pack compiler internals, QuickOps policy packs, or consortium math (`docs/non-public-exclusions.md`).

Proprietary source-available — © 2026 Oak & Sparrow Systems Enterprise LLC; evaluation, demonstration, and judging permitted. See `LICENSE`. An open-source release is planned.
