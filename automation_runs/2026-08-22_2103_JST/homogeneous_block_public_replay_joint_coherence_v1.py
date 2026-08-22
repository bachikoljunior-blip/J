from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
import re
from typing import Any, Mapping

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_RELATION_STATUS = {"ok", "exact_empty"}

class JointCoherenceError(ValueError):
    """Fail-closed validation error for rev3600 public replay coherence."""


def _literal_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise JointCoherenceError(f"{name} must be a literal bool")
    return value


def _literal_int(value: Any, name: str, *, minimum: int = 1) -> int:
    if type(value) is not int or value < minimum:
        raise JointCoherenceError(f"{name} must be a literal int >= {minimum}")
    return value


def _literal_str(value: Any, name: str) -> str:
    if type(value) is not str:
        raise JointCoherenceError(f"{name} must be a literal str")
    return value


def _sha(value: Any, name: str) -> str:
    value = _literal_str(value, name)
    if _HEX64.fullmatch(value) is None:
        raise JointCoherenceError(f"{name} must be lowercase sha256 hex")
    return value


def _closed(snapshot: Mapping[str, Any], fields: set[str], name: str) -> dict[str, Any]:
    if type(snapshot) is not dict:
        raise JointCoherenceError(f"{name} must be a literal dict")
    if set(snapshot) != fields:
        missing = sorted(fields - set(snapshot))
        extra = sorted(set(snapshot) - fields)
        raise JointCoherenceError(f"{name} schema drift: missing={missing}, extra={extra}")
    return snapshot


def _digest(domain: str, payload: Mapping[str, Any]) -> str:
    material = domain.encode("ascii") + b"\0" + json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(material).hexdigest()

ACTION_FIELDS = {
    "schema_version", "replay_verified", "status", "original_root_sha256",
    "domain_degree", "block_count", "block_size", "block_action_provenance_sha256",
    "kernel_factorization_sha256", "public_seal_sha256",
}
RELATION_FIELDS = {
    "schema_version", "replay_verified", "status", "original_root_sha256",
    "domain_degree", "block_count", "block_size", "relation_provenance_sha256",
    "relation_transcript_sha256", "public_seal_sha256",
}


def normalize_action_view(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    s = _closed(snapshot, ACTION_FIELDS, "action_snapshot")
    if _literal_int(s["schema_version"], "action.schema_version") != 1:
        raise JointCoherenceError("action.schema_version must equal 1")
    if not _literal_bool(s["replay_verified"], "action.replay_verified"):
        raise JointCoherenceError("action replay must be verified")
    if _literal_str(s["status"], "action.status") != "ok":
        raise JointCoherenceError("action.status must be ok")
    degree = _literal_int(s["domain_degree"], "action.domain_degree")
    count = _literal_int(s["block_count"], "action.block_count")
    size = _literal_int(s["block_size"], "action.block_size")
    if count * size != degree:
        raise JointCoherenceError("action block_count * block_size must equal domain_degree")
    return {
        "schema_version": 1,
        "replay_verified": True,
        "status": "ok",
        "original_root_sha256": _sha(s["original_root_sha256"], "action.original_root_sha256"),
        "domain_degree": degree,
        "block_count": count,
        "block_size": size,
        "block_action_provenance_sha256": _sha(s["block_action_provenance_sha256"], "action.block_action_provenance_sha256"),
        "kernel_factorization_sha256": _sha(s["kernel_factorization_sha256"], "action.kernel_factorization_sha256"),
        "public_seal_sha256": _sha(s["public_seal_sha256"], "action.public_seal_sha256"),
    }


def normalize_relation_view(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    s = _closed(snapshot, RELATION_FIELDS, "relation_snapshot")
    if _literal_int(s["schema_version"], "relation.schema_version") != 1:
        raise JointCoherenceError("relation.schema_version must equal 1")
    if not _literal_bool(s["replay_verified"], "relation.replay_verified"):
        raise JointCoherenceError("relation replay must be verified")
    status = _literal_str(s["status"], "relation.status")
    if status not in _ALLOWED_RELATION_STATUS:
        raise JointCoherenceError("relation.status must be ok or exact_empty")
    degree = _literal_int(s["domain_degree"], "relation.domain_degree")
    count = _literal_int(s["block_count"], "relation.block_count")
    size = _literal_int(s["block_size"], "relation.block_size")
    if count * size != degree:
        raise JointCoherenceError("relation block_count * block_size must equal domain_degree")
    return {
        "schema_version": 1,
        "replay_verified": True,
        "status": status,
        "original_root_sha256": _sha(s["original_root_sha256"], "relation.original_root_sha256"),
        "domain_degree": degree,
        "block_count": count,
        "block_size": size,
        "relation_provenance_sha256": _sha(s["relation_provenance_sha256"], "relation.relation_provenance_sha256"),
        "relation_transcript_sha256": _sha(s["relation_transcript_sha256"], "relation.relation_transcript_sha256"),
        "public_seal_sha256": _sha(s["public_seal_sha256"], "relation.public_seal_sha256"),
    }


@dataclass(frozen=True)
class JointReplayCoherenceCertificate:
    schema_version: int
    certified: bool
    status: str
    original_root_sha256: str
    domain_degree: int
    block_count: int
    block_size: int
    action_public_seal_sha256: str
    relation_public_seal_sha256: str
    block_action_provenance_sha256: str
    kernel_factorization_sha256: str
    relation_provenance_sha256: str
    relation_transcript_sha256: str
    coherence_identity: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_joint_coherence(action_snapshot: Mapping[str, Any], relation_snapshot: Mapping[str, Any]) -> JointReplayCoherenceCertificate:
    action = normalize_action_view(action_snapshot)
    relation = normalize_relation_view(relation_snapshot)
    shared = ("original_root_sha256", "domain_degree", "block_count", "block_size")
    drift = [key for key in shared if action[key] != relation[key]]
    if drift:
        raise JointCoherenceError(f"cross-snapshot shared-field drift: {drift}")
    if action["public_seal_sha256"] == relation["public_seal_sha256"]:
        raise JointCoherenceError("distinct upstream contracts must have distinct public seal identities")
    payload = {
        "schema_version": 1,
        "certified": True,
        "status": relation["status"],
        "original_root_sha256": action["original_root_sha256"],
        "domain_degree": action["domain_degree"],
        "block_count": action["block_count"],
        "block_size": action["block_size"],
        "action_public_seal_sha256": action["public_seal_sha256"],
        "relation_public_seal_sha256": relation["public_seal_sha256"],
        "block_action_provenance_sha256": action["block_action_provenance_sha256"],
        "kernel_factorization_sha256": action["kernel_factorization_sha256"],
        "relation_provenance_sha256": relation["relation_provenance_sha256"],
        "relation_transcript_sha256": relation["relation_transcript_sha256"],
    }
    identity = _digest("J/rev3600/homogeneous-block-public-replay-joint-coherence/v1", payload)
    return JointReplayCoherenceCertificate(**payload, coherence_identity=identity)


def verify_joint_coherence(certificate: Mapping[str, Any], action_snapshot: Mapping[str, Any], relation_snapshot: Mapping[str, Any]) -> bool:
    if type(certificate) is not dict:
        return False
    expected = build_joint_coherence(action_snapshot, relation_snapshot).to_dict()
    if set(certificate) != set(expected):
        return False
    for key, value in expected.items():
        if type(certificate[key]) is not type(value) or certificate[key] != value:
            return False
    return True
