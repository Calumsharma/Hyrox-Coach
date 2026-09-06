from sqlalchemy import Float, String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import StationSlug


class StationReference(Base):
    """Seed data: the 8 fixed HYROX stations, in race order, with official loads per division.

    Not user-editable — the race format itself never changes, only the athlete's program around it.
    """

    __tablename__ = "station_reference"

    slug: Mapped[StationSlug] = mapped_column(String, primary_key=True)
    order: Mapped[int] = mapped_column()
    name: Mapped[str] = mapped_column(String)
    distance_or_reps: Mapped[str] = mapped_column(String)

    # {"open_men": {"load_kg": 152}, "pro_men": {"load_kg": 202}, ...}
    # farmers_carry/sandbag/wall_balls use load_kg as per-hand or per-item load; sled uses total sled+weight.
    division_loads: Mapped[dict] = mapped_column(JSON, default=dict)

    primary_demand: Mapped[str] = mapped_column(String)  # e.g. "grip/carry", "posterior chain", "leg strength"


class AccessoryMovement(Base):
    """Library of training movements used to build programs, tagged by which station weakness they address."""

    __tablename__ = "accessory_movements"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)  # strength | run | aerobic | mobility
    addresses_stations: Mapped[list] = mapped_column(JSON, default=list)  # list[StationSlug]
    notes: Mapped[str] = mapped_column(String, default="")
