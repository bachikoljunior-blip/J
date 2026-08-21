#!/usr/bin/env python3
"""Deterministically decide whether one durable J session needs an hourly re-fire.

The caller supplies only activity belonging to the claimed session.  Unrelated
branches, pull requests, claims, and workflows are deliberately outside this
decision so concurrent work can continue without masking a stopped session.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


JST = timezone(timedelta(hours=9))
CLOSED_STATES = {
    "closed",
    "completed",
    "completed_merged",
    "abandoned",
    "superseded",
    "cancelled",
}


class RefireFormatError(ValueError):
    """Raised when a session claim or activity timestamp is unsafe to use."""


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RefireFormatError(f"{field} must be a non-empty string")
    return value.strip()


def parse_activity_timestamp(value: Any, field: str) -> datetime:
    """Parse an aware ISO-8601 timestamp and normalize it to JST."""

    text = _require_text(value, field)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise RefireFormatError(f"{field} is not ISO 8601: {text!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RefireFormatError(f"{field} must include an explicit UTC offset")
    return parsed.astimezone(JST)


@dataclass(frozen=True)
class SessionClaim:
    claim_id: str
    status: str
    started_at: datetime
    heartbeat_at: datetime
    stale_after_minutes: int

    def is_closed(self) -> bool:
        return self.status.lower() in CLOSED_STATES


@dataclass(frozen=True)
class RefireDecision:
    claim_id: str
    claim_status: str
    should_refire: bool
    reason: str
    checked_at: datetime
    latest_activity_at: datetime
    refire_after: datetime
    activity_by_source: dict[str, datetime]

    def as_json(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_status": self.claim_status,
            "should_refire": self.should_refire,
            "reason": self.reason,
            "checked_at_jst": self.checked_at.isoformat(),
            "latest_activity_at_jst": self.latest_activity_at.isoformat(),
            "refire_after_jst": self.refire_after.isoformat(),
            "activity_by_source_jst": {
                source: timestamp.isoformat()
                for source, timestamp in sorted(self.activity_by_source.items())
            },
        }


def load_session_claim(path: Path, *, expected_claim_id: str | None = None) -> SessionClaim:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RefireFormatError(f"{path}: invalid claim JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RefireFormatError(f"{path}: claim must be a JSON object")

    claim_id = _require_text(
        payload.get("claim_id") or payload.get("session_id") or payload.get("automation_run_id"),
        "claim_id",
    )
    if expected_claim_id is not None and claim_id != expected_claim_id:
        raise RefireFormatError(
            f"{path}: claim_id {claim_id!r} does not match expected {expected_claim_id!r}"
        )

    status = _require_text(
        payload.get("status") or payload.get("coordination_state") or "active",
        "status",
    ).lower()
    started_at = parse_activity_timestamp(payload.get("started_at_jst"), "started_at_jst")
    heartbeat_at = parse_activity_timestamp(
        payload.get("heartbeat_at_jst")
        or payload.get("last_heartbeat_at_jst")
        or payload.get("completed_at_jst")
        or payload.get("started_at_jst"),
        "heartbeat_at_jst",
    )
    if heartbeat_at < started_at:
        raise RefireFormatError(f"{path}: heartbeat_at_jst precedes started_at_jst")

    stale_after = payload.get("stale_after_minutes")
    if stale_after is None and isinstance(payload.get("restart_guard"), dict):
        stale_after = payload["restart_guard"].get("stale_after_minutes")
    if isinstance(stale_after, bool) or not isinstance(stale_after, int) or stale_after <= 0:
        raise RefireFormatError(
            f"{path}: stale_after_minutes must be a positive integer"
        )

    return SessionClaim(
        claim_id=claim_id,
        status=status,
        started_at=started_at,
        heartbeat_at=heartbeat_at,
        stale_after_minutes=stale_after,
    )


def decide_refire(
    claim: SessionClaim,
    *,
    now: datetime,
    activity_by_source: dict[str, datetime] | None = None,
) -> RefireDecision:
    """Return a fail-safe, session-local re-fire decision."""

    if now.tzinfo is None or now.utcoffset() is None:
        raise RefireFormatError("now must include an explicit UTC offset")
    checked_at = now.astimezone(JST)

    activities = {"claim_heartbeat": claim.heartbeat_at}
    for source, timestamp in (activity_by_source or {}).items():
        source_name = _require_text(source, "activity source")
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise RefireFormatError(
                f"activity timestamp for {source_name!r} must include an explicit UTC offset"
            )
        activities[source_name] = timestamp.astimezone(JST)

    latest_activity = max(activities.values())
    refire_after = latest_activity + timedelta(minutes=claim.stale_after_minutes)

    if claim.is_closed():
        should_refire = False
        reason = "claim_closed"
    elif checked_at > refire_after:
        should_refire = True
        reason = "session_activity_stale"
    else:
        should_refire = False
        reason = "session_activity_fresh"

    return RefireDecision(
        claim_id=claim.claim_id,
        claim_status=claim.status,
        should_refire=should_refire,
        reason=reason,
        checked_at=checked_at,
        latest_activity_at=latest_activity,
        refire_after=refire_after,
        activity_by_source=activities,
    )


def _optional_activity(
    values: Iterable[tuple[str, str | None]],
) -> dict[str, datetime]:
    result: dict[str, datetime] = {}
    for source, value in values:
        if value:
            result[source] = parse_activity_timestamp(value, source)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser(
        "check",
        help="emit a deterministic re-fire decision for exactly one session claim",
    )
    check.add_argument("--claim-file", type=Path, required=True)
    check.add_argument("--claim-id", required=True)
    check.add_argument("--now", help="aware ISO-8601 timestamp; defaults to current time")
    check.add_argument("--branch-activity-at")
    check.add_argument("--pr-activity-at")
    return parser


def command_check(args: argparse.Namespace) -> int:
    claim = load_session_claim(args.claim_file, expected_claim_id=args.claim_id)
    now = (
        datetime.now(timezone.utc)
        if args.now is None
        else parse_activity_timestamp(args.now, "--now")
    )
    activity = _optional_activity(
        (
            ("branch_commit", args.branch_activity_at),
            ("pull_request_update", args.pr_activity_at),
        )
    )
    decision = decide_refire(claim, now=now, activity_by_source=activity)
    print(json.dumps(decision.as_json(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "check":
            return command_check(args)
        raise RefireFormatError(f"unsupported command: {args.command}")
    except RefireFormatError as exc:
        print(
            json.dumps(
                {
                    "should_refire": False,
                    "reason": "invalid_input",
                    "error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 3


if __name__ == "__main__":
    sys.exit(main())
