from pydantic import BaseModel, Field
from typing import Optional, Literal

class PersonalForecastRequest(BaseModel):
    tenant_id: str = "boundarycast_demo_user"
    latitude: float = Field(default=37.7974, ge=-90, le=90)
    longitude: float = Field(default=-121.2161, ge=-180, le=180)
    precision_meters: int = Field(default=25, ge=1, le=100000)
    forecast_hours: int = Field(default=12, ge=1, le=72)
    surface_exposure: Optional[str] = None
    shade_exposure: Optional[str] = None
    elevation_meters: Optional[float] = None
    wind_exposure: Optional[str] = None
    nearby_water: Optional[bool] = None
    urban_density: Optional[Literal["low", "medium", "high"]] = None
    demo_mode: bool = True
