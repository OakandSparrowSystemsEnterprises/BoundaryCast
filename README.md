# BoundaryCast

**Your weather, checked before it speaks.**

BoundaryCast answers one question most weather products dodge: *how much can you actually trust a forecast for the exact spot you're standing on?* It checks the evidence first — official forecast, nearby observations, active alerts, microclimate context, freshness, uncertainty — and then makes the most specific claim that evidence supports. Nothing more. Every answer ships with a hash-chained, replayable proof of how it was decided.

## What it does

**🎯 Scope-aware personal forecasts.** When the evidence is strong, you get an exact-location forecast. When it isn't, BoundaryCast doesn't go silent and doesn't pretend — it degrades gracefully (microclimate-adjusted → nearby-observation area → official forecast area) and tells you which tier you're getting and why. Official alerts always govern; nothing softens them.

**⚖️ A governed oracle for prediction markets.** The same governed claim resolves weather-dependent markets: "Will it rain at this outdoor event between 2 and 5 PM?" resolves YES / NO / UNRESOLVED against an evidence-bound artifact. The market creator picks the minimum claim scope they'll accept — that *is* the resolution rule. Below it, the oracle refuses and routes to arbitration instead of guessing.

**🏛️ A market factory around the oracle.** Create a market, stake play-money YES/NO into parimutuel pools, click *Resolve with BoundaryCast*, and watch payouts settle against the artifact — outcome, claim scope, reason codes, artifact hash, replay proof.

**🔒 Zero-cache privacy.** No account, no identity, no location history. Your position is used for the live request only; durable artifacts carry a minimized location binding (rounded / grid-hash / synthetic), never your raw coordinates.

**📜 Receipts, always.** Every decision is a hash-chained artifact. Disputes replay the record — and tampering fails verification loudly.

## Try it

```bash
cd boundarycast-personal-weather
bash scripts/run_no_docker.sh        # or .\scripts\run_no_docker.ps1 on Windows
```

Open http://localhost:8787/ui — seed the demo markets, flip the evidence scenarios, and watch the oracle refuse to over-claim. Pitch deck at `/ui/pitch.html`.

The full project — engine, market factory, OWL ontology, deontic policy packs, formal epistemology, 45 tests, docs — lives in [`boundarycast-personal-weather/`](boundarycast-personal-weather/).

## License

Free and open source under the [MIT License](boundarycast-personal-weather/LICENSE) — © 2026 Oak & Sparrow Systems Enterprise LLC. The private production math stays out of this repository by design (safe harbor), not by license.
