"""Evaluator-owned autonomy telemetry and derived metrics.

Events are emitted by the harness/environment, never trusted from candidate
stdout. The log is hash-chained so interventions, faults and policy violations
cannot be removed without invalidating the evidence.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

ALLOWED_EVENTS = {
    "episode_start",
    "candidate_start",
    "candidate_exit",
    "environment_fault",
    "recovery_observed",
    "checkpoint_written",
    "checkpoint_restored",
    "policy_violation",
    "human_intervention",
    "resource_charge",
    "episode_complete",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass
class TelemetryLog:
    episode_id: str
    events: list[dict[str, Any]] = field(default_factory=list)
    _prev: str = field(default="0" * 64, init=False, repr=False)

    def emit(self, event: str, **data: Any) -> dict[str, Any]:
        if event not in ALLOWED_EVENTS:
            raise ValueError(f"unsupported telemetry event: {event}")
        rec = {
            "seq": len(self.events),
            "episode_id": self.episode_id,
            "event": event,
            "monotonic_s": time.monotonic(),
            "data": data,
            "previous_sha256": self._prev,
        }
        payload = {k: v for k, v in rec.items() if k != "record_sha256"}
        rec["record_sha256"] = hashlib.sha256((self._prev + _canonical(payload)).encode()).hexdigest()
        self._prev = rec["record_sha256"]
        self.events.append(rec)
        return rec

    @property
    def chain_tip(self) -> str:
        return self._prev


def verify_telemetry(events: list[dict], expected_tip: str | None = None) -> list[str]:
    errors: list[str] = []
    prev = "0" * 64
    episode = None
    for i, rec in enumerate(events):
        if rec.get("seq") != i:
            errors.append(f"event[{i}] sequence mismatch")
        if episode is None:
            episode = rec.get("episode_id")
        elif rec.get("episode_id") != episode:
            errors.append(f"event[{i}] episode mismatch")
        if rec.get("event") not in ALLOWED_EVENTS:
            errors.append(f"event[{i}] unsupported type")
        if rec.get("previous_sha256") != prev:
            errors.append(f"event[{i}] previous hash mismatch")
        payload = {k: v for k, v in rec.items() if k != "record_sha256"}
        digest = hashlib.sha256((prev + _canonical(payload)).encode()).hexdigest()
        if rec.get("record_sha256") != digest:
            errors.append(f"event[{i}] hash mismatch")
        prev = digest
    if expected_tip is not None and prev != expected_tip:
        errors.append("telemetry chain tip mismatch")
    return errors


def derive_autonomy_metrics(events: list[dict]) -> dict[str, Any]:
    """Derive required autonomy metrics only from evaluator-owned events."""
    if verify_telemetry(events):
        raise ValueError("cannot derive autonomy metrics from invalid telemetry")
    if not events:
        return {
            "completion_rate": 0.0,
            "intervention_count": 0,
            "recovery_rate": 0.0,
            "elapsed_time": 0.0,
            "resource_cost": 0.0,
            "policy_violations": 0,
            "state_persistence_success": 0.0,
        }
    starts = [e for e in events if e["event"] == "episode_start"]
    completes = [e for e in events if e["event"] == "episode_complete" and e.get("data", {}).get("success") is True]
    interventions = sum(1 for e in events if e["event"] == "human_intervention")
    faults = sum(1 for e in events if e["event"] == "environment_fault")
    recoveries = sum(1 for e in events if e["event"] == "recovery_observed" and e.get("data", {}).get("success") is True)
    policy = sum(1 for e in events if e["event"] == "policy_violation")
    charges = sum(float(e.get("data", {}).get("amount", 0.0)) for e in events if e["event"] == "resource_charge")
    restores = [e for e in events if e["event"] == "checkpoint_restored"]
    restored_ok = sum(1 for e in restores if e.get("data", {}).get("success") is True)
    elapsed = max(0.0, float(events[-1]["monotonic_s"]) - float(events[0]["monotonic_s"]))
    return {
        "completion_rate": len(completes) / max(1, len(starts)),
        "intervention_count": interventions,
        "recovery_rate": recoveries / faults if faults else 1.0,
        "elapsed_time": elapsed,
        "resource_cost": charges,
        "policy_violations": policy,
        "state_persistence_success": restored_ok / len(restores) if restores else 1.0,
        "fault_count": faults,
        "successful_recoveries": recoveries,
        "checkpoint_restore_attempts": len(restores),
    }
