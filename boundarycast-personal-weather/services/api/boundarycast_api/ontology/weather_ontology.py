BOUNDARYCAST_WEATHER_ONTOLOGY_V02 = {
    "ontology_id": "boundarycast-weather-ontology-v0.2",
    "classes": [
        "UserLocation", "PersonLocationContext", "LocationPrecision", "ForecastWindow",
        "OfficialForecast", "WeatherObservation", "WeatherAlert", "EvidenceBundle",
        "SourceProvenance", "MicroclimateContext", "SurfaceExposure", "ShadeExposure",
        "ElevationProfile", "WindExposure", "UrbanHeatEffect", "WaterProximity",
        "ObservationDistance", "ForecastGridDistance", "MicroclimateAdjustment",
        "MicroclimateConfidence", "ForecastClaim", "UncertaintyInterval", "PolicyPack",
        "Rule", "GatekeeperVerdict", "DecisionArtifact", "ReplayResult",
        "ClaimScope", "ScopeDecision", "ScopeReasonCode", "PersonalForecastContext",
        "LocationMinimization", "LocationHash", "ZeroCachePolicy"
    ],
    "relationships": [
        "PersonLocationContext has MicroclimateContext",
        "EvidenceBundle includes OfficialForecast",
        "EvidenceBundle includes WeatherObservation",
        "EvidenceBundle includes WeatherAlert",
        "ForecastClaim is_supported_by EvidenceBundle",
        "GatekeeperVerdict governs ForecastClaim",
        "DecisionArtifact records GatekeeperVerdict",
        "ScopeDecision assigns ClaimScope",
        "ScopeDecision cites ScopeReasonCode",
        "ScopeDecision qualifies ForecastClaim",
        "PersonalForecastContext requests ClaimScope",
        "ZeroCachePolicy constrains PersonalForecastContext",
        "ZeroCachePolicy constrains DecisionArtifact",
        "LocationMinimization produces LocationHash",
        "DecisionArtifact records LocationMinimization",
        "DecisionArtifact records ScopeDecision"
    ]
}
