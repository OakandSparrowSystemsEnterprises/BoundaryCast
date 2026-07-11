"""Public uncertainty band: a transparent, heuristic temperature interval.

This is PUBLIC PROXY math, deliberately simple and fully disclosed: the
spread widens with observation distance, evidence staleness, and weak
microclimate context. It is not the private Manifold/OASSE mathematics
and does not derive from it. Production may replace it via the private
provider seam.
"""
BASE_SPREAD_F = 2.0
DISTANCE_PENALTY_PER_KM = 0.15
STALENESS_PENALTY_PER_MIN = 0.02
WEAK_MICROCLIMATE_PENALTY = 1.5
ADEQUATE_CONFIDENCE = ("medium", "high")


def uncertainty_band(evidence, epistemology):
    official = evidence["official_forecast"]
    obs = evidence["observation"]
    temperature = official.get("temperature_f")
    if temperature is None:
        return None
    spread = BASE_SPREAD_F
    if obs.get("distance_km") is not None:
        spread += DISTANCE_PENALTY_PER_KM * obs["distance_km"]
    if official.get("freshness_minutes") is not None:
        spread += STALENESS_PENALTY_PER_MIN * official["freshness_minutes"]
    if epistemology.get("microclimate_confidence") not in ADEQUATE_CONFIDENCE:
        spread += WEAK_MICROCLIMATE_PENALTY
    if not epistemology.get("uncertainty_bounded"):
        spread += WEAK_MICROCLIMATE_PENALTY
    return {
        "temperature_low_f": round(temperature - spread, 1),
        "temperature_high_f": round(temperature + spread, 1),
        "spread_f": round(spread, 1),
        "method": "public-heuristic-band-v1 (distance + staleness + microclimate penalties; not private math)",
    }
