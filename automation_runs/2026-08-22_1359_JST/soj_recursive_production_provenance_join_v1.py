from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

ENVELOPE_SCHEMA = "corrected-soj-production-caller-replay-envelope-v1"
MAIN_PROVENANCE_SCHEMA = "corrected-soj-production-main-provenance-v1"
RECURSIVE_PROVENANCE_STATUS = "certified_corrected_soj_recursive_caller_provenance_binding"
OUTPUT_STATUS = "certified_corrected_soj_recursive_production_provenance_join"
_SHA256_BARE_RE = re.compile(r"^[0-9a-f]{64}$")
_SHA256_PREFIXED_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_REQUIRED_ARTIFACT_FIELDS = (
    "branch_accounting_identity",
    "branch_certificate_identity",
    "original_instance_identity",
    "result_identity",
    "transition_identity",
)


@dataclass(frozen=True)
class RecursiveProductionProvenanceJoin:
    schema_version: int
    status: str
    certified: bool
    exact_contract_join: bool
    main_commit_sha: str
    caller_binding_identity: str
    envelope_identity: str
    main_provenance_identity: str
    recursive_provenance_identity: str
    result_status: str
    result_lift_digest: str
    accounting_binding_digest: str
    reduction_identity: str
    child_result_identity: str
    production_provenance_identity: str
    reason: str


def _fail(reason: str) -> RecursiveProductionProvenanceJoin:
    return RecursiveProductionProvenanceJoin(
        1,
        "corrected_soj_recursive_production_provenance_join_not_certified",
        False,
        False,
        "",
        "",
        "",
        "",
        "",
        "undetermined",
        "",
        "",
        "",
        "",
        "",
        reason,
    )


def _field(obj: Any, name: str) -> Any:
    if isinstance(obj, Mapping):
        if name not in obj:
            raise ValueError(f"missing required field {name!r}")
        return obj[name]
    if not hasattr(obj, name):
        raise ValueError(f"missing required field {name!r}")
    return getattr(obj, name)


def _literal_true(value: Any, name: str) -> None:
    if type(value) is not bool or value is not True:
        raise ValueError(f"{name} must be literal true")


def _strict_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _bare_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or _SHA256_BARE_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase 64-hex SHA-256")
    return value


def _prefixed_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or _SHA256_PREFIXED_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase sha256:<64-hex>")
    return value


def _git_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or _GIT_SHA_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase 40-hex Git SHA")
    return value


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a finite sequence")
    return value


def _repo_path(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/"):
        raise ValueError(f"{name} must be a nonempty repository-relative path")
    if "\\" in value or "\x00" in value or "\n" in value or "\r" in value or ":" in value:
        raise ValueError(f"{name} contains an unsafe path character")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"{name} must use canonical relative POSIX syntax")
    return value


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _bare_digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _prefixed_digest(payload: Mapping[str, Any]) -> str:
    return "sha256:" + _bare_digest(payload)


def _normalize_envelope(envelope: Any) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        raise ValueError("caller_replay_envelope must be a mapping")
    if _field(envelope, "schema") != ENVELOPE_SCHEMA:
        raise ValueError("caller replay envelope schema mismatch")
    caller_identity = _bare_sha(_field(envelope, "caller_binding_identity"), "envelope.caller_binding_identity")
    mode = _field(envelope, "mode")
    if mode != "larger_ground_recursive":
        raise ValueError("rev700 only accepts the larger_ground_recursive envelope")
    result_status = _field(envelope, "result_status")
    if result_status not in {"exact_nonempty", "exact_empty"} or not isinstance(result_status, str):
        raise ValueError("envelope.result_status is unsupported")
    original_identity = _bare_sha(_field(envelope, "original_instance_identity"), "envelope.original_instance_identity")
    transition_identity = _bare_sha(_field(envelope, "transition_identity"), "envelope.transition_identity")
    result_identity = _bare_sha(_field(envelope, "result_identity"), "envelope.result_identity")
    accounted_work = _strict_int(_field(envelope, "accounted_work"), "envelope.accounted_work")
    max_work = _strict_int(_field(envelope, "max_accounted_work"), "envelope.max_accounted_work")
    current = _strict_int(_field(envelope, "current_domain_size"), "envelope.current_domain_size", minimum=1)
    root_n = _strict_int(_field(envelope, "original_root_n"), "envelope.original_root_n", minimum=1)
    _literal_true(_field(envelope, "replay_verified"), "envelope.replay_verified")
    if accounted_work > max_work:
        raise ValueError("envelope accounted_work exceeds max_accounted_work")
    if current > root_n:
        raise ValueError("envelope current_domain_size exceeds original_root_n")
    observed_identity = _bare_sha(_field(envelope, "envelope_identity"), "envelope.envelope_identity")
    payload = {
        "schema": ENVELOPE_SCHEMA,
        "caller_binding_identity": caller_identity,
        "mode": mode,
        "result_status": result_status,
        "original_instance_identity": original_identity,
        "transition_identity": transition_identity,
        "result_identity": result_identity,
        "accounted_work": accounted_work,
        "max_accounted_work": max_work,
        "current_domain_size": current,
        "original_root_n": root_n,
        "replay_verified": True,
    }
    if _bare_digest(payload) != observed_identity:
        raise ValueError("envelope_identity does not replay from the public rev500 payload")
    return payload | {"envelope_identity": observed_identity}


