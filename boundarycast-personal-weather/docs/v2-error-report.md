# BoundaryCast Personal Weather, V2 Error Report

Date: July 11, 2026
Scope: full review of all 60 files, errors fixed and polish applied. Every fix below was verified by live endpoint testing against a running instance.

## Errors found and fixed

### 1. Impossible coordinates accepted (governance defect)
`PersonalForecastRequest` had no bounds on latitude, longitude, or precision. A request with latitude 999 was accepted, marked `location_known: true`, granted `personal_location_language_allowed: true`, and published a personal-location forecast with a hash-chained artifact for a coordinate that does not exist. For a system whose claim is "check before you speak," this was the most serious defect.
Fix: pydantic bounds. Latitude -90 to 90, longitude -180 to 180, precision_meters 1 to 100000. The request now fails schema validation with HTTP 422 before any pipeline stage runs.

### 2. Gatekeeper verdict precedence could downgrade a MUST rule
`evaluate_gatekeeper` only honored an ABSTAIN effect when `knowledge_state == "insufficient"`. If the uncertainty policy (deontic MUST, effect ABSTAIN) fired while knowledge state was "partial", the verdict silently softened to PERMIT_WITH_CAUTION. A policy effect was being overridden by a knowledge-state heuristic.
Fix: strict severity precedence, BLOCK > PROTOCOL > ABSTAIN > PERMIT_WITH_CAUTION > PERMIT. The strictest effect always wins. Knowledge state can tighten the verdict but never loosen it. Regression-tested across all precedence combinations.

### 3. Reason codes drifted from the policy packs the artifact cites
The artifact ledger records `policy_pack_versions` as its authority, but the rule engine emitted codes the packs do not define:
- Engine emitted `not_replayable`; replay-policy-v1 defines `verdict_not_replayable`.
- Engine emitted `evidence_stale_or_partial`; evidence-freshness-policy-v1 defines `observation_stale_or_missing`.
- publication-policy-v1 defines `insufficient_evidence_for_publication`; the engine never emitted it under any condition.
Fix: engine codes now match pack codes one for one, and the insufficient-evidence rule is now enforced (knowledge_state insufficient appends ABSTAIN with the pack's reason code).

### 4. Web UI could never demonstrate medium microclimate confidence
The adapter requires 4 or more known attributes for "medium" confidence, but the form exposed only 3 (surface, shade, urban density). The demo's own UI could not reach the confidence tier the policy pack governs.
Fix: added wind exposure, elevation, and nearby water controls. Medium confidence and a clean PERMIT verdict are now reachable from the browser.

### 5. Web UI had no error handling
A failed fetch or a 422 rejection left the page stuck on "Checking evidence, policy, and artifact path..." with the error visible only in the console. Empty numeric inputs became NaN and were submitted silently.
Fix: client-side coordinate validation with a visible message, HTTP error responses rendered in the result card, network failures caught and displayed, the run button disabled during flight, NaN inputs converted to null.

### 6. verify_artifacts.py always exited 0
The script printed a raw dict and returned success even when the chain failed verification, making it useless as a CI gate or scripted check.
Fix: readable output plus exit code 1 on failure. Verified against a deliberately tampered ledger: clean chain exits 0, tampered chain reports the hash mismatch and exits 1.

### 7. Bare host returned 404
README instructs opening http://localhost:8787/ui but the root path served nothing.
Fix: `GET /` now redirects (307) to `/ui/`.

### 8. Missing package init files
Eight subpackages (adapters, artifacts, epistemology, foresight_proxy, gatekeeper_lite, models, ontology, policy) had no `__init__.py`. Imports worked through implicit namespace packages but the layout was fragile under packaging tools, zip imports, and some analyzers.
Fix: `__init__.py` added to all eight.

## Polish applied

- **Dead modules wired in.** `evidence_score.py` and `uncertainty.py` were never imported; the epistemology output now carries `evidence_score` and `uncertainty`. `risk_window.py` and `trend_detector.py` were never imported; the claim now carries a `public_proxy` block built from them, which makes the public-boundary markers visible in every response instead of sitting unused.
- **UI surfaces the epistemology.** Evidence score and uncertainty label now render as pills alongside confidence and knowledge state.
- **index.html asset paths made relative** so the page works regardless of mount path.
- **Numeric inputs typed** with min/max/step attributes matching the schema bounds.
- **run_no_docker.sh** guards venv creation instead of recreating it on every run.
- **artifacts/.gitkeep** added so the ledger directory exists in a fresh clone (matching the existing .gitignore pattern `artifacts/*.ndjson`).
- **Disabled-button style** added for the in-flight state.

## Verified end to end

Boot, root redirect, /ui/ serving, /health, full-pipeline forecast (PERMIT with medium confidence), minimal forecast (PERMIT_WITH_CAUTION with pack-aligned reason code), coordinate rejection (422), out-of-window forecast_hours rejection (422), replay chain verification over multiple artifacts, tamper detection with correct exit codes, and full compileall across the package.

## Not changed

Adapters remain demo stubs by design, the public boundary in docs/non-public-exclusions.md is respected, no private math was added, README and docs text untouched, policy pack JSON untouched (the engine was aligned to the packs, not the reverse).
