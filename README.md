BoundaryCast Personal Weather (v3)
BoundaryCast is your weather, checked before it speaks. It travels with you and gives the most specific forecast claim the evidence supports, from exact-location weather down to official-area guidance, without pretending and without storing your location history.

It does not try to out-Windy Windy. Instead, it improves on static weather pages by evaluating what can responsibly be said about the weather at an individual user's exact location: official forecasts, observations, alerts, microclimate context, evidence freshness, uncertainty, and policy rules are all checked before publishing a forecast verdict. Every decision is bound to a replayable artifact.

What's new in v3
Claim Scope — a graceful-degradation layer (exact_location, microclimate_adjusted, nearby_observation_area, official_forecast_area, official_alert_only, unsupported_specific_claim). The verdict answers may the system speak?; the scope answers how specific may it be? See docs/v3-claim-scope-and-zero-cache.md.
Zero-cache privacy — no account, no identity, no location history; artifacts carry a minimized location binding, never raw real coordinates. See docs/privacy-zero-cache.md.
Public boundary
This repository is public-safe. It does not include QTP, full Manifold equations, SIP constitutional derivations, production Gatekeeper invariants, claim-altitude math, universal corridor operators, private OASSE thresholds, enterprise policy-pack compiler internals, QuickOps labor/cash/safety policy packs, or consortium math.

Stack
User Exact Location -> Microclimate Context -> Public Weather Evidence -> Weather Ontology -> Epistemology Scaffold -> Claim Scope Decision -> Policy Packs -> Gatekeeper-Lite -> Forecast Verdict -> Artifact Ledger -> Replay Verification.

Run no Docker
cd boundarycast-personal-weather
.\scripts\run_no_docker.ps1
Or on macOS/Linux:

cd boundarycast-personal-weather
bash scripts/run_no_docker.sh
Then open http://localhost:8787/ui

Demo endpoints
GET /health
POST /api/v1/personal-forecast
GET /api/v1/replay
Tests
cd services/api
pip install -r requirements-dev.txt
python -m pytest tests/
13 regression tests cover claim scope, graceful degradation, severity precedence, reason-code/pack alignment, artifact chain tamper detection, and location minimization.
