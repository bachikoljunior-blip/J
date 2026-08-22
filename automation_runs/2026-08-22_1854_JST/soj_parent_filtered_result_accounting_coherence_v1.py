from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Sequence

SCHEMA_VERSION = 1
PARENT_NONEMPTY_STATUS = "exact_parent_filtered_ground_coset"
PARENT_EMPTY_STATUS = "exact_empty_parent_filtered_ground_coset"
HANDOFF_STATUS = "certified_corrected_soj_larger_ground_recursive_handoff"
OUTPUT_STATUS = "certified_parent_filtered_result_accounting_coherence"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ParentFilteredResultAccountingCoherence:
    schema_version: int
    status: str
    certified: bool
    exact: bool
    complete: bool
    outcome_kind: str
    reduction_identity: str
    semantic_binding_identity: str
    child_instance_identity: str
    child_result_identity: str
    parent_result_identity: str
    handoff_digest: str
    parent_action_degree: int
    child_ground_size: int
    candidate_count: int
    accepted_count: int
    parent_filter_work_bound: int
    charged_log2_reduction_cost: float
    coherence_identity: str
    reason: str


def _fail(reason: str) -> ParentFilteredResultAccountingCoherence:
    return ParentFilteredResultAccountingCoherence(
        SCHEMA_VERSION,
        "parent_filtered_result_accounting_coherence_not_certified",
        False,
        False,
        False,
        "undetermined",
        "",
        "",
        "",
        "",
        "",
        "",
        0,
        0,
        0,
        0,
        0,
        0.0,
        "",
        reason,
    )


def _field(obj: Any, name: str) -> Any:
    if type(obj) is dict:
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


def _strict_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be a strict integer >= {minimum}")
    return value


def _strict_str(value: Any, name: str) -> str:
    if type(value) is not str:
        raise ValueError(f"{name} must be a literal string")
    return value


def _digest(value: Any, name: str) -> str:
    value = _strict_str(value, name)
    if _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase sha256:<64 hex>")
    return value


def _finite_nonnegative_real(value: Any, name: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be a finite nonnegative real")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be a finite nonnegative real")
    return result


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a finite sequence")
    return value


def _permutation(raw: Any, degree: int, name: str) -> tuple[int, ...]:
    seq = _sequence(raw, name)
    if len(seq) != degree:
        raise ValueError(f"{name} has wrong action degree")
    out = tuple(_strict_int(value, f"{name}[{i}]", minimum=0) for i, value in enumerate(seq))
    if any(value >= degree for value in out) or len(set(out)) != degree:
        raise ValueError(f"{name} is not a permutation of 0..{degree - 1}")
    return out


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _normalize_parent_result(parent_result: Any, replay_verified: bool) -> dict[str, Any]:
    if type(replay_verified) is not bool or replay_verified is not True:
        raise ValueError("rev2200-style parent-filtered result must be replay-verified independently")
    if _field(parent_result, "schema_version") != SCHEMA_VERSION:
        raise ValueError("parent-filtered result schema mismatch")
    status = _strict_str(_field(parent_result, "status"), "parent_result.status")
    if status not in {PARENT_NONEMPTY_STATUS, PARENT_EMPTY_STATUS}:
        raise ValueError("unexpected parent-filtered result status")
    for name in ("certified", "exact", "complete"):
        _strict_true(parent_result, name)

    reduction_identity = _digest(_field(parent_result, "reduction_identity"), "reduction_identity")
    semantic_binding_identity = _digest(
        _field(parent_result, "semantic_binding_identity"), "semantic_binding_identity"
    )
    child_instance_identity = _digest(_field(parent_result, "child_instance_identity"), "child_instance_identity")
    child_result_identity = _digest(_field(parent_result, "child_result_identity"), "child_result_identity")
    parent_result_identity = _digest(_field(parent_result, "result_identity"), "result_identity")
    action_degree = _strict_int(_field(parent_result, "action_degree"), "action_degree", minimum=1)
    candidate_count = _strict_int(_field(parent_result, "candidate_count"), "candidate_count", minimum=0)
    accepted_count = _strict_int(_field(parent_result, "accepted_count"), "accepted_count", minimum=0)
    work_bound = _strict_int(_field(parent_result, "work_bound"), "work_bound", minimum=1)
    if accepted_count > candidate_count:
        raise ValueError("accepted_count cannot exceed candidate_count")

    representative = _field(parent_result, "representative")
    stabilizer = _sequence(_field(parent_result, "parent_stabilizer_elements"), "parent_stabilizer_elements")
    if status == PARENT_EMPTY_STATUS:
        if accepted_count != 0 or representative is not None or len(stabilizer) != 0:
            raise ValueError("exact-empty parent result may not carry accepted elements, representative, or stabilizer")
        outcome_kind = "exact_empty"
    else:
        if accepted_count <= 0 or representative is None:
            raise ValueError("nonempty parent result requires accepted candidates and a representative")
        _permutation(representative, action_degree, "representative")
        normalized_stabilizer = tuple(
            _permutation(raw, action_degree, f"parent_stabilizer_elements[{i}]")
            for i, raw in enumerate(stabilizer)
        )
        if normalized_stabilizer != tuple(sorted(set(normalized_stabilizer))):
            raise ValueError("parent stabilizer elements must be unique and lexicographically canonical")
        outcome_kind = "nonempty"

    return {
        "outcome_kind": outcome_kind,
        "status": status,
        "reduction_identity": reduction_identity,
        "semantic_binding_identity": semantic_binding_identity,
        "child_instance_identity": child_instance_identity,
        "child_result_identity": child_result_identity,
        "parent_result_identity": parent_result_identity,
        "child_ground_size": action_degree,
        "candidate_count": candidate_count,
        "accepted_count": accepted_count,
        "parent_filter_work_bound": work_bound,
    }


