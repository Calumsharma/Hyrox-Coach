from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ExerciseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    category: str
    description: str
    cues: list[str]
    video_url: str | None
    video_source: str