def _normalize_main_provenance(provenance: Any, replay_verified: bool) -> dict[str, Any]:
    _literal_true(replay_verified, "main_provenance_replay_verified")
    if not isinstance(provenance, Mapping):
        raise ValueError("main_provenance must be a mapping")
    if _field(provenance, "schema") != MAIN_PROVENANCE_SCHEMA:
        raise ValueError("main provenance schema mismatch")
    main_commit = _git_sha(_field(provenance, "main_commit_sha"), "main_provenance.main_commit_sha")
    caller_identity = _bare_sha(_field(provenance, "caller_binding_identity"), "main_provenance.caller_binding_identity")
    envelope_identity = _bare_sha(_field(provenance, "envelope_identity"), "main_provenance.envelope_identity")
    observed_identity = _bare_sha(_field(provenance, "provenance_identity"), "main_provenance.provenance_identity")
    raw_artifacts = _sequence(_field(provenance, "verified_artifacts"), "main_provenance.verified_artifacts")
    if len(raw_artifacts) != len(_REQUIRED_ARTIFACT_FIELDS):
        raise ValueError("main provenance must contain exactly five verified identity artifacts")
    artifacts: list[dict[str, Any]] = []
    for i, expected_field in enumerate(_REQUIRED_ARTIFACT_FIELDS):
        raw = raw_artifacts[i]
        if not isinstance(raw, Mapping):
            raise ValueError(f"verified_artifacts[{i}] must be a mapping")
        if set(raw) != {"identity_field", "identity", "source_commit_sha", "source_path", "artifact_sha256"}:
            raise ValueError(f"verified_artifacts[{i}] has a noncanonical field set")
        identity_field = _field(raw, "identity_field")
        if identity_field != expected_field:
            raise ValueError("main provenance verified_artifacts are not in canonical rev600 order")
        artifacts.append(
            {
                "identity_field": identity_field,
                "identity": _bare_sha(_field(raw, "identity"), f"verified_artifacts[{i}].identity"),
                "source_commit_sha": _git_sha(_field(raw, "source_commit_sha"), f"verified_artifacts[{i}].source_commit_sha"),
                "source_path": _repo_path(_field(raw, "source_path"), f"verified_artifacts[{i}].source_path"),
                "artifact_sha256": _bare_sha(_field(raw, "artifact_sha256"), f"verified_artifacts[{i}].artifact_sha256"),
            }
        )
    payload = {
        "schema": MAIN_PROVENANCE_SCHEMA,
        "main_commit_sha": main_commit,
        "caller_binding_identity": caller_identity,
        "envelope_identity": envelope_identity,
        "verified_artifacts": artifacts,
    }
    if _bare_digest(payload) != observed_identity:
        raise ValueError("main provenance identity does not replay from the public rev600 payload")
    return payload | {"provenance_identity": observed_identity, "artifact_map": {a["identity_field"]: a["identity"] for a in artifacts}}


def _normalize_recursive_provenance(certificate: Any, replay_verified: bool) -> dict[str, Any]:
    _literal_true(replay_verified, "recursive_provenance_replay_verified")
    if _field(certificate, "schema_version") != 1:
        raise ValueError("recursive provenance schema version mismatch")
    if _field(certificate, "status") != RECURSIVE_PROVENANCE_STATUS:
        raise ValueError("recursive provenance status mismatch")
    _literal_true(_field(certificate, "certified"), "recursive_provenance.certified")
    _literal_true(_field(certificate, "exact_contract_binding"), "recursive_provenance.exact_contract_binding")
    caller_identity = _bare_sha(_field(certificate, "caller_binding_identity"), "recursive_provenance.caller_binding_identity")
    result_status = _field(certificate, "result_status")
    if result_status not in {"exact_nonempty", "exact_empty"} or not isinstance(result_status, str):
        raise ValueError("recursive_provenance.result_status is unsupported")
    return {
        "caller_binding_identity": caller_identity,
        "result_status": result_status,
        "result_lift_digest": _prefixed_sha(_field(certificate, "result_lift_digest"), "recursive_provenance.result_lift_digest"),
        "accounting_binding_digest": _prefixed_sha(_field(certificate, "accounting_binding_digest"), "recursive_provenance.accounting_binding_digest"),
        "reduction_identity": _prefixed_sha(_field(certificate, "reduction_identity"), "recursive_provenance.reduction_identity"),
        "child_result_identity": _prefixed_sha(_field(certificate, "child_result_identity"), "recursive_provenance.child_result_identity"),
        "provenance_identity": _prefixed_sha(_field(certificate, "provenance_identity"), "recursive_provenance.provenance_identity"),
    }


