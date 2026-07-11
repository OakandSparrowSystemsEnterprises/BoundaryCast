# Stage Demo Script (3 minutes)

**Open on the Market Board.** Click **Seed demo markets** before judges arrive — three markets appear: rain at an outdoor event, wind on a delivery route, heat at a job site, each with YES/NO pools and implied odds.

**Say:** "Prediction markets fail when resolution is vague. BoundaryCast makes weather markets resolvable by turning a local weather claim into an evidence-bound, scope-aware, replayable oracle artifact."

## Beat 1 — one-click resolution (45s)

Stake 10 on NO in the rain market. Click **Resolve with BoundaryCast**.

Point at the resolution: NO (firm), the gatekeeper verdict, the claim scope, the reason codes, the artifact hash, the payouts splitting the pool, and the replay line: *artifact chain verified*.

**Say:** "The market didn't trust me, it trusted the oracle recipe: evidence checked, claim scope granted, verdict issued, artifact hash-chained."

## Beat 2 — the oracle refuses to over-claim (45s)

In the **Forecast Future Weather** panel, set **minimum resolution scope: exact location**, clear the microclimate fields, resolve the temp market.

**UNRESOLVED → arbitration** (`scope_below_market_minimum`).

**Say:** "The market creator's minimum claim scope is the resolution rule. When the evidence only supports an area-level claim, the oracle refuses to resolve and says exactly why. It never pretends."

## Beat 3 — official alert supremacy (45s)

Flip **Demo scenario → active official alert**. Resolve the alert market in the **Forecast Future Weather** panel: **YES (official)**. Then settle a condition market on the board: **UNRESOLVED — official_alert_governs**, stakes refunded.

**Say:** "Official alerts govern. BoundaryCast never resolves a condition market from under an alert it must not soften."

## Beat 4 — the receipts (30s)

Show `GET /api/v1/replay` (or the replay line) and mention `scripts/verify_artifacts.py` exits nonzero on tampering. Show `GET /api/v1/oracle/recipe` — the machine-readable manifest any market factory can list.

**Close:** "Anyone can create a weather-dependent market. Not everyone can write safe resolution rules. Our oracle recipe packages the resolution logic — what evidence counts, when alerts govern, when the claim is exact versus area-level, and when the oracle must abstain."

## If asked "is the microclimate math real?"

"The demo adapters are stubs and the public repo carries a public proxy — the governance layer is fully real and tested. The production foresight math is proprietary and loads through a private provider seam at runtime; it never touches the public repository."
