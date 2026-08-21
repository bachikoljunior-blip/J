#!/usr/bin/env python3
"""Bind every problem-solving phase to the durable parallel-claim registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

try:
    from automation.parallel_claims import (
        JST,
        Claim,
        ClaimFormatError,
        find_conflicts,
        load_registry,
        normalize_repo_path,
        normalize_scope,
        parse_jst_timestamp,
        repo_path_is_within,
        repo_paths_overlap,
        scopes_overlap,
    )
except ModuleNotFoundError:  # Direct ``python automation/<script>.py`` invocation.
    from parallel_claims import (  # type: ignore[no-redef]
        JST,
        Claim,
        ClaimFormatError,
        find_conflicts,
        load_registry,
        normalize_repo_path,
        normalize_scope,
        parse_jst_timestamp,
        repo_path_is_within,
        repo_paths_overlap,
        scopes_overlap,
    )


OBSERVE_PHASES = frozenset({"forecast", "select_leaf", "existing_solution_audit"})
EXCLUSIVE_PHASES = frozenset(
    {
        "attempt_solution",
        "decompose",
        "evaluate",
        "integrate_children",
        "solve_parent",
        "solve_root",
        "update_problem_tree",
        "publish",
        "merge",
    }
)
ALL_PHASES = OBSERVE_PHASES | EXCLUSIVE_PHASES


def scope_is_within(requested_scope: str, owner_scope: str) -> bool:
    requested = normalize_scope(requested_scope).split("/")
    owner = normalize_scope(owner_scope).split("/")
    return len(requested) >= len(owner) and requested[: len(owner)] == owner


def _claim_snapshot(claim: Claim, now: datetime) -> dict[str, Any]:
    return {
        "claim_id": claim.claim_id,
        "scope": claim.scope,
        "target_revision": claim.target_revision,
        "heartbeat_at_jst": claim.heartbeat_at.isoformat(),
        "state": claim.state_at(now),
        "branch": claim.branch,
        "reserved_paths": list(claim.reserved_paths),
    }


def snapshot_digest(snapshot: Iterable[dict[str, Any]]) -> str:
    normalized = sorted(snapshot, key=lambda item: item["claim_id"])
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def registry_digest(claims: Iterable[Claim], now: datetime) -> str:
    return snapshot_digest(
        _claim_snapshot(claim, now) for claim in claims if claim.is_fresh(now)
    )


def admit_problem_phase(
    claims: Iterable[Claim],
    *,
    claim_id: str,
    phase: str,
    scope: str,
    target_revision: int | None,
    now: datetime,
    registry_source_sha: str,
    paths: Iterable[str] = (),
) -> dict[str, Any]:
    if phase not in ALL_PHASES:
        raise ClaimFormatError(f"unknown problem-solving phase: {phase}")
    normalized_scope = normalize_scope(scope)
    if not normalized_scope:
        raise ClaimFormatError("scope must normalize to a non-empty path")
    normalized_paths = tuple(sorted({normalize_repo_path(path) for path in paths}))

    claim_list = list(claims)
    owners = [claim for claim in claim_list if claim.claim_id == claim_id]
    reasons: list[str] = []
    owner = owners[0] if len(owners) == 1 else None
    if len(owners) != 1:
        reasons.append("own_claim_missing_or_duplicate")
    elif owner.legacy:
        reasons.append("own_claim_not_schema_v2")
    elif not owner.is_fresh(now):
        reasons.append("own_claim_not_fresh")

    mode = "observe" if phase in OBSERVE_PHASES else "exclusive"
    conflicts: list[tuple[Claim, list[str]]] = []
    if mode == "exclusive" and owner is not None:
        if not scope_is_within(normalized_scope, owner.scope):
            reasons.append("scope_outside_own_claim")
        if target_revision != owner.target_revision:
            reasons.append("target_revision_differs_from_own_claim")
        if normalized_paths and not owner.reserved_paths:
            reasons.append("own_claim_has_no_reserved_paths")
        for path in normalized_paths:
            if not any(
                repo_path_is_within(path, reserved)
                for reserved in owner.reserved_paths
            ):
                reasons.append("path_outside_own_claim")
                break
        conflicts = find_conflicts(
            claim_list,
            scope=normalized_scope,
            target_revision=target_revision,
            now=now,
            exclude_claim_ids={claim_id},
            reserved_paths=normalized_paths,
        )
        if conflicts:
            reasons.append("parallel_claim_collision")

    active_parallel = sorted(
        (
        claim
        for claim in claim_list
        if claim.claim_id != claim_id and claim.is_fresh(now)
        ),
        key=lambda claim: claim.claim_id,
    )
    return {
        "admitted": not reasons,
        "phase": phase,
        "mode": mode,
        "scope": normalized_scope,
        "target_revision": target_revision,
        "paths": list(normalized_paths),
        "registry_source_sha": registry_source_sha,
        "registry_digest": registry_digest(claim_list, now),
        "own_claim": None if owner is None else _claim_snapshot(owner, now),
        "parallel_active_claims": [
            _claim_snapshot(claim, now) for claim in active_parallel
        ],
        "conflicts": [
            {**_claim_snapshot(claim, now), "reasons": collision_reasons}
            for claim, collision_reasons in conflicts
        ],
        "reasons": reasons,
    }


def evidence_payload(result: dict[str, Any], recorded_at: datetime) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "event_type": "problem_solving_phase_admission",
        "recorded_at_jst": recorded_at.isoformat(),
        **result,
    }


def validate_evidence_payload(payload: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if payload.get("event_type") != "problem_solving_phase_admission":
        errors.append("event_type is not problem_solving_phase_admission")
    if payload.get("admitted") is not True:
        errors.append("evidence must record an admitted phase")
    phase = payload.get("phase")
    if phase not in ALL_PHASES:
        errors.append("phase is unknown")
    expected_mode = "observe" if phase in OBSERVE_PHASES else "exclusive"
    if payload.get("mode") != expected_mode:
        errors.append("mode does not match phase")

    source_sha = payload.get("registry_source_sha")
    if not isinstance(source_sha, str) or len(source_sha) != 40:
        errors.append("registry_source_sha must be a 40-character commit SHA")
    owner = payload.get("own_claim")
    parallel = payload.get("parallel_active_claims")
    if not isinstance(owner, dict) or owner.get("state") != "active":
        errors.append("own_claim must be an active claim snapshot")
        owner = None
    if not isinstance(parallel, list) or not all(isinstance(item, dict) for item in parallel):
        errors.append("parallel_active_claims must be a list of snapshots")
        parallel = []

    if owner is not None:
        snapshots = [owner, *parallel]
        if payload.get("registry_digest") != snapshot_digest(snapshots):
            errors.append("registry_digest does not match embedded active claims")
        if expected_mode == "exclusive":
            if not scope_is_within(str(payload.get("scope", "")), str(owner.get("scope", ""))):
                errors.append("exclusive evidence scope is outside own claim")
            if payload.get("target_revision") != owner.get("target_revision"):
                errors.append("exclusive evidence revision differs from own claim")
            paths = payload.get("paths")
            if not isinstance(paths, list) or not all(isinstance(item, str) for item in paths):
                errors.append("paths must be a list of repository-relative strings")
                paths = []
            owner_paths = owner.get("reserved_paths", [])
            if not isinstance(owner_paths, list):
                errors.append("own_claim reserved_paths must be a list")
                owner_paths = []
            for path in paths:
                try:
                    if not any(repo_path_is_within(path, reserved) for reserved in owner_paths):
                        errors.append("exclusive evidence path is outside own claim")
                except ClaimFormatError:
                    errors.append("exclusive evidence path is invalid")
            for item in parallel:
                if scopes_overlap(str(payload.get("scope", "")), str(item.get("scope", ""))):
                    errors.append("exclusive evidence overlaps a parallel claim")
                target = payload.get("target_revision")
                if target is not None and target == item.get("target_revision"):
                    errors.append("exclusive evidence collides on target revision")
                parallel_paths = item.get("reserved_paths", [])
                if isinstance(parallel_paths, list):
                    for path in paths:
                        if any(repo_paths_overlap(path, other) for other in parallel_paths):
                            errors.append("exclusive evidence overlaps a parallel reserved path")
    return tuple(errors)


def _git_head(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--claim-id", required=True)
    parser.add_argument("--phase", choices=sorted(ALL_PHASES), required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--target-revision", type=int)
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--now")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    now = (
        datetime.now(JST)
        if args.now is None
        else parse_jst_timestamp(args.now, "--now", Path("<command-line>"))
    )
    claims, errors = load_registry(root)
    if errors:
        print(json.dumps({"admitted": False, "reasons": errors}, indent=2))
        return 3
    try:
        result = admit_problem_phase(
            claims,
            claim_id=args.claim_id,
            phase=args.phase,
            scope=args.scope,
            target_revision=args.target_revision,
            now=now,
            registry_source_sha=_git_head(root),
            paths=args.path,
        )
    except ClaimFormatError as exc:
        print(json.dumps({"admitted": False, "reasons": [str(exc)]}, indent=2))
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if args.output is not None and result["admitted"]:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(evidence_payload(result, now), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    return 0 if result["admitted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