def _normalize_handoff(handoff: Any, replay_verified: bool) -> dict[str, Any]:
    if type(replay_verified) is not bool or replay_verified is not True:
        raise ValueError("rev291-style recursive handoff must be replay-verified independently")
    if _strict_str(_field(handoff, "status"), "handoff.status") != HANDOFF_STATUS:
        raise ValueError("unexpected recursive handoff status")
    _strict_true(handoff, "certified")
    handoff_digest = _digest(_field(handoff, "handoff_digest"), "handoff_digest")
    charged_log2_reduction_cost = _finite_nonnegative_real(
        _field(handoff, "charged_log2_reduction_cost"), "charged_log2_reduction_cost"
    )

    reduction = _field(handoff, "reduction")
    if reduction is None:
        raise ValueError("recursive handoff must retain the certified reduction snapshot")
    for name in (
        "canonical",
        "exact",
        "progress_certified",
        "solution_transport_certified",
        "ambient_membership_transport_certified",
        "complement_ambiguity_handled",
    ):
        _strict_true(reduction, name)
    parent_action_degree = _strict_int(
        _field(reduction, "source_action_degree"), "reduction.source_action_degree", minimum=1
    )
    child_ground_size = _strict_int(_field(reduction, "child_ground_size"), "reduction.child_ground_size", minimum=1)
    johnson_ground_size = _strict_int(
        _field(reduction, "johnson_ground_size"), "reduction.johnson_ground_size", minimum=1
    )
    if child_ground_size != johnson_ground_size or child_ground_size >= parent_action_degree:
        raise ValueError("recursive handoff does not certify strict Johnson-ground shrink")
    reduction_identity = _digest(_field(reduction, "reduction_identity"), "handoff.reduction_identity")

    accounting_root = _field(handoff, "accounting_root")
    validation = _field(handoff, "validation")
    if accounting_root is None or validation is None:
        raise ValueError("recursive handoff must retain recurrence accounting evidence")
    if _strict_str(_field(accounting_root, "operation_kind"), "accounting_root.operation_kind") != "aux_shrink":
        raise ValueError("recursive handoff accounting root must be aux_shrink")
    for name in ("canonical", "cost_certified"):
        _strict_true(accounting_root, name)
    if _strict_int(_field(accounting_root, "m"), "accounting_root.m", minimum=1) != parent_action_degree:
        raise ValueError("accounting root does not represent the parent action degree")
    _strict_true(validation, "certified")
    children = _sequence(_field(accounting_root, "children"), "accounting_root.children")
    if len(children) != 1:
        raise ValueError("recursive handoff must have exactly one recurrence child")
    edge = children[0]
    if _strict_int(_field(edge, "multiplicity"), "child multiplicity", minimum=1) != 1:
        raise ValueError("recursive handoff must charge exactly one recursive child")
    child_node = _field(edge, "node")
    if child_node is None:
        raise ValueError("recursive handoff child node missing")
    if _strict_int(_field(child_node, "m"), "child_node.m", minimum=1) != child_ground_size:
        raise ValueError("recurrence child measure differs from Johnson ground size")

    return {
        "reduction_identity": reduction_identity,
        "handoff_digest": handoff_digest,
        "parent_action_degree": parent_action_degree,
        "child_ground_size": child_ground_size,
        "charged_log2_reduction_cost": charged_log2_reduction_cost,
    }


