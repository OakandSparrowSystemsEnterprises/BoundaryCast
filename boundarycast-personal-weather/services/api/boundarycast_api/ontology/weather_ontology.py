BOUNDARYCAST_WEATHER_ONTOLOGY_V01 = {
    "ontology_id": "boundarycast-weather-ontology-v0.1",
    "classes": [
        "UserLocation", "PersonLocationContext", "LocationPrecision", "ForecastWindow",
        "OfficialForecast", "WeatherObservation", "WeatherAlert", "EvidenceBundle",
        "SourceProvenance", "MicroclimateContext", "SurfaceExposure", "ShadeExposure",
        "ElevationProfile", "WindExposure", "UrbanHeatEffect", "WaterProximity",
        "ObservationDistance", "ForecastGridDistance", "MicroclimateAdjustment",
        "MicroclimateConfidence", "ForecastClaim", "UncertaintyInterval", "PolicyPack",
        "Rule", "GatekeeperVerdict", "DecisionArtifact", "ReplayResult"
    ],
    "relationships": [
        "PersonLocationContext has MicroclimateContext",
        "EvidenceBundle includes OfficialForecast",
        "EvidenceBundle includes WeatherObservation",
        "EvidenceBundle includes WeatherAlert",
        "ForecastClaim is_supported_by EvidenceBundle",
        "GatekeeperVerdict governs ForecastClaim",
        "DecisionArtifact records GatekeeperVerdict"
    ]
}
