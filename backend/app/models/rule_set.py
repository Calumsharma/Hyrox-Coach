from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RaceRuleSet(Base):
    """Version/source metadata for the official HYROX race rules a program is built against.

    Deliberately holds only versioning metadata — not the station definitions themselves.
    `StationReference` remains the sole source of truth for station order/loads/demands; this
    table is what `StationReference.rule_set_version` points at, not a parallel copy of the
    same data in JSON (see Program Engine v5 plan, Milestone 1A ruleset data migration).
    """

    __tablename__ = "race_rule_sets"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # e.g. "hyrox_singles_2026_27"
    effective_from: Mapped[date] = mapped_column(Date)
    source_url: Mapped[str] = mapped_column(String)
    notes: Mapped[str] = mapped_column(String, default="")