def certify_parent_filtered_result_accounting_coherence(
    parent_result: Any,
    recursive_handoff: Any,
    *,
    parent_result_replay_verified: bool,
    recursive_handoff_replay_verified: bool,
) -> ParentFilteredResultAccountingCoherence:
    """Bind a replayed exact rev2200-style filtered result to one replayed recurrence handoff.

    The certificate deliberately keeps two accounting units separate: the handoff's
    logarithmic reduction charge and rev2200's conservative integer filtering work
    bound. It proves compatibility and exposes both charges; it does not invent a
    conversion between them or mutate the shared recurrence/proof-DAG substrate.
    """
    try:
        result = _normalize_parent_result(parent_result, parent_result_replay_verified)
        handoff = _normalize_handoff(recursive_handoff, recursive_handoff_replay_verified)
    except (TypeError, ValueError, OverflowError) as exc:
        return _fail(str(exc))

    if result["reduction_identity"] != handoff["reduction_identity"]:
        return _fail("parent-filtered result and recursive handoff use different reduction identities")
    if result["child_ground_size"] != handoff["child_ground_size"]:
        return _fail("parent-filtered result action degree differs from the recurrence child measure")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": OUTPUT_STATUS,
        "outcome_kind": result["outcome_kind"],
        "reduction_identity": result["reduction_identity"],
        "semantic_binding_identity": result["semantic_binding_identity"],
        "child_instance_identity": result["child_instance_identity"],
        "child_result_identity": result["child_result_identity"],
        "parent_result_identity": result["parent_result_identity"],
        "handoff_digest": handoff["handoff_digest"],
        "parent_action_degree": handoff["parent_action_degree"],
        "child_ground_size": handoff["child_ground_size"],
        "candidate_count": result["candidate_count"],
        "accepted_count": result["accepted_count"],
        "parent_filter_work_bound": result["parent_filter_work_bound"],
        "charged_log2_reduction_cost": handoff["charged_log2_reduction_cost"],
    }
    coherence_identity = _canonical_digest(payload)
    return ParentFilteredResultAccountingCoherence(
        SCHEMA_VERSION,
        OUTPUT_STATUS,
        True,
        True,
        True,
        result["outcome_kind"],
        result["reduction_identity"],
        result["semantic_binding_identity"],
        result["child_instance_identity"],
        result["child_result_identity"],
        result["parent_result_identity"],
        handoff["handoff_digest"],
        handoff["parent_action_degree"],
        handoff["child_ground_size"],
        result["candidate_count"],
        result["accepted_count"],
        result["parent_filter_work_bound"],
        handoff["charged_log2_reduction_cost"],
        coherence_identity,
        "the exact parent-filtered recursive result and the admitted recurrence handoff replay to one reduction/child-measure identity; filtering work remains separately exposed",
    )


def replay_parent_filtered_result_accounting_coherence(
    certificate: ParentFilteredResultAccountingCoherence,
    parent_result: Any,
    recursive_handoff: Any,
    *,
    parent_result_replay_verified: bool,
    recursive_handoff_replay_verified: bool,
) -> bool:
    if type(certificate) is not ParentFilteredResultAccountingCoherence:
        return False
    replay = certify_parent_filtered_result_accounting_coherence(
        parent_result,
        recursive_handoff,
        parent_result_replay_verified=parent_result_replay_verified,
        recursive_handoff_replay_verified=recursive_handoff_replay_verified,
    )
    return bool(
        replay.certified
        and replay == certificate
        and replay.coherence_identity == certificate.coherence_identity
    )


__all__ = [
    "HANDOFF_STATUS",
    "OUTPUT_STATUS",
    "PARENT_EMPTY_STATUS",
    "PARENT_NONEMPTY_STATUS",
    "ParentFilteredResultAccountingCoherence",
    "certify_parent_filtered_result_accounting_coherence",
    "replay_parent_filtered_result_accounting_coherence",
]