def certify_recursive_production_provenance_join(
    caller_replay_envelope: Mapping[str, Any],
    main_provenance: Mapping[str, Any],
    recursive_provenance: Any,
    *,
    main_provenance_replay_verified: bool,
    recursive_provenance_replay_verified: bool,
) -> RecursiveProductionProvenanceJoin:
    """Join rev500/rev600/rev650 public contracts without re-performing their semantics.

    rev500 and rev600 canonical digests are replayed here. The two explicit replay
    flags are still required because rev600's Git reachability checks and rev650's
    upstream result/accounting replays cannot be reconstructed from their compact
    output certificates alone. This function only certifies cross-contract identity
    compatibility; it does not execute recursive SI or prove main reachability.
    """
    try:
        envelope = _normalize_envelope(caller_replay_envelope)
        main = _normalize_main_provenance(main_provenance, main_provenance_replay_verified)
        recursive = _normalize_recursive_provenance(recursive_provenance, recursive_provenance_replay_verified)
    except (TypeError, ValueError) as exc:
        return _fail(str(exc))

    if envelope["caller_binding_identity"] != main["caller_binding_identity"]:
        return _fail("rev500 envelope and rev600 provenance disagree on caller binding identity")
    if envelope["caller_binding_identity"] != recursive["caller_binding_identity"]:
        return _fail("rev500 envelope and rev650 recursive provenance disagree on caller binding identity")
    if envelope["envelope_identity"] != main["envelope_identity"]:
        return _fail("rev600 provenance does not authenticate the supplied rev500 envelope identity")
    if envelope["result_status"] != recursive["result_status"]:
        return _fail("rev500 envelope and rev650 recursive provenance disagree on result status")

    artifact_map = main["artifact_map"]
    if artifact_map["original_instance_identity"] != envelope["original_instance_identity"]:
        return _fail("rev600 main artifact disagrees with the rev500 original instance identity")
    if artifact_map["transition_identity"] != envelope["transition_identity"]:
        return _fail("rev600 main artifact disagrees with the rev500 transition identity")
    if artifact_map["result_identity"] != envelope["result_identity"]:
        return _fail("rev600 main artifact disagrees with the rev500 result identity")

    result_lift_bare = recursive["result_lift_digest"].removeprefix("sha256:")
    accounting_bare = recursive["accounting_binding_digest"].removeprefix("sha256:")
    if envelope["result_identity"] != result_lift_bare:
        return _fail("rev500 result identity is not the replay-verified rev650 result-lift digest")
    if artifact_map["branch_certificate_identity"] != result_lift_bare:
        return _fail("rev600 branch certificate artifact is not the rev650 result-lift digest")
    if artifact_map["branch_accounting_identity"] != accounting_bare:
        return _fail("rev600 branch accounting artifact is not the rev650 accounting-binding digest")

    payload = {
        "schema_version": 1,
        "status": OUTPUT_STATUS,
        "main_commit_sha": main["main_commit_sha"],
        "caller_binding_identity": envelope["caller_binding_identity"],
        "envelope_identity": envelope["envelope_identity"],
        "main_provenance_identity": main["provenance_identity"],
        "recursive_provenance_identity": recursive["provenance_identity"],
        "result_status": recursive["result_status"],
        "result_lift_digest": recursive["result_lift_digest"],
        "accounting_binding_digest": recursive["accounting_binding_digest"],
        "reduction_identity": recursive["reduction_identity"],
        "child_result_identity": recursive["child_result_identity"],
    }
    production_identity = _prefixed_digest(payload)
    return RecursiveProductionProvenanceJoin(
        1,
        OUTPUT_STATUS,
        True,
        True,
        main["main_commit_sha"],
        envelope["caller_binding_identity"],
        envelope["envelope_identity"],
        main["provenance_identity"],
        recursive["provenance_identity"],
        recursive["result_status"],
        recursive["result_lift_digest"],
        recursive["accounting_binding_digest"],
        recursive["reduction_identity"],
        recursive["child_result_identity"],
        production_identity,
        "the replayed rev500 envelope, replay-verified rev600 main provenance, and replay-verified rev650 recursive producer provenance carry one exact recursive result/accounting identity chain",
    )


def replay_recursive_production_provenance_join(
    certificate: RecursiveProductionProvenanceJoin,
    caller_replay_envelope: Mapping[str, Any],
    main_provenance: Mapping[str, Any],
    recursive_provenance: Any,
    *,
    main_provenance_replay_verified: bool,
    recursive_provenance_replay_verified: bool,
) -> bool:
    if not isinstance(certificate, RecursiveProductionProvenanceJoin):
        return False
    if certificate.schema_version != 1 or not certificate.certified or not certificate.exact_contract_join:
        return False
    replay = certify_recursive_production_provenance_join(
        caller_replay_envelope,
        main_provenance,
        recursive_provenance,
        main_provenance_replay_verified=main_provenance_replay_verified,
        recursive_provenance_replay_verified=recursive_provenance_replay_verified,
    )
    return bool(replay.certified and replay == certificate and replay.production_provenance_identity == certificate.production_provenance_identity)


__all__ = [
    "RecursiveProductionProvenanceJoin",
    "certify_recursive_production_provenance_join",
    "replay_recursive_production_provenance_join",
]
