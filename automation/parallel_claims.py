#!/usr/bin/env python3
"""Validate and query J's durable parallel-session claim registry.

The registry is intentionally repository-backed: every worker can reconstruct it
from ``main`` without relying on a shared process, local filesystem, or chat
session.  Canonical v2 claims live as one JSON file per session under
``agi/run-history/active``.  Older claim records are accepted read-only so the
protocol can be introduced without erasing history.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


JST = timezone(timedelta(hours=9))
DEFAULT_STALE_AFTER_MINUTES = 90
CLAIM_EVENT_TYPES = {"active_session_claim", "parallel_execution_claim"}
CLOSED_STATES = {
    "closed",
    "completed",
    "completed_merged",
    "abandoned",
    "superseded",
    "cancelled",
}


class ClaimFormatError(ValueError):
    """Raised when a registry entry cannot be interpreted safely."""


def _require_text(value: Any, field: str, path: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClaimFormatError(f"{path}: {field} must be a non-empty string")
    return value.strip()


def parse_jst_timestamp(value: Any, field: str, path: Path) -> datetime:
    text = _require_text(value, field, path)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ClaimFormatError(f"{path}: {field} is not ISO 8601: {text!r}") from exc
    if parsed.utcoffset() != JST.utcoffset(None):
        raise ClaimFormatError(f"{path}: {field} must carry the +09:00 JST offset")
    return parsed


def normalize_scope(value: str) -> str:
    """Return a stable hierarchical key, including for descriptive v1 scopes."""

    scope = value.strip().lower().replace("\\", "/")
    # Legacy entries append prose after their CRX path.  The first token is the
    # machine-comparable key; v2 entries forbid that ambiguity via ``scope``.
    if "/" in scope:
        scope = scope.split()[0]
    return "/".join(part for part in scope.strip("/").split("/") if part)


def scopes_overlap(left: str, right: str) -> bool:
    left_parts = normalize_scope(left).split("/")
    right_parts = normalize_scope(right).split("/")
    common = min(len(left_parts), len(right_parts))
    return left_parts[:common] == right_parts[:common]


@dataclass(frozen=True)
class Claim:
    claim_id: str
    session_id: str
    scope: str
    started_at: datetime
    heartbeat_at: datetime
    stale_after_minutes: int
    status: str
    target_revision: int | None
    branch: str | None
    path: Path
    legacy: bool
    completed_at: datetime | None

    def is_closed(self) -> bool:
        return self.completed_at is not None or self.status.lower() in CLOSED_STATES

    def is_fresh(self, now: datetime) -> bool:
        if self.is_closed():
            return False
        return now <= self.heartbeat_at + timedelta(minutes=self.stale_after_minutes)

    def state_at(self, now: datetime) -> str:
        if self.is_closed():
            return "closed"
        if self.is_fresh(now):
            return "active"
        return "stale"


def _optional_revision(value: Any, path: Path) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ClaimFormatError(f"{path}: target_revision must be a non-negative integer or null")
    return value


def load_claim(path: Path) -> Claim:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClaimFormatError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ClaimFormatError(f"{path}: claim must be a JSON object")

    event_type = data.get("event_type")
    if event_type not in CLAIM_EVENT_TYPES:
        raise ClaimFormatError(
            f"{path}: event_type must be one of {sorted(CLAIM_EVENT_TYPES)}"
        )

    schema_version = data.get("schema_version")
    if schema_version not in (None, 1, 2):
        raise ClaimFormatError(f"{path}: unsupported schema_version {schema_version!r}")

    canonical_required = {
        "claim_id",
        "session_id",
        "scope",
        "started_at_jst",
        "heartbeat_at_jst",
        "stale_after_minutes",
        "starting_main_sha",
        "starting_agi_gi_rev",
        "target_revision",
        "branch",
        "status",
        "agi_state",
    }
    # Other parallel workers may publish a conservative reservation with a
    # schema-v2 label but a singleton scope list or legacy base-SHA fields.
    # Recognize it as a blocking interoperability claim, but never grant it the
    # canonical ownership privileges used by phase admission.
    canonical = (
        schema_version == 2
        and canonical_required.issubset(data)
        and isinstance(data.get("scope"), str)
    )

    claim_id = data.get("claim_id") or data.get("session_id") or data.get("automation_run_id")
    if claim_id is None and event_type == "parallel_execution_claim":
        claim_id = path.stem
    claim_id = _require_text(claim_id, "claim_id", path)
    session_id = _require_text(
        data.get("session_id") or data.get("automation_run_id") or claim_id,
        "session_id",
        path,
    )

    scope_value = (
        data.get("scope")
        or data.get("exclusive_scope")
        or data.get("delegated_leaf")
        or data.get("completed_leaf")
    )
    if isinstance(scope_value, list):
        if len(scope_value) != 1 or not isinstance(scope_value[0], str):
            raise ClaimFormatError(
                f"{path}: interoperability scope list must contain exactly one string"
            )
        scope_value = scope_value[0]
    scope = normalize_scope(_require_text(scope_value, "scope", path))
    if not scope:
        raise ClaimFormatError(f"{path}: scope normalizes to an empty key")

    started_at = parse_jst_timestamp(data.get("started_at_jst"), "started_at_jst", path)
    heartbeat_value = (
        data.get("heartbeat_at_jst")
        or data.get("last_heartbeat_at_jst")
        or data.get("completed_at_jst")
        or data.get("started_at_jst")
    )
    heartbeat_at = parse_jst_timestamp(heartbeat_value, "heartbeat_at_jst", path)
    if heartbeat_at < started_at:
        raise ClaimFormatError(f"{path}: heartbeat_at_jst precedes started_at_jst")

    stale_value = data.get("stale_after_minutes")
    if stale_value is None and isinstance(data.get("restart_guard"), dict):
        stale_value = data["restart_guard"].get("stale_after_minutes")
    stale_after = DEFAULT_STALE_AFTER_MINUTES if stale_value is None else stale_value
    if isinstance(stale_after, bool) or not isinstance(stale_after, int) or stale_after <= 0:
        raise ClaimFormatError(f"{path}: stale_after_minutes must be a positive integer")

    completed_at = None
    if data.get("completed_at_jst") is not None:
        completed_at = parse_jst_timestamp(data["completed_at_jst"], "completed_at_jst", path)
        if completed_at < started_at:
            raise ClaimFormatError(f"{path}: completed_at_jst precedes started_at_jst")

    status_value = data.get("status") or data.get("coordination_state")
    if status_value is None:
        status_value = "closed" if completed_at else "active"
    status = _require_text(status_value, "status", path).lower()

    branch_value = data.get("branch") or data.get("completed_branch")
    branch = None if branch_value is None else _require_text(branch_value, "branch", path)
    revision = _optional_revision(data.get("target_revision"), path)

    if canonical:
        if event_type != "active_session_claim":
            raise ClaimFormatError(f"{path}: schema v2 requires active_session_claim")
        if path.stem != claim_id:
            raise ClaimFormatError(f"{path}: filename stem must equal claim_id")
        starting_sha = _require_text(data.get("starting_main_sha"), "starting_main_sha", path)
        if re.fullmatch(r"[0-9a-f]{40}", starting_sha) is None:
            raise ClaimFormatError(f"{path}: starting_main_sha must be 40 lowercase hex digits")
        starting_rev = data.get("starting_agi_gi_rev")
        if isinstance(starting_rev, bool) or not isinstance(starting_rev, int) or starting_rev < 0:
            raise ClaimFormatError(
                f"{path}: starting_agi_gi_rev must be a non-negative integer"
            )
        _require_text(data.get("branch"), "branch", path)
        canonical_scope = _require_text(data.get("scope"), "scope", path)
        if any(character.isspace() for character in canonical_scope):
            raise ClaimFormatError(
                f"{path}: schema-v2 scope must be a slash path without whitespace or prose"
            )
        if data.get("agi_state") != "NOT_AGI":
            raise ClaimFormatError(f"{path}: operational claims must not assert AGI")

    return Claim(
        claim_id=claim_id,
        session_id=session_id,
        scope=scope,
        started_at=started_at,
        heartbeat_at=heartbeat_at,
        stale_after_minutes=stale_after,
        status=status,
        target_revision=revision,
        branch=branch,
        path=path,
        legacy=not canonical,
        completed_at=completed_at,
    )


def load_registry(root: Path) -> tuple[list[Claim], list[str]]:
    claim_dir = root / "agi" / "run-history" / "active"
    claims: list[Claim] = []
    errors: list[str] = []
    if not claim_dir.is_dir():
        return [], [f"{claim_dir}: claim directory does not exist"]
    for path in sorted(claim_dir.glob("*.json")):
        try:
            claims.append(load_claim(path))
        except ClaimFormatError as exc:
            errors.append(str(exc))
    return claims, errors


def find_conflicts(
    claims: Iterable[Claim],
    *,
    scope: str,
    target_revision: int | None,
    now: datetime,
    exclude_claim_ids: set[str] | None = None,
) -> list[tuple[Claim, list[str]]]:
    excluded = exclude_claim_ids or set()
    normalized_scope = normalize_scope(scope)
    conflicts: list[tuple[Claim, list[str]]] = []
    for claim in claims:
        if claim.claim_id in excluded or not claim.is_fresh(now):
            continue
        reasons: list[str] = []
        if scopes_overlap(normalized_scope, claim.scope):
            reasons.append("scope_overlap")
        if target_revision is not None and claim.target_revision == target_revision:
            reasons.append("target_revision_collision")
        if reasons:
            conflicts.append((claim, reasons))
    return conflicts


def find_registry_collisions(
    claims: Iterable[Claim], *, now: datetime
) -> list[tuple[Claim, Claim, list[str]]]:
    fresh = [claim for claim in claims if claim.is_fresh(now)]
    collisions: list[tuple[Claim, Claim, list[str]]] = []
    for left_index, left in enumerate(fresh):
        for right in fresh[left_index + 1 :]:
            reasons: list[str] = []
            if scopes_overlap(left.scope, right.scope):
                reasons.append("scope_overlap")
            if (
                left.target_revision is not None
                and left.target_revision == right.target_revision
            ):
                reasons.append("target_revision_collision")
            if reasons:
                collisions.append((left, right, reasons))
    return collisions


def _now_from_argument(value: str | None) -> datetime:
    if value is None:
        return datetime.now(JST)
    return parse_jst_timestamp(value, "--now", Path("<command-line>"))


def _claim_json(claim: Claim, now: datetime) -> dict[str, Any]:
    return {
        "claim_id": claim.claim_id,
        "session_id": claim.session_id,
        "scope": claim.scope,
        "target_revision": claim.target_revision,
        "branch": claim.branch,
        "state": claim.state_at(now),
        "heartbeat_at_jst": claim.heartbeat_at.isoformat(),
        "stale_after_minutes": claim.stale_after_minutes,
        "legacy": claim.legacy,
        "path": claim.path.as_posix(),
    }


def command_validate(args: argparse.Namespace) -> int:
    now = _now_from_argument(args.now)
    claims, errors = load_registry(args.root)
    collisions = find_registry_collisions(claims, now=now)
    result = {
        "valid": not errors and not collisions,
        "claims": [_claim_json(claim, now) for claim in claims],
        "collisions": [
            {
                "left_claim_id": left.claim_id,
                "right_claim_id": right.claim_id,
                "reasons": reasons,
            }
            for left, right, reasons in collisions
        ],
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not errors and not collisions else 3


def command_check(args: argparse.Namespace) -> int:
    now = _now_from_argument(args.now)
    normalized_scope = normalize_scope(args.scope)
    if not normalized_scope:
        raise ClaimFormatError("--scope must normalize to a non-empty hierarchical key")
    if args.target_revision is not None and args.target_revision < 0:
        raise ClaimFormatError("--target-revision must be non-negative")
    claims, errors = load_registry(args.root)
    if errors:
        print(
            json.dumps(
                {"available": False, "reason": "invalid_registry", "errors": errors},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 3
    conflicts = find_conflicts(
        claims,
        scope=args.scope,
        target_revision=args.target_revision,
        now=now,
        exclude_claim_ids=set(args.exclude_claim_id),
    )
    payload = {
        "available": not conflicts,
        "scope": normalized_scope,
        "target_revision": args.target_revision,
        "checked_at_jst": now.isoformat(),
        "conflicts": [
            {**_claim_json(claim, now), "reasons": reasons}
            for claim, reasons in conflicts
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not conflicts else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate every JSON claim")
    validate.add_argument("--root", type=Path, default=Path.cwd())
    validate.add_argument("--now", help="deterministic JST timestamp for state reporting")
    validate.set_defaults(func=command_validate)

    check = subparsers.add_parser("check", help="fail closed on a live scope/revision collision")
    check.add_argument("--root", type=Path, default=Path.cwd())
    check.add_argument("--scope", required=True)
    check.add_argument("--target-revision", type=int)
    check.add_argument("--exclude-claim-id", action="append", default=[])
    check.add_argument("--now", help="deterministic JST timestamp for tests or replay")
    check.set_defaults(func=command_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ClaimFormatError as exc:
        print(json.dumps({"available": False, "reason": "invalid_input", "error": str(exc)}))
        return 3


if __name__ == "__main__":
    sys.exit(main())
