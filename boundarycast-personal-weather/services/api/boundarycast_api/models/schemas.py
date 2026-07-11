from pydantic import BaseModel, Field
from typing import Optional, Literal

RequestedScope = Literal[
    "exact_location",
    "microclimate_adjusted",
    "nearby_observation_area",
    "official_forecast_area",
]

class PersonalForecastRequest(BaseModel):
    tenant_id: str = Field(default="boundarycast_demo_user", min_length=1, max_length=100)
    latitude: float = Field(default=37.7974, ge=-90, le=90)
    longitude: float = Field(default=-121.2161, ge=-180, le=180)
    precision_meters: int = Field(default=25, ge=1, le=100000)
    forecast_hours: int = Field(default=12, ge=1, le=72)
    requested_scope: RequestedScope = "exact_location"
    surface_exposure: Optional[str] = Field(default=None, max_length=100)
    shade_exposure: Optional[str] = Field(default=None, max_length=100)
    elevation_meters: Optional[float] = Field(default=None, ge=-500, le=10000)
    wind_exposure: Optional[str] = Field(default=None, max_length=100)
    nearby_water: Optional[bool] = None
    urban_density: Optional[Literal["low", "medium", "high"]] = None
    demo_mode: bool = True
    # Demo-only evidence scenario switches, so every claim scope tier is
    # reachable from the UI and the regression suite without a real outage.
    simulate_alert: bool = False
    simulate_no_official_forecast: bool = False
    simulate_no_observation: bool = False


class MarketResolutionRequest(PersonalForecastRequest):
    """A prediction-market resolution request: a market question bound to a
    location, a measurable condition, and the minimum claim scope the market
    creator accepts as a resolution basis."""
    market_id: str = Field(default="market_demo_001", min_length=1, max_length=100)
    question: str = Field(default="Will the condition hold at this location within the forecast window?",
                          min_length=1, max_length=500)
    metric: Literal["temperature_f", "wind_mph", "precip_probability", "alert_active"] = "temperature_f"
    operator: Literal["gt", "gte", "lt", "lte"] = "gt"
    threshold: float = Field(default=0, ge=-1e9, le=1e9)
    minimum_scope: RequestedScope = "official_forecast_area"


class MarketCreateRequest(MarketResolutionRequest):
    """Create a market on the demo book. market_id is assigned by the book."""


class StakeRequest(BaseModel):
    side: Literal["YES", "NO"]
    amount: float = Field(gt=0, le=1_000_000)
    trader: str = Field(default="anon", min_length=1, max_length=100)


class MarketSettleRequest(BaseModel):
    """Settle-time overrides for the demo evidence scenario, so a market
    created earlier can be resolved under live conditions (or a simulated
    alert) on stage."""
    simulate_alert: Optional[bool] = None
    simulate_no_official_forecast: Optional[bool] = None
    simulate_no_observation: Optional[bool] = None
