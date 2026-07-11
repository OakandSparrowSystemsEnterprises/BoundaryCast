# Privacy: Zero-Cache Posture

BoundaryCast uses a zero-cache posture for personal location. Your weather is checked at the moment you ask, and your position is not turned into a record of where you have been.

## Commitments

- **No account.** There is no signup, login, or user profile.
- **No identity.** The system does not persist names, emails, phone numbers, addresses, or account IDs.
- **No location history.** Exact location is used only to evaluate the live forecast request. It is not stored, queued, or accumulated across requests.
- **Live request only.** Location, microclimate inputs, and evidence are held in memory for the duration of one forecast evaluation.
- **Minimized artifact location binding.** Decision artifacts are durable (they make verdicts replayable), so they never contain raw exact real-world coordinates. Each artifact carries a `location_binding_type` of:
  - `synthetic` — demo/synthetic coordinates, safe to store as-is;
  - `rounded` — coordinates rounded to ~1 km cells, with a coarse grid hash, sufficient for replay without identifying a person's exact position;
  - `grid_hash` — a hashed grid-cell reference only;
  - `not_stored` — no location binding at all.
- **Demo data should be synthetic or rounded.** Anything committed to this repository as an example (sample artifacts, tenant files, UI defaults) uses synthetic or rounded coordinates only.

## What replay needs, and what it does not

Replay verification needs the hash chain, the evidence and claim roots, the policy pack versions, and the verdict — not your exact coordinates. The minimized binding exists so a replayed artifact can be tied to a coarse area without ever reconstructing a movement log.
