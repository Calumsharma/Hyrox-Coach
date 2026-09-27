"""The 2 activated BenchmarkDefinition rows — Program Engine v5 Milestone 2, plan §H.

Both are running time trials, raw_value in seconds, running-only distances so no HYROX
division-based load applies. BenchmarkDefinition/BenchmarkDefinitionMetric are immutable seed
definitions (see app/models/benchmark.py) — this seed function only ever inserts rows that
don't yet exist; it never updates one in place.
"""

from app.db import SessionLocal
from app.models import BenchmarkDefinition, BenchmarkDefinitionMetric

FIVE_K_BENCHMARK_ID = "benchmark_5k_time_trial"
TEN_K_BENCHMARK_ID = "benchmark_10k_time_trial"

BENCHMARK_DEFINITIONS = [
    {
        "id": FIVE_K_BENCHMARK_ID,
        "name": "5K Time Trial",
        "protocol_description": "A single maximal-effort, continuous time trial over a fixed, "
        "accurately-measured 5000m distance.",
        "unit": "sec",
        "evidence_class": "coach_derived",
    },
    {
        "id": TEN_K_BENCHMARK_ID,
        "name": "10K Time Trial",
        "protocol_description": "A single maximal-effort, continuous time trial over a fixed, "
        "accurately-measured 10000m distance.",
        "unit": "sec",
        "evidence_class": "coach_derived",
    },
]

BENCHMARK_DEFINITION_METRICS = [
    {"benchmark_id": FIVE_K_BENCHMARK_ID, "metric_id": "threshold_pace_riegel_sec_per_km"},
    {"benchmark_id": TEN_K_BENCHMARK_ID, "metric_id": "threshold_pace_riegel_sec_per_km"},
]


def run():
    db = SessionLocal()
    try:
        inserted_defs = 0
        for row in BENCHMARK_DEFINITIONS:
            if db.get(BenchmarkDefinition, row["id"]) is None:
                db.add(BenchmarkDefinition(**row))
                inserted_defs += 1
        db.commit()

        inserted_links = 0
        for row in BENCHMARK_DEFINITION_METRICS:
            existing = (
                db.query(BenchmarkDefinitionMetric)
                .filter(
                    BenchmarkDefinitionMetric.benchmark_id == row["benchmark_id"],
                    BenchmarkDefinitionMetric.metric_id == row["metric_id"],
                )
                .first()
            )
            if existing is None:
                db.add(BenchmarkDefinitionMetric(**row))
                inserted_links += 1
        db.commit()
        print(f"Seeded {inserted_defs} new benchmark definition(s), {inserted_links} new benchmark-metric link(s).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
