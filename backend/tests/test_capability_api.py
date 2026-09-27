"""First FastAPI TestClient route-level test in this codebase — Program Engine v5 Milestone 2,
plan §J/point 12. Proves the full Swagger self-test walkthrough through the real API surface:
submit -> recompute -> status -> repeat -> zero duplicate rows across all four tables. Also
proves, per independent review: every route requires authentication; metric_id validation is
consistent across assessments/scores/gaps/recompute/status; gaps expose complete lineage; a
forced mid-recompute failure leaves no partial chain; and "current" objects in status/recompute
responses correctly carry `is_current`/`is_currently_selected=True`, never a stale default.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import auth as auth_router_module
from app.api import capabilities as capabilities_router_module
from app.db import get_db
from app.models import (
    Athlete,
    BenchmarkDefinition,
    BenchmarkDefinitionMetric,
    CapabilityAssessment,
    CapabilityDefinition,
    CapabilityGap,
    CapabilityMetric,
    CapabilityScore,
    CapabilityScoreAssessment,
)
from app.schemas.capability import BenchmarkResultCreate
from app.seed_data.benchmarks import TEN_K_BENCHMARK_ID

THRESHOLD_PACE_METRIC_ID = "threshold_pace_riegel_sec_per_km"

_VALID_CONTEXT = {
    "test_type": "time_trial",
    "surface": "track",
    "elapsed_time_basis": "watch_time",
    "distance_verification": "certified_course",
}


@pytest.fixture
def client(db_session):
    app = FastAPI()
    app.include_router(auth_router_module.router)
    app.include_router(capabilities_router_module.router)
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


def _seed_threshold_pace(db_session):
    # Committed in dependency order, matching the real seed_data/seed.py sequence — a single
    # batched commit across independently-added rows connected only by bare FKs (no ORM
    # `relationship()`) is not reliably ordered by SQLAlchemy's flush, so each layer commits
    # before the next references it.
    db_session.add(CapabilityDefinition(id="threshold_race_pace", name="Threshold & Race Pace", description="", measurement_hint=""))
    db_session.commit()
    db_session.add(CapabilityMetric(
        id=THRESHOLD_PACE_METRIC_ID, capability_id="threshold_race_pace", station=None,
        unit="sec_per_km", higher_is_better=False, evidence_class="coach_derived", description="",
    ))
    db_session.add(BenchmarkDefinition(id=TEN_K_BENCHMARK_ID, name="10K Time Trial", protocol_description="", unit="sec", evidence_class="coach_derived"))
    db_session.commit()
    db_session.add(BenchmarkDefinitionMetric(benchmark_id=TEN_K_BENCHMARK_ID, metric_id=THRESHOLD_PACE_METRIC_ID))
    db_session.commit()


def _authorized_headers(client, email="api-test@example.com"):
    resp = client.post("/auth/dev-login", json={"email": email})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _all_table_counts(db_session):
    return (
        db_session.query(CapabilityAssessment).count(),
        db_session.query(CapabilityScore).count(),
        db_session.query(CapabilityScoreAssessment).count(),
        db_session.query(CapabilityGap).count(),
    )


def test_full_submit_recompute_status_walkthrough_is_idempotent(client, db_session):
    _seed_threshold_pace(db_session)
    headers = _authorized_headers(client)

    defs_resp = client.get("/capabilities/benchmark-definitions", headers=headers)
    assert defs_resp.status_code == 200
    ten_k_def = next(d for d in defs_resp.json() if d["id"] == TEN_K_BENCHMARK_ID)
    assert THRESHOLD_PACE_METRIC_ID in ten_k_def["metric_ids"]

    submit_resp = client.post(
        "/capabilities/benchmark-results",
        headers=headers,
        json={
            "benchmark_id": TEN_K_BENCHMARK_ID,
            "completed_at": "2026-09-01T08:00:00",
            "raw_value": 2400.0,
            "context": _VALID_CONTEXT,
        },
    )
    assert submit_resp.status_code == 201

    recompute_resp = client.post(
        "/capabilities/recompute", headers=headers, json={"metric_id": THRESHOLD_PACE_METRIC_ID}
    )
    assert recompute_resp.status_code == 200
    recompute_body = recompute_resp.json()
    assert recompute_body["status"] == "ok"
    # The gap returned by recompute IS the current one by construction — must not be left at the
    # Pydantic default `is_current=False`.
    assert recompute_body["gap"]["is_current"] is True
    assert len(recompute_body["gap"]["assessment_ids"]) == 1
    assert len(recompute_body["gap"]["source_references"]) == 1

    status_resp = client.get(
        "/capabilities/status", headers=headers, params={"metric_id": THRESHOLD_PACE_METRIC_ID}
    )
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["state"] == "current"
    assert body["current_gap"]["classification"] == "unclassified"
    assert body["current_gap"]["confidence"] == "none"
    assert body["current_gap"]["is_current"] is True
    assert body["current_score"]["is_current"] is True
    assert body["current_assessment"]["is_currently_selected"] is True
    assert body["provenance"]["gap_id"] is not None
    assert body["provenance"]["score_id"] is not None
    assert len(body["provenance"]["assessment_ids"]) == 1

    # Gaps route exposes the same complete lineage (point 1: gap -> score -> assessment -> source).
    gaps_resp = client.get("/capabilities/gaps", headers=headers, params={"metric_id": THRESHOLD_PACE_METRIC_ID})
    assert gaps_resp.status_code == 200
    gap_row = gaps_resp.json()[0]
    assert gap_row["is_current"] is True
    assert gap_row["based_on_score_id"] == body["current_score"]["id"]
    assert len(gap_row["assessment_ids"]) == 1
    assert gap_row["source_references"][0]["source_id"] is not None  # the BenchmarkResult id

    before = _all_table_counts(db_session)

    # Repeat recompute with no new evidence — zero duplicate rows across all four tables.
    recompute_resp_2 = client.post(
        "/capabilities/recompute", headers=headers, json={"metric_id": THRESHOLD_PACE_METRIC_ID}
    )
    assert recompute_resp_2.status_code == 200

    assert _all_table_counts(db_session) == before

    status_resp_2 = client.get(
        "/capabilities/status", headers=headers, params={"metric_id": THRESHOLD_PACE_METRIC_ID}
    )
    assert status_resp_2.json() == body


def test_benchmark_result_rejects_malformed_context(client, db_session):
    _seed_threshold_pace(db_session)
    headers = _authorized_headers(client)

    resp = client.post(
        "/capabilities/benchmark-results",
        headers=headers,
        json={
            "benchmark_id": TEN_K_BENCHMARK_ID,
            "completed_at": "2026-09-01T08:00:00",
            "raw_value": 2400.0,
            "context": {"test_type": "time_trial", "surface": "track"},  # missing 2 required fields
        },
    )
    assert resp.status_code == 422


def test_benchmark_result_rejects_out_of_vocabulary_context_value(client, db_session):
    _seed_threshold_pace(db_session)
    headers = _authorized_headers(client)

    resp = client.post(
        "/capabilities/benchmark-results",
        headers=headers,
        json={
            "benchmark_id": TEN_K_BENCHMARK_ID,
            "completed_at": "2026-09-01T08:00:00",
            "raw_value": 2400.0,
            "context": {**_VALID_CONTEXT, "surface": "lava"},
        },
    )
    assert resp.status_code == 422


def test_benchmark_result_rejects_non_positive_raw_value(client, db_session):
    _seed_threshold_pace(db_session)
    headers = _authorized_headers(client)

    resp = client.post(
        "/capabilities/benchmark-results",
        headers=headers,
        json={
            "benchmark_id": TEN_K_BENCHMARK_ID,
            "completed_at": "2026-09-01T08:00:00",
            "raw_value": -5.0,
            "context": _VALID_CONTEXT,
        },
    )
    assert resp.status_code == 400


def test_benchmark_result_rejects_unsupported_benchmark_id(client, db_session):
    _seed_threshold_pace(db_session)
    headers = _authorized_headers(client)

    resp = client.post(
        "/capabilities/benchmark-results",
        headers=headers,
        json={
            "benchmark_id": "not_a_real_benchmark",
            "completed_at": "2026-09-01T08:00:00",
            "raw_value": 2400.0,
            "context": _VALID_CONTEXT,
        },
    )
    assert resp.status_code == 400


def test_recompute_rejects_unsupported_metric_id(client, db_session):
    headers = _authorized_headers(client)
    resp = client.post("/capabilities/recompute", headers=headers, json={"metric_id": "not_a_real_metric"})
    assert resp.status_code == 400


def test_status_rejects_unsupported_metric_id(client, db_session):
    headers = _authorized_headers(client)
    resp = client.get("/capabilities/status", headers=headers, params={"metric_id": "not_a_real_metric"})
    assert resp.status_code == 400


# --- Point 1: metric_id validation applied consistently to assessments/scores/gaps too ---

def test_assessments_rejects_unsupported_metric_id(client, db_session):
    headers = _authorized_headers(client)
    resp = client.get("/capabilities/assessments", headers=headers, params={"metric_id": "not_a_real_metric"})
    assert resp.status_code == 400


def test_scores_rejects_unsupported_metric_id(client, db_session):
    headers = _authorized_headers(client)
    resp = client.get("/capabilities/scores", headers=headers, params={"metric_id": "not_a_real_metric"})
    assert resp.status_code == 400


def test_gaps_rejects_unsupported_metric_id(client, db_session):
    headers = _authorized_headers(client)
    resp = client.get("/capabilities/gaps", headers=headers, params={"metric_id": "not_a_real_metric"})
    assert resp.status_code == 400


def test_benchmark_result_schema_does_not_expose_athlete_id_field():
    """Structural test for point 7: athlete_id is not part of the request schema at all, so
    there is nothing in the payload a client could use to submit on another athlete's behalf."""
    assert "athlete_id" not in BenchmarkResultCreate.model_fields


