from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.parallel_claims import (  # noqa: E402
    JST,
    Claim,
    ClaimFormatError,
    find_conflicts,
    find_registry_collisions,
    load_claim,
    load_registry,
    parse_jst_timestamp,
)

SCHEMA_VERSION = 1
EVENT_TYPE = "claim_publication_preflight"
MODES = frozenset({"prepublish", "published-audit", "registry-audit"})


def _claim_snapshot(claim: Claim, now: datetime) -> dict[str, Any]:
    return {
        "claim_id": claim.claim_id,
        "scope": claim.scope,
        "target_revision": claim.target_revision,
        "heartbeat_at_jst": claim.heartbeat_at.isoformat(),
        "state": claim.state_at(now),
        "branch": claim.branch,
        "reserved_paths": list(claim.reserved_paths),
        "legacy": claim.legacy,
    }


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _fresh_registry_snapshot(claims: Iterable[Claim], now: datetime) -> list[dict[str, Any]]:
    return sorted(
        (_claim_snapshot(claim, now) for claim in claims if claim.is_fresh(now)),
        key=lambda item: item["claim_id"],
    )


def _base_result(mode: str, now: datetime) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "event_type": EVENT_TYPE,
        "mode": mode,
        "recorded_at_jst": now.isoformat(),
        "admitted": False,
        "reasons": [],
        "candidate": None,
        "registry_digest": None,
        "fresh_registry": [],
        "conflicts": [],
    }


def _load_registry_fail_closed(root: Path) -> tuple[list[Claim], list[str]]:
    claims, errors = load_registry(root)
    if errors:
        return [], [f"registry_format_error: {error}" for error in errors]
    return claims, []


