import hashlib
import json

import pytest

from arena import grade_workspace, materialize_workspace, snapshot_workspace, validate_arena_grader
from autonomy import TelemetryLog, derive_autonomy_metrics, verify_telemetry


def test_workspace_snapshot_and_private_file_grader(tmp_path):
    inp, work = tmp_path / "input", tmp_path / "work"
    public = {"workspace_files": {"src/a.txt": "alpha", "data.json": '{"x":1}'}}
    materialize_workspace(public, inp, work)
    snap = snapshot_workspace(work)
    expected = hashlib.sha256(b"alpha").hexdigest()
    private = {"arena_grader": {"type": "file_sha256", "files": {"src/a.txt": expected}}}
    assert validate_arena_grader(private) == []
    passed, evidence = grade_workspace(private, work, snap)
    assert passed and evidence["checks"][0]["passed"]
    (work / "src/a.txt").write_text("tampered")
    passed, _ = grade_workspace(private, work)
    assert not passed


def test_json_equal_grader(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    (work / "result.json").write_text(json.dumps({"answer": 42}))
    private = {"arena_grader": {"type": "json_equal", "path": "result.json", "expected": {"answer": 42}}}
    assert grade_workspace(private, work)[0]


def test_symlinks_rejected(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    (work / "real").write_text("x")
    (work / "link").symlink_to(work / "real")
    with pytest.raises(ValueError):
        snapshot_workspace(work)


def test_autonomy_metrics_and_tamper_detection():
    log = TelemetryLog("ep1")
    log.emit("episode_start")
    log.emit("candidate_start")
    log.emit("environment_fault", kind="synthetic")
    log.emit("checkpoint_written", checkpoint="c1")
    log.emit("checkpoint_restored", checkpoint="c1", success=True)
    log.emit("recovery_observed", success=True)
    log.emit("resource_charge", amount=2.5, unit="credits")
    log.emit("episode_complete", success=True)
    assert verify_telemetry(log.events, log.chain_tip) == []
    metrics = derive_autonomy_metrics(log.events)
    assert metrics["completion_rate"] == 1.0
    assert metrics["recovery_rate"] == 1.0
    assert metrics["state_persistence_success"] == 1.0
    assert metrics["resource_cost"] == 2.5
    assert metrics["intervention_count"] == 0
    assert metrics["policy_violations"] == 0
    log.events[2]["data"]["kind"] = "hidden edit"
    assert verify_telemetry(log.events, log.chain_tip)
