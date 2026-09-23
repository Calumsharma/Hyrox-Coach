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


# --- Program Engine v5 Milestone 1B: capability measurement foundation ---
# See the Milestone 1B plan (happy-weaving-raven.md) for the full rationale behind each.

class AssessmentType(str, enum.Enum):
    """Where a CapabilityAssessment's evidence originated. Does not by itself determine
    whether the assessment is a direct measurement or a derived feature — see
    CapabilityAssessment.derivation_method."""

    BENCHMARK_RESULT = "benchmark_result"
    LOGGED_SESSION_DERIVED = "logged_session_derived"
    SELF_REPORT = "self_report"
    WEARABLE_DERIVED = "wearable_derived"
    RACE_RESULT = "race_result"


class CapabilityClassification(str, enum.Enum):
    """CapabilityGap's weak/adequate/strong/unclassified verdict."""

    WEAK = "weak"
    ADEQUATE = "adequate"
    STRONG = "strong"
    UNCLASSIFIED = "unclassified"


class CapabilityConfidence(str, enum.Enum):
    """CapabilityGap's confidence in its classification. NONE means no CapabilityBandPolicy
    exists yet for this metric — never a guessed value."""

    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class BandLabel(str, enum.Enum):
    """CapabilityBand's own label — never 'unclassified', since a band always represents a
    real classification; the unclassified state is the absence of an applicable band."""

    WEAK = "weak"
    ADEQUATE = "adequate"
    STRONG = "strong"


class SourceQualityTier(str, enum.Enum):
    """The evidence-quality hierarchy a CapabilityConfidenceRule is scoped to — direct
    task-specific evidence outranks training logs, which outrank indirect proxies, which
    outrank self-report. Pain/illness safety reporting is a separate mechanism entirely
    (AthleteStatusReport) and does not appear in this hierarchy."""

    DIRECT_BENCHMARK = "direct_benchmark"
    RACE_RESULT = "race_result"
    TRAINING_LOG = "training_log"
    INDIRECT_PROXY = "indirect_proxy"
    SELF_REPORT = "self_report"


class ConfidenceTier(str, enum.Enum):
    """What a satisfied CapabilityConfidenceRule produces. No NONE value — a rule only ever
    grants a positive confidence tier; the absence of any satisfied rule is what produces
    CapabilityConfidence.NONE on the resulting CapabilityGap."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class StatusReportSource(str, enum.Enum):
    """Who/what supplied an AthleteStatusReport. Deliberately closed to athlete-provided input
    only in Milestone 1B — never inferred, never a route/service default."""

    ATHLETE_SELF_REPORT = "athlete_self_report"


class SymptomSeverity(str, enum.Enum):
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class EffectOnTraining(str, enum.Enum):
    NONE = "none"
    REDUCED = "reduced"
    AVOID = "avoid"
