from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

GATES = tuple(f"G{i}" for i in range(8))


@dataclass(frozen=True)
class ReportVerification:
    valid: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ConsensusDecision:
    passed: bool
    reasons: tuple[str, ...]
    team_ids: tuple[str, ...]


def canonical_report_bytes(report: Mapping[str, Any]) -> bytes:
    return json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def report_digest(report: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_report_bytes(report)).hexdigest()


def sign_report(report: Mapping[str, Any], private_key: Ed25519PrivateKey) -> str:
    return base64.b64encode(private_key.sign(canonical_report_bytes(report))).decode("ascii")


def public_key_b64(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


def verify_report(report: Mapping[str, Any], signature_b64: str, expected_public_key_b64: str) -> ReportVerification:
    reasons = _validate_report_shape(report)
    try:
        signature = base64.b64decode(signature_b64, validate=True)
        public_raw = base64.b64decode(expected_public_key_b64, validate=True)
        key = Ed25519PublicKey.from_public_bytes(public_raw)
        key.verify(signature, canonical_report_bytes(report))
    except (ValueError, InvalidSignature) as exc:
        reasons.append(f"invalid Ed25519 signature: {type(exc).__name__}")
    return ReportVerification(not reasons, tuple(reasons))


def replication_consensus(signed_reports: Sequence[Mapping[str, Any]], evaluator_registry: Mapping[str, Mapping[str, Any]]) -> ConsensusDecision:
    reasons: list[str] = []
    valid_reports: list[Mapping[str, Any]] = []
    seen_teams: set[str] = set()

    for index, envelope in enumerate(signed_reports):
        if not isinstance(envelope, Mapping):
            reasons.append(f"report envelope {index} invalid")
            continue
        report = envelope.get("report")
        signature = envelope.get("signature")
        if not isinstance(report, Mapping) or not isinstance(signature, str):
            reasons.append(f"report envelope {index} missing report/signature")
            continue
        team_id = str(report.get("evaluator_team", ""))
        registry = evaluator_registry.get(team_id)
        if not registry:
            reasons.append(f"unregistered evaluator team: {team_id or index}")
            continue
        if registry.get("independent") is not True:
            reasons.append(f"evaluator team not registered independent: {team_id}")
            continue
        verification = verify_report(report, signature, str(registry.get("public_key_b64", "")))
        if not verification.valid:
            reasons.extend(f"{team_id}: {r}" for r in verification.reasons)
            continue
        if team_id in seen_teams:
            reasons.append(f"duplicate evaluator team: {team_id}")
            continue
        seen_teams.add(team_id)
        valid_reports.append(report)

    if len(valid_reports) < 2:
        reasons.append("fewer than two valid independent signed reports")

    candidate_hashes = {r.get("candidate_sha256") for r in valid_reports}
    if len(candidate_hashes) > 1:
        reasons.append("independent reports do not refer to the same candidate")

    if valid_reports and not any(r.get("fresh_sealed_suite") is True for r in valid_reports):
        reasons.append("no independent report used a fresh sealed suite")

    for report in valid_reports:
        gates = report.get("gate_decisions", {})
        if any(gates.get(g) is not True for g in GATES):
            reasons.append(f"{report.get('evaluator_team')}: not all gates passed")

    return ConsensusDecision(not reasons, tuple(reasons), tuple(sorted(seen_teams)))


def _validate_report_shape(report: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    required_hashes = (
        "candidate_sha256",
        "harness_sha256",
        "environment_sha256",
        "suite_sha256",
        "preregistration_sha256",
        "metrics_sha256",
        "exclusions_sha256",
    )
    if not report.get("evaluator_team"):
        reasons.append("missing evaluator_team")
    for field in required_hashes:
        if not _sha256ish(report.get(field)):
            reasons.append(f"{field} must be a lowercase 64-hex digest")
    gates = report.get("gate_decisions")
    if not isinstance(gates, Mapping) or set(gates) != set(GATES):
        reasons.append("gate_decisions must contain exactly G0..G7")
    elif any(type(gates[g]) is not bool for g in GATES):
        reasons.append("gate_decisions values must be booleans")
    if type(report.get("fresh_sealed_suite")) is not bool:
        reasons.append("fresh_sealed_suite must be boolean")
    return reasons


def _sha256ish(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
