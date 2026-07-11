from pydantic import BaseModel, Field
from typing import Optional, Literal

RequestedScope = Literal[
    "exact_location",
    "microclimate_adjusted",
    "nearby_observation_area",
    "official_forecast_area",
]

class PersonalForecastRequest(BaseModel):
    tenant_id: str = "boundarycast_demo_user"
    latitude: float = Field(default=37.7974, ge=-90, le=90)
    longitude: float = Field(default=-121.2161, ge=-180, le=180)
    precision_meters: int = Field(default=25, ge=1, le=100000)
    forecast_hours: int = Field(default=12, ge=1, le=72)
    requested_scope: RequestedScope = "exact_location"
    surface_exposure: Optional[str] = None
    shade_exposure: Optional[str] = None
    elevation_meters: Optional[float] = None
    wind_exposure: Optional[str] = None
    nearby_water: Optional[bool] = None
    urban_density: Optional[Literal["low", "medium", "high"]] = None
    demo_mode: bool = True
    # Demo-only evidence scenario switches, so every claim scope tier is
    # reachable from the UI and the regression suite without a real outage.
    simulate_alert: bool = False
    simulate_no_official_forecast: bool = False
    simulate_no_observation: bool = False
