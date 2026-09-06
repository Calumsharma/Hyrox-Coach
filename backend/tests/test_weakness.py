from datetime import date

from app.models import Athlete, PastHyroxResult
from app.services.weakness import STATION_SLUGS, rank_weaknesses


def test_falls_back_to_self_report_when_no_full_splits():
    athlete = Athlete(self_reported_weak_stations=["sled_push", "farmers_carry", "wall_balls"])
    athlete.past_results = []
    assert rank_weaknesses(athlete, top_n=2) == ["sled_push", "farmers_carry"]


def test_ranks_from_splits_when_full_race_data_available():
    # sled_push and farmers_carry take disproportionately long relative to the athlete's own average.
    splits = {slug: 60 for slug in STATION_SLUGS}
    splits["sled_push"] = 180
    splits["farmers_carry"] = 150

    athlete = Athlete(self_reported_weak_stations=["wall_balls"])
    athlete.past_results = [
        PastHyroxResult(
            event_date=date(2026, 1, 1),
            division="open_men",
            total_time_seconds=sum(splits.values()),
            station_splits_seconds=splits,
        )
    ]

    ranked = rank_weaknesses(athlete, top_n=2)
    assert ranked == ["sled_push", "farmers_carry"]


def test_uses_most_recent_result_when_multiple_exist():
    old_splits = {slug: 60 for slug in STATION_SLUGS}
    old_splits["wall_balls"] = 200

    new_splits = {slug: 60 for slug in STATION_SLUGS}
    new_splits["sled_pull"] = 200

    athlete = Athlete(self_reported_weak_stations=[])
    athlete.past_results = [
        PastHyroxResult(event_date=date(2025, 1, 1), division="open_men",
                         total_time_seconds=sum(old_splits.values()), station_splits_seconds=old_splits),
        PastHyroxResult(event_date=date(2026, 6, 1), division="open_men",
                         total_time_seconds=sum(new_splits.values()), station_splits_seconds=new_splits),
    ]

    assert rank_weaknesses(athlete, top_n=1) == ["sled_pull"]
