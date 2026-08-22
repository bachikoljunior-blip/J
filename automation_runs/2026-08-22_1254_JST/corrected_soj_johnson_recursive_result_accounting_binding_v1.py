from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Sequence


SCHEMA_VERSION = 1
HANDOFF_STATUS = "certified_corrected_soj_larger_ground_recursive_handoff"
LIFT_NONEMPTY_STATUS = "certified_exact_parent_johnson_coset_lift"
LIFT_EMPTY_STATUS = "certified_exact_empty_parent_johnson_result"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class JohnsonRecursiveResultAccountingBinding:
    schema_version: int
    status: str
    certified: bool
    exact: bool
    complete: bool
    outcome_kind: str
    parent_action_degree: int
    child_ground_size: int
    reduction_identity: str
    handoff_digest: str
    child_result_identity: str
    result_lift_digest: str
    charged_log2_reduction_cost: float
    binding_digest: str
    reason: str


def _fail(
    reason: str,
    *,
    parent_action_degree: int = 0,
    child_ground_size: int = 0,
    reduction_identity: str = "",
    handoff_digest: str = "",
    child_result_identity: str = "",
    result_lift_digest: str = "",
    charged_log2_reduction_cost: float = 0.0,
) -> JohnsonRecursiveResultAccountingBinding:
    return JohnsonRecursiveResultAccountingBinding(
        SCHEMA_VERSION,
        "johnson_recursive_result_accounting_binding_not_certified",
        False,
        False,
        False,
        "undetermined",
        parent_action_degree,
        child_ground_size,
        reduction_identity,
        handoff_digest,
        child_result_identity,
        result_lift_digest,
        charged_log2_reduction_cost,
        "",
        reason,
    )


def _field(obj: Any, name: str) -> Any:
    if not hasattr(obj, name):
        raise ValueError(f"missing required field {name!r}")
    return getattr(obj, name)


def _strict_bool(obj: Any, name: str) -> bool:
    value = _field(obj, name)
    if type(value) is not bool:
        raise ValueError(f"{name} must be a strict boolean")
    return value


def _strict_int(obj: Any, name: str) -> int:
    value = _field(obj, name)
    if type(value) is not int:
        raise ValueError(f"{name} must be a strict integer")
    return value


def _sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase sha256:<64 hex> digest")
    return value


