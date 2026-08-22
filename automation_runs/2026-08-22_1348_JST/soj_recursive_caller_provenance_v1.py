from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

CALLER_SCHEMA = "corrected-soj-production-caller-binding-v1"
ACCOUNTING_STATUS = "certified_johnson_recursive_result_accounting_binding"
LIFT_NONEMPTY_STATUS = "certified_exact_parent_johnson_coset_lift"
LIFT_EMPTY_STATUS = "certified_exact_empty_parent_johnson_result"
OUTPUT_STATUS = "certified_corrected_soj_recursive_caller_provenance_binding"
_SHA256_BARE_RE = re.compile(r"^[0-9a-f]{64}$")
_SHA256_PREFIXED_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class RecursiveCallerProvenanceBinding:
    schema_version: int
    status: str
    certified: bool
    exact_contract_binding: bool
    caller_binding_identity: str
    result_status: str
    result_lift_digest: str
    accounting_binding_digest: str
    reduction_identity: str
    child_result_identity: str
    provenance_identity: str
    reason: str


def _fail(reason: str) -> RecursiveCallerProvenanceBinding:
    return RecursiveCallerProvenanceBinding(
        1,
        "corrected_soj_recursive_caller_provenance_not_certified",
        False,
        False,
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


def _strict_true(obj: Any, name: str) -> None:
    value = _field(obj, name)
    if type(value) is not bool or value is not True:
        raise ValueError(f"{name} must be literal true")


def _strict_int(obj: Any, name: str) -> int:
    value = _field(obj, name)
    if type(value) is not int:
        raise ValueError(f"{name} must be a strict integer")
    return value


def _bare_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or _SHA256_BARE_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase 64-hex SHA-256")
    return value


def _prefixed_sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or _SHA256_PREFIXED_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase sha256:<64-hex>")
    return value


def _strip_sha256(value: str) -> str:
    return value.removeprefix("sha256:")


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a finite sequence")
    return value


def _permutation(value: Any, degree: int, name: str) -> tuple[int, ...]:
    seq = _sequence(value, name)
    if len(seq) != degree:
        raise ValueError(f"{name} has the wrong action degree")
    out: list[int] = []
    for i, image in enumerate(seq):
        if type(image) is not int:
            raise ValueError(f"{name}[{i}] must be a strict integer")
        out.append(image)
    perm = tuple(out)
    if any(image < 0 or image >= degree for image in perm) or len(set(perm)) != degree:
        raise ValueError(f"{name} is not a permutation of 0..{degree - 1}")
    return perm


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _bare_digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _prefixed_digest(payload: Mapping[str, Any]) -> str:
    return "sha256:" + _bare_digest(payload)


def _normalize_caller_binding(binding: Any) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        raise ValueError("caller_binding must be a mapping")
    if _field(binding, "schema") != CALLER_SCHEMA:
        raise ValueError("caller binding schema mismatch")
    _strict_true(binding, "canonical")
    _strict_true(binding, "exact")
    if _field(binding, "mode") != "larger_ground_recursive":
        raise ValueError("recursive provenance binding requires larger_ground_recursive mode")
    result_status = _field(binding, "result_status")
    if result_status not in {"exact_nonempty", "exact_empty"} or not isinstance(result_status, str):
        raise ValueError("unsupported caller result_status")
    original_instance_identity = _bare_sha(_field(binding, "original_instance_identity"), "original_instance_identity")
    transition_identity = _bare_sha(_field(binding, "transition_identity"), "transition_identity")
    result_identity = _bare_sha(_field(binding, "result_identity"), "result_identity")
    branch_certificate_identity = _bare_sha(
        _field(binding, "branch_certificate_identity"), "branch_certificate_identity"
    )
    branch_accounting_identity = _bare_sha(
        _field(binding, "branch_accounting_identity"), "branch_accounting_identity"
    )
    accounted_work = _field(binding, "accounted_work")
    if type(accounted_work) is not int or accounted_work < 0:
        raise ValueError("accounted_work must be a nonnegative integer")
    caller_binding_identity = _bare_sha(_field(binding, "caller_binding_identity"), "caller_binding_identity")
    if branch_certificate_identity != result_identity:
        raise ValueError("rev400 recursive branch certificate identity must equal result identity")
    payload = {
        "schema": CALLER_SCHEMA,
        "canonical": True,
        "exact": True,
        "mode": "larger_ground_recursive",
        "original_instance_identity": original_instance_identity,
        "transition_identity": transition_identity,
        "result_status": result_status,
        "result_identity": result_identity,
        "accounted_work": accounted_work,
        "branch_certificate_identity": branch_certificate_identity,
        "branch_accounting_identity": branch_accounting_identity,
    }
    if _bare_digest(payload) != caller_binding_identity:
        raise ValueError("caller_binding_identity does not replay from the public rev400 payload")
    payload["caller_binding_identity"] = caller_binding_identity
    return payload


def _normalize_result_lift(lift: Any, replay_verified: bool) -> dict[str, Any]:
    if type(replay_verified) is not bool or replay_verified is not True:
        raise ValueError("result_lift must be independently replay-verified")
    if _strict_int(lift, "schema_version") != 1:
        raise ValueError("result_lift schema version mismatch")
    status = _field(lift, "status")
    if status not in {LIFT_NONEMPTY_STATUS, LIFT_EMPTY_STATUS}:
        raise ValueError("unsupported result_lift status")
    for field in ("certified", "exact", "complete"):
        _strict_true(lift, field)
    parent_degree = _strict_int(lift, "parent_action_degree")
    child_ground = _strict_int(lift, "child_ground_size")
    if parent_degree <= 0 or child_ground <= 0 or child_ground >= parent_degree:
        raise ValueError("result_lift measures must be positive and strictly shrinking")
    reduction_identity = _prefixed_sha(_field(lift, "reduction_identity"), "result_lift.reduction_identity")
    child_result_identity = _prefixed_sha(_field(lift, "child_result_identity"), "result_lift.child_result_identity")
    transcript_digest = _prefixed_sha(_field(lift, "transcript_digest"), "result_lift.transcript_digest")
    representative = _field(lift, "parent_representative")
    generators = _sequence(_field(lift, "parent_stabilizer_generators"), "parent_stabilizer_generators")
    if status == LIFT_EMPTY_STATUS:
        if representative is not None or len(generators) != 0:
            raise ValueError("exact-empty result_lift may not carry a representative or generators")
        outcome_kind = "exact_empty"
    else:
        if representative is None:
            raise ValueError("nonempty result_lift requires a parent representative")
        _permutation(representative, parent_degree, "parent_representative")
        normalized_generators = tuple(
            _permutation(generator, parent_degree, f"parent_stabilizer_generators[{i}]")
            for i, generator in enumerate(generators)
        )
        if normalized_generators != tuple(sorted(set(normalized_generators))):
            raise ValueError("parent_stabilizer_generators must be canonical and unique")
        outcome_kind = "nonempty"
    return {
        "outcome_kind": outcome_kind,
        "parent_action_degree": parent_degree,
        "child_ground_size": child_ground,
        "reduction_identity": reduction_identity,
        "child_result_identity": child_result_identity,
        "result_lift_digest": transcript_digest,
    }


def _normalize_accounting(accounting: Any, replay_verified: bool) -> dict[str, Any]:
    if type(replay_verified) is not bool or replay_verified is not True:
        raise ValueError("accounting_binding must be independently replay-verified")
    if _strict_int(accounting, "schema_version") != 1:
        raise ValueError("accounting_binding schema version mismatch")
    if _field(accounting, "status") != ACCOUNTING_STATUS:
        raise ValueError("accounting_binding status mismatch")
    for field in ("certified", "exact", "complete"):
        _strict_true(accounting, field)
    outcome_kind = _field(accounting, "outcome_kind")
    if outcome_kind not in {"nonempty", "exact_empty"}:
        raise ValueError("accounting_binding outcome_kind mismatch")
    parent_degree = _strict_int(accounting, "parent_action_degree")
    child_ground = _strict_int(accounting, "child_ground_size")
    if parent_degree <= 0 or child_ground <= 0 or child_ground >= parent_degree:
        raise ValueError("accounting_binding measures must be positive and strictly shrinking")
    reduction_identity = _prefixed_sha(_field(accounting, "reduction_identity"), "accounting.reduction_identity")
    handoff_digest = _prefixed_sha(_field(accounting, "handoff_digest"), "accounting.handoff_digest")
    child_result_identity = _prefixed_sha(_field(accounting, "child_result_identity"), "accounting.child_result_identity")
    result_lift_digest = _prefixed_sha(_field(accounting, "result_lift_digest"), "accounting.result_lift_digest")
    binding_digest = _prefixed_sha(_field(accounting, "binding_digest"), "accounting.binding_digest")
    charge = _field(accounting, "charged_log2_reduction_cost")
    if type(charge) not in (int, float) or not math.isfinite(float(charge)) or float(charge) < 0.0:
        raise ValueError("charged_log2_reduction_cost must be a finite nonnegative real")
    return {
        "outcome_kind": outcome_kind,
        "parent_action_degree": parent_degree,
        "child_ground_size": child_ground,
        "reduction_identity": reduction_identity,
        "handoff_digest": handoff_digest,
        "child_result_identity": child_result_identity,
        "result_lift_digest": result_lift_digest,
        "accounting_binding_digest": binding_digest,
    }


def certify_recursive_caller_provenance(
    caller_binding: Mapping[str, Any],
    result_lift: Any,
    accounting_binding: Any,
    *,
    result_lift_replay_verified: bool,
    accounting_binding_replay_verified: bool,
) -> RecursiveCallerProvenanceBinding:
    """Cross-bind public rev293/rev340 producer digests into a rev400 recursive caller binding.

    This is an exact *contract/provenance* binding only. It does not execute recursive
    String Isomorphism, authenticate repository reachability, re-run the Johnson
    reduction, or convert cost/accounting evidence into a semantic solution proof.
    Upstream result-lift and accounting certificates must have been replayed
    independently before this function is called.
    """
    try:
        caller = _normalize_caller_binding(caller_binding)
        lift = _normalize_result_lift(result_lift, result_lift_replay_verified)
        accounting = _normalize_accounting(accounting_binding, accounting_binding_replay_verified)
    except (TypeError, ValueError) as exc:
        return _fail(str(exc))

    if lift["outcome_kind"] != accounting["outcome_kind"]:
        return _fail("result_lift and accounting_binding disagree on exact outcome kind")
    if lift["parent_action_degree"] != accounting["parent_action_degree"]:
        return _fail("result_lift and accounting_binding disagree on parent action degree")
    if lift["child_ground_size"] != accounting["child_ground_size"]:
        return _fail("result_lift and accounting_binding disagree on child ground size")
    if lift["reduction_identity"] != accounting["reduction_identity"]:
        return _fail("result_lift and accounting_binding disagree on reduction identity")
    if lift["child_result_identity"] != accounting["child_result_identity"]:
        return _fail("result_lift and accounting_binding disagree on child result identity")
    if lift["result_lift_digest"] != accounting["result_lift_digest"]:
        return _fail("accounting_binding does not reference the supplied result_lift digest")

    expected_status = "exact_nonempty" if lift["outcome_kind"] == "nonempty" else "exact_empty"
    if caller["result_status"] != expected_status:
        return _fail("rev400 caller result_status disagrees with the replayed recursive result lift")

    result_digest_bare = _strip_sha256(lift["result_lift_digest"])
    accounting_digest_bare = _strip_sha256(accounting["accounting_binding_digest"])
    if caller["result_identity"] != result_digest_bare:
        return _fail("rev400 result identity is not the public rev293 result-lift transcript digest")
    if caller["branch_certificate_identity"] != result_digest_bare:
        return _fail("rev400 recursive branch certificate is not the public rev293 result-lift transcript digest")
    if caller["branch_accounting_identity"] != accounting_digest_bare:
        return _fail("rev400 recursive accounting identity is not the public rev340 accounting binding digest")

    payload = {
        "schema_version": 1,
        "status": OUTPUT_STATUS,
        "caller_binding_identity": caller["caller_binding_identity"],
        "result_status": caller["result_status"],
        "result_lift_digest": lift["result_lift_digest"],
        "accounting_binding_digest": accounting["accounting_binding_digest"],
        "reduction_identity": lift["reduction_identity"],
        "child_result_identity": lift["child_result_identity"],
        "parent_action_degree": lift["parent_action_degree"],
        "child_ground_size": lift["child_ground_size"],
    }
    provenance_identity = _prefixed_digest(payload)
    return RecursiveCallerProvenanceBinding(
        1,
        OUTPUT_STATUS,
        True,
        True,
        caller["caller_binding_identity"],
        caller["result_status"],
        lift["result_lift_digest"],
        accounting["accounting_binding_digest"],
        lift["reduction_identity"],
        lift["child_result_identity"],
        provenance_identity,
        "the rev400 recursive caller digest replays and its result/accounting identities are exactly the supplied replay-verified rev293/rev340 producer digests",
    )


def replay_recursive_caller_provenance(
    certificate: RecursiveCallerProvenanceBinding,
    caller_binding: Mapping[str, Any],
    result_lift: Any,
    accounting_binding: Any,
    *,
    result_lift_replay_verified: bool,
    accounting_binding_replay_verified: bool,
) -> bool:
    if not isinstance(certificate, RecursiveCallerProvenanceBinding):
        return False
    if not certificate.certified or certificate.schema_version != 1:
        return False
    replay = certify_recursive_caller_provenance(
        caller_binding,
        result_lift,
        accounting_binding,
        result_lift_replay_verified=result_lift_replay_verified,
        accounting_binding_replay_verified=accounting_binding_replay_verified,
    )
    return bool(replay.certified and replay == certificate and replay.provenance_identity == certificate.provenance_identity)


__all__ = [
    "RecursiveCallerProvenanceBinding",
    "certify_recursive_caller_provenance",
    "replay_recursive_caller_provenance",
]
