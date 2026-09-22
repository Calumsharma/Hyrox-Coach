from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, JSON
from sqlalchemy.orm import Mapped, mapped_column


from app.db import Base


class AthleteEquipmentProfile(Base):
    """What equipment an athlete actually has access to. Athlete-editable.

    Values are expected to be drawn from a controlled equipment vocabulary once one exists
    (`EquipmentVocabulary`, a later milestone) — free text for now, since nothing yet validates
    against it and Milestone 1A does not create that table.
    """

    __tablename__ = "athlete_equipment_profiles"

    athlete_id: Mapped[str] = mapped_column(String, ForeignKey("athletes.id"), primary_key=True)
    available_equipment: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
