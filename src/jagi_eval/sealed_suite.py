from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class SuiteEligibility:
    eligible: bool
    reasons: tuple[str, ...]


def validate_sealed_suite(
    suite: Mapping[str, Any],
    candidate: Mapping[str, Any],
    prior_exposures: Sequence[Mapping[str, Any]] = (),
) -> SuiteEligibility:
    reasons: list[str] = []
    freeze_at = _parse_time(candidate.get("frozen_at"), "candidate.frozen_at", reasons)
    created_at = _parse_time(suite.get("created_at"), "suite.created_at", reasons)

    if freeze_at and created_at and created_at <= freeze_at:
        reasons.append("decisive suite must be created after candidate freeze")

    if suite.get("state") != "sealed":
        reasons.append("suite must be sealed before scored execution")
    if suite.get("answers_accessible_to_candidate") is not False:
        reasons.append("answers must be inaccessible to candidate")
    if suite.get("developer_has_task_access") is not False:
        reasons.append("candidate developers must not have decisive task access")
    if not _sha256ish(suite.get("suite_sha256")):
        reasons.append("suite_sha256 must be a 64-hex digest")

    tasks = suite.get("tasks")
    if not isinstance(tasks, Sequence) or isinstance(tasks, (str, bytes)) or not tasks:
        reasons.append("suite.tasks must contain task metadata")
    else:
        seen: set[str] = set()
        for idx, task in enumerate(tasks):
            if not isinstance(task, Mapping):
                reasons.append(f"task[{idx}] metadata invalid")
                continue
            digest = task.get("sha256")
            if not _sha256ish(digest):
                reasons.append(f"task[{idx}] sha256 invalid")
            elif digest in seen:
                reasons.append(f"task[{idx}] duplicate digest")
            seen.add(str(digest))
            generated_at = _parse_time(task.get("generated_at"), f"task[{idx}].generated_at", reasons)
            if freeze_at and generated_at and generated_at <= freeze_at:
                reasons.append(f"task[{idx}] not generated/materially transformed after freeze")
            if not task.get("template_id"):
                reasons.append(f"task[{idx}] missing template_id")
            if not task.get("cluster_id"):
                reasons.append(f"task[{idx}] missing cluster_id")

    candidate_hash = candidate.get("artifact_sha256")
    lineage_root = candidate.get("lineage_root")
    suite_id = suite.get("suite_id")
    if not suite_id or not lineage_root or not _sha256ish(candidate_hash):
        reasons.append("candidate/suite identity fields incomplete")
    else:
        for exposure in prior_exposures:
            if exposure.get("suite_id") != suite_id or exposure.get("lineage_root") != lineage_root:
                continue
            previous_hash = exposure.get("artifact_sha256")
            if previous_hash != candidate_hash:
                reasons.append("suite already exposed to another candidate in this lineage")
            elif exposure.get("reason") != "verified_infrastructure_rerun":
                reasons.append("suite already exposed to this frozen candidate")

    return SuiteEligibility(not reasons, tuple(reasons))


def _parse_time(value: Any, field: str, reasons: list[str]) -> datetime | None:
    if not isinstance(value, str):
        reasons.append(f"{field} must be an ISO-8601 timestamp")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        reasons.append(f"{field} must be an ISO-8601 timestamp")
        return None
    if parsed.tzinfo is None:
        reasons.append(f"{field} must include timezone")
        return None
    return parsed.astimezone(timezone.utc)


def _sha256ish(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