# --- Point 1: every one of the seven routes requires authentication ---

@pytest.mark.parametrize(
    "method,path,kwargs",
    [
        ("get", "/capabilities/benchmark-definitions", {}),
        ("post", "/capabilities/benchmark-results", {"json": {
            "benchmark_id": TEN_K_BENCHMARK_ID, "completed_at": "2026-09-01T08:00:00",
            "raw_value": 2400.0, "context": _VALID_CONTEXT,
        }}),
        ("post", "/capabilities/recompute", {"json": {"metric_id": THRESHOLD_PACE_METRIC_ID}}),
        ("get", "/capabilities/assessments", {"params": {"metric_id": THRESHOLD_PACE_METRIC_ID}}),
        ("get", "/capabilities/scores", {"params": {"metric_id": THRESHOLD_PACE_METRIC_ID}}),
        ("get", "/capabilities/gaps", {"params": {"metric_id": THRESHOLD_PACE_METRIC_ID}}),
        ("get", "/capabilities/status", {"params": {"metric_id": THRESHOLD_PACE_METRIC_ID}}),
    ],
)
def test_every_capability_route_rejects_unauthenticated_request(client, db_session, method, path, kwargs):
    _seed_threshold_pace(db_session)
    resp = getattr(client, method)(path, **kwargs)  # no Authorization header at all
    assert resp.status_code in (401, 403)


# --- Point 2: a forced failure mid-recompute leaves no partial chain, proven at the route level ---

def test_forced_failure_mid_recompute_leaves_no_partial_chain_via_route(client, db_session, monkeypatch):
    _seed_threshold_pace(db_session)
    headers = _authorized_headers(client)
    submit_resp = client.post(
        "/capabilities/benchmark-results",
        headers=headers,
        json={
            "benchmark_id": TEN_K_BENCHMARK_ID,
            "completed_at": "2026-09-01T08:00:00",
            "raw_value": 2400.0,
            "context": _VALID_CONTEXT,
        },
    )
    assert submit_resp.status_code == 201

    import app.api.capabilities as capabilities_module

    def _boom(*args, **kwargs):
        raise RuntimeError("forced failure")

    monkeypatch.setattr(capabilities_module, "compute_gap", _boom)

    with pytest.raises(RuntimeError):
        client.post("/capabilities/recompute", headers=headers, json={"metric_id": THRESHOLD_PACE_METRIC_ID})

    # The whole recomputation reverted, including the assessment/score this same failed call
    # ingested — never a partial chain left behind.
    assert _all_table_counts(db_session) == (0, 0, 0, 0)
