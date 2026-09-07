from typing import Optional

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ExerciseReference(Base):
    """A movement library entry, keyed by the same slug used in Workout.prescription blocks
    (see app/services/movement_library.py) so the app can link a prescribed movement straight
    to its how-to entry.

    `video_url` is intentionally nullable — we have no real video content yet (self-filmed or
    licensed/white-labeled) and won't fabricate links to content that doesn't exist. Until a
    video pipeline exists, entries carry a written description only and the client shows a
    "video coming soon" state.
    """

    __tablename__ = "exercise_references"

    slug: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)  # strength | station | mobility
    description: Mapped[str] = mapped_column(String)
    cues: Mapped[list] = mapped_column(JSON, default=list)  # short coaching cues, e.g. "brace before descending"
    video_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    video_source: Mapped[str] = mapped_column(String, default="none")  # none | self_filmed | licensed | external_link
