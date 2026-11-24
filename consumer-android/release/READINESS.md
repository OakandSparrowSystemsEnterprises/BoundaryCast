# BoundaryCast RC1 release boundary

Original public repo: 584bea49d49e1b89a4c102655dc51a313da1f768. Consumer path only; no changes to existing service/markets/private provider seam. Ported public scopes and verdict names, stricter no-synthetic and alert-availability handling. No real-money or play-money markets in app. No private math, exact-location forecast guarantee, proctoring/security certification, or Gatekeeper V2 production authority claimed.

NWS official documentation: https://www.weather.gov/documentation/services-web-api
NWS data usage and attribution: https://www.weather.gov/disclaimer
Android permissions: foreground fine/coarse only; INTERNET; no background permission. Android app uses coordinates rounded to four decimals in direct requests to NWS, which receives location/IP. No logs, stored history or OASSE data server in code. Current view cleared when backgrounded; external provider may retain standard logs. Verify actual behavior on devices and applicable Play data safety declarations, including whether transient location transfers are declarable; no assumption of a no-data-collected declaration.

Acceptance: run policy fixtures; check actual NWS point/alerts/forecast/station data against official data; test GPS permission denial and approximate permission; check outside coverage, no network, malformed responses, stale observation, missing alerts, severe/Extreme controlled fixtures; check that no fake metrics or false all-clear appear; check native build, device and release manifest. Review accessibility and privacy; prepare final support/terms/privacy URLs, store graphics, Play listing, upload key and signed bundle, internal testing and publisher approval. LicensePrep's existing organization Play account can be used once Google verifies it. Proposed commercial model: one-time paid download, no ads, subscriptions or in-app purchases. Price not set; no paid service commitment. Do not publish paid before acceptance.

## Source verification
PASS: 93 deterministic mobile policy and fixture checks. Not a native build or live provider acceptance.
App JavaScript parses. No actual Android build or live request was run in this session.
