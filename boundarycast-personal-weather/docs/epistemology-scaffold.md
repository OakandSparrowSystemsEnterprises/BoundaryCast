# Epistemology Scaffold

BoundaryCast asks whether it knows enough to speak.

Core checks:

- SchemaValid
- LocationKnown
- LocationPreciseEnough
- OfficialForecastAvailable
- ObservationAvailable
- EvidenceFresh
- SourceKnown
- ObservationDistanceAcceptable
- ForecastGridDistanceKnown
- OfficialAlertChecked
- MicroclimateContextKnown
- MicroclimateConfidenceBounded
- UncertaintyBounded
- ClaimInsideForecastWindow
- PolicyPackActive
- VerdictReplayable

Claim scope checks (v3):

- determine_claim_scope
- highest_supported_scope
- fallback_scope
- exact_location_supported
- microclimate_adjustment_supported
- nearby_observation_supported
- official_forecast_supported
- official_alert_governs
- unsupported_specific_claim

A claim may be true-looking but still not publishable if evidence is missing, stale, distant, over-specific, or not replayable. And a claim that is publishable may still not be publishable *at the requested specificity* — that is what the claim scope checks decide.
