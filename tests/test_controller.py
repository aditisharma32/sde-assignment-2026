"""Unit and integration tests for Outcome-First Controller components."""
import pytest
from controller.cohorts import CohortEngine, CohortDefinition
from controller.config import ControllerConfig
from controller.detector import AnomalyDetector
from controller.governance import (
    compute_changed_dims,
    compute_max_shift,
    clamp_shift_toward,
)
from controller.ingestion import WorkflowMetrics
from controller.optimizer import (
    WorkflowOptimizer,
    two_proportion_z_test,
    normal_cdf,
)
from controller.store import AuditStore


def test_cohort_matching_and_precedence():
    engine = CohortEngine([
        {"id": "senior", "where": {"age_band": ["60+"]}},
        {"id": "young", "where": {"age_band": ["18-30"]}},
        {"id": "lang_ta", "where": {"lang": ["ta"]}},
    ])

    # Senior gets matched to senior
    lead1 = {"age_band": "60+", "lang": "ta"}
    assert engine.assign(lead1) == "senior"

    # Non-senior Tamil gets matched to lang_ta
    lead2 = {"age_band": "31-45", "lang": "ta"}
    assert engine.assign(lead2) == "lang_ta"

    # Default fallback
    lead3 = {"age_band": "31-45", "lang": "en"}
    assert engine.assign(lead3) == "default"


def test_two_proportion_z_test():
    # Equal proportions -> z near 0, p near 0.5
    z, p = two_proportion_z_test(50, 100, 50, 100)
    assert abs(z) < 0.01
    assert abs(p - 0.5) < 0.05

    # Variant B much better -> positive z, small p
    z, p = two_proportion_z_test(20, 200, 80, 200)
    assert z > 5.0
    assert p < 0.001


def test_did_allocation_and_degradation():
    cfg = ControllerConfig()
    opt = WorkflowOptimizer(cfg)
    det = AnomalyDetector(cfg)
    metrics = WorkflowMetrics("test_wf")

    # D1 and D2 have normal pickup (~30%)
    for _ in range(100):
        metrics.did_rolling["D1"].append(True if _ < 30 else False)
        metrics.did_rolling["D2"].append(True if _ < 30 else False)
    # D3 has degraded pickup (~5%)
    for _ in range(100):
        metrics.did_rolling["D3"].append(True if _ < 5 else False)

    healthy, degraded = det.detect_degraded_dids(metrics, ["D1", "D2", "D3"])
    assert "D3" in degraded
    assert "D1" in healthy
    assert "D2" in healthy

    alloc = opt.compute_did_allocation(healthy, degraded, cur_alloc={"D1": 0.5, "D2": 0.5})
    assert "D3" not in alloc or alloc["D3"] == 0.0
    assert abs(alloc["D1"] - 0.5) < 0.05
    assert abs(alloc["D2"] - 0.5) < 0.05


def test_hallucination_detection():
    cfg = ControllerConfig(halluc_min_connected=50, halluc_alert_rate=0.03)
    det = AnomalyDetector(cfg)
    metrics = WorkflowMetrics("test_wf")

    # Clean prompt: 1 flag in 60 calls (< 2%)
    for i in range(60):
        metrics.recent_qa_calls.append(("P1", i == 0))
    incident = det.detect_hallucination_incident(metrics, "P1")
    assert incident is None

    # Bad prompt: 6 flags in 60 calls (10% > 3%)
    for i in range(60):
        metrics.recent_qa_calls.append(("P2", i < 6))
    incident = det.detect_hallucination_incident(metrics, "P2")
    assert incident is not None
    assert incident["flag_rate"] == 0.10


def test_decay_detection():
    cfg = ControllerConfig(decay_eval_window_days=2, decay_drop_threshold=0.08)
    det = AnomalyDetector(cfg)
    metrics = WorkflowMetrics("test_wf")

    # Days 0-2: high engagement (60/100 = 60%)
    for d in (0, 1, 2):
        s = metrics.variant_by_day[d]["default"]["welcome_message"]["W3"]
        s[0] = 200
        s[1] = 100
        s[2] = 60

    # Days 3-4: engagement drops to (25/100 = 25%)
    for d in (3, 4):
        s = metrics.variant_by_day[d]["default"]["welcome_message"]["W3"]
        s[0] = 200
        s[1] = 100
        s[2] = 25

    decay = det.detect_variant_decay(metrics, "default", "welcome_message", "W3", current_day=4)
    assert decay is not None
    assert decay["drop_pct"] > 0.40


def test_governance_shift_and_clamping():
    old_cfg = {
        "cohorts": [],
        "allocations": {
            "default": {
                "caller_id": {"D1": 1.0, "D2": 0.0},
                "welcome_message": {"W1": 1.0},
                "voice": {"V1": 1.0},
            }
        },
        "prompt_version": "P1",
        "schedule": {},
    }
    target_cfg = {
        "cohorts": [],
        "allocations": {
            "default": {
                "caller_id": {"D1": 0.0, "D2": 1.0},
                "welcome_message": {"W1": 1.0},
                "voice": {"V1": 1.0},
            }
        },
        "prompt_version": "P1",
        "schedule": {},
    }

    # Shift is 1.0 TVD
    assert compute_max_shift(old_cfg, target_cfg) == 1.0

    # Clamp shift to 0.4
    clamped = clamp_shift_toward(old_cfg, target_cfg, max_shift=0.4)
    shift = compute_max_shift(old_cfg, clamped)
    assert shift <= 0.40001
    assert clamped["allocations"]["default"]["caller_id"]["D2"] > 0.35


def test_audit_store(tmp_path):
    db_file = tmp_path / "test_audit.db"
    store = AuditStore(str(db_file))

    store.set_checkpoint("test_key", "val_123")
    assert store.get_checkpoint("test_key") == "val_123"

    store.record_audit(
        ts="2027-01-04T10:00:00+05:30",
        sim_minute=600,
        workflow_id="nw_renewal",
        actor="controller_auto",
        version=2,
        changed_dims=["caller_id"],
        rationale="Rebalance caller IDs",
    )

    trail = store.query_audit_trail(workflow_id="nw_renewal")
    assert len(trail) == 1
    assert trail[0]["version"] == 2
    assert trail[0]["actor"] == "controller_auto"

    why = store.query_why_workflow_changed("nw_renewal", 2)
    assert why is not None
    assert why["rationale"] == "Rebalance caller IDs"
