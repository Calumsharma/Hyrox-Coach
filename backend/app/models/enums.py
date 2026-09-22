import enum


class Division(str, enum.Enum):
    OPEN_MEN = "open_men"
    OPEN_WOMEN = "open_women"
    PRO_MEN = "pro_men"
    PRO_WOMEN = "pro_women"
    DOUBLES_MEN = "doubles_men"
    DOUBLES_WOMEN = "doubles_women"
    DOUBLES_MIXED = "doubles_mixed"


SOLO_DIVISIONS = {Division.OPEN_MEN, Division.OPEN_WOMEN, Division.PRO_MEN, Division.PRO_WOMEN}


class ExperienceTier(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Discipline(str, enum.Enum):
    """The competition a training block is built for. Only HYROX has a real program builder
    right now — the others exist as a stated roadmap, not fabricated content. See
    `app/services/program_engine.py`'s `BUILDERS` registry."""

    HYROX = "hyrox"
    FIVE_K = "5k"
    TEN_K = "10k"
    HALF_MARATHON = "half_marathon"
    MARATHON = "marathon"
    HALF_IRONMAN = "half_ironman"
    CROSSFIT_COMPETITION = "crossfit_competition"


class StationSlug(str, enum.Enum):
    SKIERG = "skierg"
    SLED_PUSH = "sled_push"
    SLED_PULL = "sled_pull"
    BURPEE_BROAD_JUMP = "burpee_broad_jump"
    ROW = "row"
    FARMERS_CARRY = "farmers_carry"
    SANDBAG_LUNGES = "sandbag_lunges"
    WALL_BALLS = "wall_balls"


class WorkoutType(str, enum.Enum):
    RUN = "run"
    STATION_SKILL = "station_skill"
    STRENGTH = "strength"
    AEROBIC = "aerobic"
    MOBILITY = "mobility"
    REST = "rest"
    RACE_DAY = "race_day"


class WearableProvider(str, enum.Enum):
    WHOOP = "whoop"
    GARMIN = "garmin"
    OURA = "oura"
    APPLE_HEALTH = "apple_health"


class RecoveryTrend(str, enum.Enum):
    RISING = "rising"
    STABLE = "stable"
    FALLING = "falling"


class HeartRateZone(str, enum.Enum):
    """Standard 5-zone %HRmax model. Z3 is the "grey zone" — HYROX programming should mostly
    avoid living there (see app/services/heart_rate.py and the physiology research notes)."""

    Z1_RECOVERY = "z1_recovery"
    Z2_AEROBIC_BASE = "z2_aerobic_base"
    Z3_TEMPO = "z3_tempo"
    Z4_THRESHOLD = "z4_threshold"
    Z5_ANAEROBIC = "z5_anaerobic"


class EvidenceClass(str, enum.Enum):
    """How a piece of programming logic or data is grounded — see the Program Engine v5 plan's
    domain model. Attached to anything the capability-based architecture introduces so a coach
    (or an athlete) can see whether a decision traces to an official rule, published research,
    a coach's own judgment call, or an explicitly experimental mechanism."""

    OFFICIAL_RULE = "official_rule"
    RESEARCH_SUPPORTED = "research_supported"
    COACH_DERIVED = "coach_derived"
    EXPERIMENTAL = "experimental"


class ProgrammeDecisionType(str, enum.Enum):
    """The kind of automated or manual change a ProgrammeDecision audit row records."""

    BASELINE_GENERATION = "baseline_generation"
    PROGRESSION_ADJUSTMENT = "progression_adjustment"
    RECOVERY_ADAPTATION = "recovery_adaptation"
    SAFETY_OVERRIDE = "safety_override"
    MISSED_SESSION_RESCHEDULED = "missed_session_rescheduled"
    MISSED_SESSION_SUBSTITUTED = "missed_session_substituted"
    MISSED_SESSION_DROPPED_REBALANCED = "missed_session_dropped_rebalanced"
    MANUAL_COACH_EDIT = "manual_coach_edit"
