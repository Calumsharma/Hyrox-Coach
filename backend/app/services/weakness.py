"""Rank an athlete's weakest HYROX stations.

If a recent race has full station splits, weakness is derived from the athlete's
own pacing (which stations took disproportionately long relative to their own
average) rather than an external population benchmark — we don't have reliable,
sourced normative split data to compare against, and a wrong "average" would be
worse than no external comparison at all. Self-report is the fallback (and, for
now, the primary path) when no split data exists.
"""

import statistics

from app.models import Athlete
from app.models.enums import StationSlug

STATION_SLUGS = [s.value for s in StationSlug]


def rank_weaknesses(athlete: Athlete, top_n: int = 3) -> list[str]:
    most_recent = _most_recent_result_with_full_splits(athlete)
    if most_recent is not None:
        return _rank_from_splits(most_recent.station_splits_seconds, top_n)

    return list(athlete.self_reported_weak_stations)[:top_n]


def _most_recent_result_with_full_splits(athlete: Athlete):
    candidates = [
        r for r in athlete.past_results
        if all(slug in r.station_splits_seconds for slug in STATION_SLUGS)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r.event_date)


def _rank_from_splits(splits: dict, top_n: int) -> list[str]:
    times = [splits[slug] for slug in STATION_SLUGS]
    mean = statistics.mean(times)
    stdev = statistics.pstdev(times) or 1.0

    z_scores = {slug: (splits[slug] - mean) / stdev for slug in STATION_SLUGS}
    ranked = sorted(z_scores, key=z_scores.get, reverse=True)
    return ranked[:top_n]
