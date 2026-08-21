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
        normalize_scope,
        parse_jst_timestamp,
    )
except ModuleNotFoundError:  # Direct ``python automation/<script>.py`` invocation.
    from parallel_claims import (  # type: ignore[no-redef]
        JST,
        Claim,
        ClaimFormatError,
        find_conflicts,
        load_registry,
        normalize_scope,
        parse_jst_timestamp,
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
    }


def registry_digest(claims: Iterable[Claim], now: datetime) -> str:
    snapshot = sorted(
        (_claim_snapshot(claim, now) for claim in claims),
        key=lambda item: item["claim_id"],
    )
    encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def admit_problem_phase(
    claims: Iterable[Claim],
    *,
    claim_id: str,
    phase: str,
    scope: str,
    target_revision: int | None,
    now: datetime,
    registry_source_sha: str,
) -> dict[str, Any]:
    if phase not in ALL_PHASES:
        raise ClaimFormatError(f"unknown problem-solving phase: {phase}")
    normalized_scope = normalize_scope(scope)
    if not normalized_scope:
        raise ClaimFormatError("scope must normalize to a non-empty path")

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
        conflicts = find_conflicts(
            claim_list,
            scope=normalized_scope,
            target_revision=target_revision,
            now=now,
            exclude_claim_ids={claim_id},
        )
        if conflicts:
            reasons.append("parallel_claim_collision")

    active_parallel = [
        claim
        for claim in claim_list
        if claim.claim_id != claim_id and claim.is_fresh(now)
    ]
    return {
        "admitted": not reasons,
        "phase": phase,
        "mode": mode,
        "scope": normalized_scope,
        "target_revision": target_revision,
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
    parser.add_argument("--now")
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
        )
    except ClaimFormatError as exc:
        print(json.dumps({"admitted": False, "reasons": [str(exc)]}, indent=2))
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["admitted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
