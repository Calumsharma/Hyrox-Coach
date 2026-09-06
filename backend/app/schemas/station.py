from pydantic import BaseModel, ConfigDict

from app.models.enums import StationSlug


class StationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: StationSlug
    order: int
    name: str
    distance_or_reps: str
    primary_demand: str
    division_loads: dict
