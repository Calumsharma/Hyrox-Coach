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