def _real(value: Any, name: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be a finite real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite real number")
    return result


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a finite sequence")
    return value


def _normalize_permutation(raw: Any, *, degree: int, name: str) -> tuple[int, ...]:
    seq = _sequence(raw, name)
    if len(seq) != degree:
        raise ValueError(f"{name} has the wrong action degree")
    values: list[int] = []
    for index, value in enumerate(seq):
        if type(value) is not int:
            raise ValueError(f"{name}[{index}] must be a strict integer")
        values.append(value)
    perm = tuple(values)
    if any(value < 0 or value >= degree for value in perm) or len(set(perm)) != degree:
        raise ValueError(f"{name} is not a permutation of 0..{degree - 1}")
    return perm


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _normalize_handoff(handoff: Any, *, replay_verified: bool) -> dict[str, Any]:
    if type(replay_verified) is not bool or not replay_verified:
        raise ValueError("rev291-style recursive handoff must be replay-verified independently")
    if str(_field(handoff, "status")) != HANDOFF_STATUS:
        raise ValueError("unexpected recursive handoff status")
    if not _strict_bool(handoff, "certified"):
        raise ValueError("recursive handoff is not certified")

    handoff_digest = _sha256(_field(handoff, "handoff_digest"), "handoff_digest")
    charge = _real(_field(handoff, "charged_log2_reduction_cost"), "charged_log2_reduction_cost")
    if charge < 0.0:
        raise ValueError("charged_log2_reduction_cost must be nonnegative")

    reduction = _field(handoff, "reduction")
    if reduction is None:
        raise ValueError("certified recursive handoff must retain its reduction snapshot")
    for name in (
        "canonical",
        "exact",
        "progress_certified",
        "solution_transport_certified",
        "ambient_membership_transport_certified",
        "complement_ambiguity_handled",
    ):
        if not _strict_bool(reduction, name):
            raise ValueError(f"handoff reduction field {name} must be true")
    parent_degree = _strict_int(reduction, "source_action_degree")
    child_ground_size = _strict_int(reduction, "child_ground_size")
    ground_size = _strict_int(reduction, "johnson_ground_size")
    if parent_degree <= 0 or child_ground_size <= 0:
        raise ValueError("handoff reduction measures must be positive")
    if child_ground_size != ground_size:
        raise ValueError("handoff child measure differs from the certified Johnson ground")
    if child_ground_size >= parent_degree:
        raise ValueError("handoff child measure does not strictly shrink the parent action degree")
    reduction_identity = _sha256(_field(reduction, "reduction_identity"), "reduction_identity")

    accounting_root = _field(handoff, "accounting_root")
    validation = _field(handoff, "validation")
    if accounting_root is None or validation is None:
        raise ValueError("certified recursive handoff must retain accounting root and validation")
    if str(_field(accounting_root, "operation_kind")) != "aux_shrink":
        raise ValueError("recursive handoff accounting root must be an aux_shrink node")
    if not _strict_bool(accounting_root, "canonical"):
        raise ValueError("recursive handoff accounting root is not canonical")
    if not _strict_bool(accounting_root, "cost_certified"):
        raise ValueError("recursive handoff accounting root is not cost-certified")
    root_m = _strict_int(accounting_root, "m")
    if root_m != parent_degree:
        raise ValueError("recursive handoff accounting root measure differs from the represented parent degree")
    if not _strict_bool(validation, "certified"):
        raise ValueError("main recurrence validation was not certified")

    children = _sequence(_field(accounting_root, "children"), "accounting_root.children")
    if len(children) != 1:
        raise ValueError("recursive handoff accounting root must have exactly one recursive child")
    child_edge = children[0]
    multiplicity = _strict_int(child_edge, "multiplicity")
    if multiplicity != 1:
        raise ValueError("recursive handoff must bind exactly one recursive child")
    child_node = _field(child_edge, "child")
    if child_node is None:
        raise ValueError("recursive handoff accounting child is missing")
    child_m = _strict_int(child_node, "m")
    if child_m != child_ground_size:
        raise ValueError("recurrence child measure differs from the certified Johnson ground")

    return {
        "parent_action_degree": parent_degree,
        "child_ground_size": child_ground_size,
        "reduction_identity": reduction_identity,
        "handoff_digest": handoff_digest,
        "charged_log2_reduction_cost": charge,
    }


def _normalize_lift(lift: Any, *, replay_verified: bool) -> dict[str, Any]:
    if type(replay_verified) is not bool or not replay_verified:
        raise ValueError("rev293-style recursive result lift must be replay-verified independently")
    status = str(_field(lift, "status"))
    if status not in {LIFT_NONEMPTY_STATUS, LIFT_EMPTY_STATUS}:
        raise ValueError("unexpected recursive result-lift status")
    for name in ("certified", "exact", "complete"):
        if not _strict_bool(lift, name):
            raise ValueError(f"result-lift field {name} must be true")

    parent_degree = _strict_int(lift, "parent_action_degree")
    child_ground_size = _strict_int(lift, "child_ground_size")
    if parent_degree <= 0 or child_ground_size <= 0:
        raise ValueError("result-lift measures must be positive")
    reduction_identity = _sha256(_field(lift, "reduction_identity"), "lift.reduction_identity")
    child_result_identity = _sha256(_field(lift, "child_result_identity"), "child_result_identity")
    result_lift_digest = _sha256(_field(lift, "transcript_digest"), "result_lift.transcript_digest")

    representative = _field(lift, "parent_representative")
    generators = _sequence(_field(lift, "parent_stabilizer_generators"), "parent_stabilizer_generators")
    if status == LIFT_EMPTY_STATUS:
        if representative is not None or len(generators) != 0:
            raise ValueError("exact-empty result lift may not carry a representative or stabilizer generators")
        outcome_kind = "exact_empty"
    else:
        if representative is None:
            raise ValueError("nonempty result lift requires a parent representative")
        _normalize_permutation(representative, degree=parent_degree, name="parent_representative")
        normalized_generators = tuple(
            _normalize_permutation(raw, degree=parent_degree, name=f"parent_stabilizer_generators[{index}]")
            for index, raw in enumerate(generators)
        )
        if normalized_generators != tuple(sorted(set(normalized_generators))):
            raise ValueError("parent stabilizer generators must be unique and lexicographically canonical")
        outcome_kind = "nonempty"

    return {
        "outcome_kind": outcome_kind,
        "parent_action_degree": parent_degree,
        "child_ground_size": child_ground_size,
        "reduction_identity": reduction_identity,
        "child_result_identity": child_result_identity,
        "result_lift_digest": result_lift_digest,
    }


def certify_johnson_recursive_result_accounting_binding(
    handoff: Any,
    result_lift: Any,
    *,
    handoff_replay_verified: bool,
    result_lift_replay_verified: bool,
) -> JohnsonRecursiveResultAccountingBinding:
    """Bind one exact post-recursion Johnson result to its admitted recursion edge.

    The routine intentionally performs no recursion and no reduction construction.
    Both sibling certificates must already have been replayed by their owning
    implementations. This post-replay boundary checks that the recursive accounting
    edge and the exact lifted result refer to the same reduction identity, the same
    represented parent action degree, and the same Johnson ground child measure.

    Exact-empty and nonempty parent outcomes remain distinct. A nonempty result must
    still carry a syntactically valid parent permutation/canonical generator tuple;
    semantic transport is an upstream rev293 proof obligation guarded here by the
    explicit independent replay bit.
    """
    try:
        handoff_snapshot = _normalize_handoff(handoff, replay_verified=handoff_replay_verified)
        lift_snapshot = _normalize_lift(result_lift, replay_verified=result_lift_replay_verified)
    except (TypeError, ValueError) as exc:
        return _fail(str(exc))

    parent_degree = handoff_snapshot["parent_action_degree"]
    child_ground_size = handoff_snapshot["child_ground_size"]
    reduction_identity = handoff_snapshot["reduction_identity"]
    handoff_digest = handoff_snapshot["handoff_digest"]
    child_result_identity = lift_snapshot["child_result_identity"]
    result_lift_digest = lift_snapshot["result_lift_digest"]
    charge = handoff_snapshot["charged_log2_reduction_cost"]

    if lift_snapshot["reduction_identity"] != reduction_identity:
        return _fail(
            "recursive handoff and lifted result carry different reduction identities",
            parent_action_degree=parent_degree,
            child_ground_size=child_ground_size,
            reduction_identity=reduction_identity,
            handoff_digest=handoff_digest,
            child_result_identity=child_result_identity,
            result_lift_digest=result_lift_digest,
            charged_log2_reduction_cost=charge,
        )
    if lift_snapshot["parent_action_degree"] != parent_degree:
        return _fail(
            "lifted exact result belongs to a different represented parent action degree",
            parent_action_degree=parent_degree,
            child_ground_size=child_ground_size,
            reduction_identity=reduction_identity,
            handoff_digest=handoff_digest,
            child_result_identity=child_result_identity,
            result_lift_digest=result_lift_digest,
            charged_log2_reduction_cost=charge,
        )
    if lift_snapshot["child_ground_size"] != child_ground_size:
        return _fail(
            "lifted exact result belongs to a different Johnson recursive child measure",
            parent_action_degree=parent_degree,
            child_ground_size=child_ground_size,
            reduction_identity=reduction_identity,
            handoff_digest=handoff_digest,
            child_result_identity=child_result_identity,
            result_lift_digest=result_lift_digest,
            charged_log2_reduction_cost=charge,
        )

    outcome_kind = lift_snapshot["outcome_kind"]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "certified_johnson_recursive_result_accounting_binding",
        "outcome_kind": outcome_kind,
        "parent_action_degree": parent_degree,
        "child_ground_size": child_ground_size,
        "reduction_identity": reduction_identity,
        "handoff_digest": handoff_digest,
        "child_result_identity": child_result_identity,
        "result_lift_digest": result_lift_digest,
        "charged_log2_reduction_cost": charge,
    }
    binding_digest = _canonical_digest(payload)
    return JohnsonRecursiveResultAccountingBinding(
        SCHEMA_VERSION,
        "certified_johnson_recursive_result_accounting_binding",
        True,
        True,
        True,
        outcome_kind,
        parent_degree,
        child_ground_size,
        reduction_identity,
        handoff_digest,
        child_result_identity,
        result_lift_digest,
        charge,
        binding_digest,
        "one independently replayed exact Johnson parent result is bound to the same independently replayed recursion/accounting edge without weakening either upstream certificate",
    )


def replay_johnson_recursive_result_accounting_binding(
    certificate: JohnsonRecursiveResultAccountingBinding,
    handoff: Any,
    result_lift: Any,
    *,
    handoff_replay_verified: bool,
    result_lift_replay_verified: bool,
) -> bool:
    if not isinstance(certificate, JohnsonRecursiveResultAccountingBinding):
        return False
    if not certificate.certified or certificate.schema_version != SCHEMA_VERSION:
        return False
    replay = certify_johnson_recursive_result_accounting_binding(
        handoff,
        result_lift,
        handoff_replay_verified=handoff_replay_verified,
        result_lift_replay_verified=result_lift_replay_verified,
    )
    return bool(replay.certified and replay == certificate and replay.binding_digest == certificate.binding_digest)


__all__ = [
    "HANDOFF_STATUS",
    "LIFT_NONEMPTY_STATUS",
    "LIFT_EMPTY_STATUS",
    "JohnsonRecursiveResultAccountingBinding",
    "certify_johnson_recursive_result_accounting_binding",
    "replay_johnson_recursive_result_accounting_binding",
]