def _load_candidate_payload(payload: Mapping[str, Any]) -> Claim:
    if not isinstance(payload, Mapping):
        raise ClaimFormatError("candidate must be a JSON object")
    claim_id = payload.get("claim_id")
    if not isinstance(claim_id, str) or not claim_id.strip():
        raise ClaimFormatError("candidate claim_id must be a non-empty string")
    with tempfile.TemporaryDirectory(prefix="j-claim-preflight-") as tmp:
        path = Path(tmp) / f"{claim_id}.json"
        path.write_text(
            json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        claim = load_claim(path)
    if claim.legacy:
        raise ClaimFormatError("candidate must be canonical schema-v2")
    return claim


def _conflict_snapshot(conflicts: Iterable[tuple[Claim, list[str]]], now: datetime) -> list[dict[str, Any]]:
    return sorted(
        ({**_claim_snapshot(claim, now), "reasons": sorted(reasons)} for claim, reasons in conflicts),
        key=lambda item: item["claim_id"],
    )


def preflight_candidate(payload: Mapping[str, Any], root: Path, now: datetime) -> dict[str, Any]:
    result = _base_result("prepublish", now)
    claims, registry_errors = _load_registry_fail_closed(root)
    if registry_errors:
        result["reasons"] = registry_errors
        return result
    fresh = _fresh_registry_snapshot(claims, now)
    result["fresh_registry"] = fresh
    result["registry_digest"] = _digest(fresh)

    try:
        candidate = _load_candidate_payload(payload)
    except (ClaimFormatError, OSError, TypeError, ValueError) as exc:
        result["reasons"] = [f"candidate_format_error: {exc}"]
        return result

    result["candidate"] = _claim_snapshot(candidate, now)
    reasons: list[str] = []
    if candidate.is_closed():
        reasons.append("candidate_closed")
    elif not candidate.is_fresh(now):
        reasons.append("candidate_not_fresh")
    if any(claim.claim_id == candidate.claim_id for claim in claims):
        reasons.append("candidate_already_published")

    conflicts = find_conflicts(
        claims,
        scope=candidate.scope,
        target_revision=candidate.target_revision,
        now=now,
        reserved_paths=candidate.reserved_paths,
    )
    result["conflicts"] = _conflict_snapshot(conflicts, now)
    if conflicts:
        reasons.append("parallel_claim_collision")
    result["reasons"] = sorted(set(reasons))
    result["admitted"] = not result["reasons"]
    return result


def audit_published_candidate(payload: Mapping[str, Any], root: Path, now: datetime) -> dict[str, Any]:
    result = _base_result("published-audit", now)
    claims, registry_errors = _load_registry_fail_closed(root)
    if registry_errors:
        result["reasons"] = registry_errors
        return result
    fresh = _fresh_registry_snapshot(claims, now)
    result["fresh_registry"] = fresh
    result["registry_digest"] = _digest(fresh)

    try:
        candidate = _load_candidate_payload(payload)
    except (ClaimFormatError, OSError, TypeError, ValueError) as exc:
        result["reasons"] = [f"candidate_format_error: {exc}"]
        return result

    result["candidate"] = _claim_snapshot(candidate, now)
    owners = [claim for claim in claims if claim.claim_id == candidate.claim_id]
    reasons: list[str] = []
    if len(owners) != 1:
        reasons.append("published_claim_missing_or_duplicate")
        owner = candidate
    else:
        owner = owners[0]
        if owner.legacy:
            reasons.append("published_claim_not_schema_v2")
        if owner.is_closed():
            reasons.append("published_claim_closed")
        elif not owner.is_fresh(now):
            reasons.append("published_claim_not_fresh")
        if (
            owner.scope != candidate.scope
            or owner.target_revision != candidate.target_revision
            or owner.branch != candidate.branch
            or owner.reserved_paths != candidate.reserved_paths
        ):
            reasons.append("published_claim_differs_from_candidate")

    conflicts = find_conflicts(
        claims,
        scope=owner.scope,
        target_revision=owner.target_revision,
        now=now,
        exclude_claim_ids={candidate.claim_id},
        reserved_paths=owner.reserved_paths,
    )
    result["conflicts"] = _conflict_snapshot(conflicts, now)
    if conflicts:
        reasons.append("parallel_claim_collision")
    result["reasons"] = sorted(set(reasons))
    result["admitted"] = not result["reasons"]
    return result


def audit_registry(root: Path, now: datetime) -> dict[str, Any]:
    result = _base_result("registry-audit", now)
    claims, registry_errors = _load_registry_fail_closed(root)
    if registry_errors:
        result["reasons"] = registry_errors
        return result
    fresh = _fresh_registry_snapshot(claims, now)
    result["fresh_registry"] = fresh
    result["registry_digest"] = _digest(fresh)
    collisions = []
    for left, right, reasons in find_registry_collisions(claims, now=now):
        pair = sorted((_claim_snapshot(left, now), _claim_snapshot(right, now)), key=lambda item: item["claim_id"])
        collisions.append({"left": pair[0], "right": pair[1], "reasons": sorted(reasons)})
    collisions.sort(key=lambda item: (item["left"]["claim_id"], item["right"]["claim_id"], item["reasons"]))
    result["conflicts"] = collisions
    if collisions:
        result["reasons"] = ["registry_has_fresh_collisions"]
    else:
        result["admitted"] = True
    return result


def _read_payload(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClaimFormatError(f"cannot read candidate JSON: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise ClaimFormatError("candidate JSON must be an object")
    return payload


def _write_result(path: Path | None, result: dict[str, Any]) -> None:
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    print(text, end="")
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail-closed preflight/audit for J parallel claim publication")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--mode", required=True, choices=sorted(MODES))
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--now")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    now = (
        datetime.now(JST)
        if args.now is None
        else parse_jst_timestamp(args.now, "--now", Path("<command-line>"))
    )
    root = args.root.resolve()
    if args.mode == "registry-audit":
        result = audit_registry(root, now)
    else:
        if args.candidate is None:
            parser.error("--candidate is required for prepublish and published-audit modes")
        try:
            payload = _read_payload(args.candidate)
        except ClaimFormatError as exc:
            result = _base_result(args.mode, now)
            result["reasons"] = [f"candidate_format_error: {exc}"]
        else:
            if args.mode == "prepublish":
                result = preflight_candidate(payload, root, now)
            else:
                result = audit_published_candidate(payload, root, now)
    _write_result(args.output, result)
    if result["admitted"]:
        return 0
    if any(str(reason).startswith(("candidate_format_error", "registry_format_error")) for reason in result["reasons"]):
        return 3
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
