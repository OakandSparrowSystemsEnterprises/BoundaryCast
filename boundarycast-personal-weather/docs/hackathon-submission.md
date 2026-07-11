# Submission: BoundaryCast Weather Oracle Recipe

**One-liner:** BoundaryCast turns local weather into a governed, replayable oracle for prediction markets.

**Idea fit:** #1 Permissionless Market Factory with Oracle Recipes (primary), #11 Local City Prediction Markets and #5 Startup Founder Hedge Markets (secondary — weather drives events, delivery, construction, agriculture, outdoor ops).

## The problem

Prediction markets fail when resolution is vague. Weather markets are the worst case: "Will it rain at the event?" needs an answer that is specific about *where*, honest about *how much evidence supports that specificity*, and auditable after the fact. Weather data is a commodity. **Resolution integrity is not.**

## What we built

A weather oracle recipe with governance at its core:

1. **Claim Scope** — the oracle states how specific its claim is (`exact_location` → `microclimate_adjusted` → `nearby_observation_area` → `official_forecast_area`), and the market creator's `minimum_scope` **is the resolution rule**. Evidence below the minimum never silently resolves — it escalates to arbitration with a reason code.
2. **Gatekeeper verdicts** — the system decides whether it may speak at all (`PERMIT`, `PERMIT_WITH_CAUTION`, `ABSTAIN`, `PROTOCOL`, `BLOCK`) with strict severity precedence. Official alerts supersede condition markets outright.
3. **Replayable resolution artifacts** — every resolution is bound to a hash-chained decision artifact (evidence root, claim root, policy pack versions, claim scope, verdict). Disputes replay the record; tampering is detected and exits nonzero.
4. **Zero-cache privacy** — no identity, no location history; artifacts carry minimized location bindings only.

## Endpoints

- `GET /api/v1/oracle/recipe` — machine-readable recipe manifest a market factory can list
- `POST /api/v1/oracle/resolve` — market question in, YES / NO / UNRESOLVED + replayable artifact out
- `POST /api/v1/personal-forecast` — the underlying governed personal forecast
- `GET /api/v1/replay` — verify the artifact chain

## Demo flow (3 minutes)

1. Normal evidence → "temp > 100°F at this job site" resolves **NO (firm, exact-location basis)**.
2. Raise the market's minimum scope to exact-location with weak evidence → **UNRESOLVED → arbitration** (`scope_below_market_minimum`). The oracle refuses to over-claim.
3. Flip on the official-alert scenario → alert market resolves **YES (official)**; the temp market goes **UNRESOLVED** because the oracle won't resolve from under an official alert.
4. Show the artifact hash + replay verification.

## Honest scope

Weather adapters are demo stubs (synthetic data, deterministic); production wires real NWS/observation feeds behind identical governance. The governance layer — scope decision, policy packs, gatekeeper, artifact chain, 24 passing tests — is fully real.
