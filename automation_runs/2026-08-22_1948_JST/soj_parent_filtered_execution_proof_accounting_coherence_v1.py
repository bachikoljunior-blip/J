from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = 1
EXECUTION_STATUS = "certified_parent_filtered_child_execution_proof_dag_binding"
PROOF_ACCOUNTING_STATUS = "certified_parent_filtered_proof_accounting_coherence"
OUTPUT_STATUS = "certified_parent_filtered_execution_proof_accounting_coherence"
PARENT_NONEMPTY_STATUS = "exact_parent_filtered_ground_coset"
PARENT_EMPTY_STATUS = "exact_empty_parent_filtered_ground_coset"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ParentFilteredExecutionProofAccountingCoherence:
    schema_version: int
    status: str
    certified: bool
    exact: bool
    complete: bool
    parent_outcome_kind: str
    child_execution_outcome_kind: str
    source_status: str
    reduction_identity: str
    semantic_binding_identity: str
    child_instance_identity: str
    child_result_identity: str
    parent_result_identity: str
    execution_binding_identity: str
    execution_closure_identity: str
    execution_result_lift_digest: str
    execution_proof_identity_digest: str
    child_proof_identity_digest: str
    parent_result_proof_dag_identity: str
    accounting_coherence_identity: str
    handoff_digest: str
    parent_action_degree: int
    child_ground_size: int
    candidate_count: int
    accepted_count: int
    parent_filter_work_bound: int
    charged_log2_reduction_cost: float
    same_child_execution_certified: bool
    parent_result_identity_equivalence_certified: bool
    coherence_identity: str
    reason: str


def _fail(reason: str) -> ParentFilteredExecutionProofAccountingCoherence:
    return ParentFilteredExecutionProofAccountingCoherence(
        SCHEMA_VERSION,
        "parent_filtered_execution_proof_accounting_coherence_not_certified",
        False,
        False,
        False,
        "undetermined",
        "undetermined",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
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
        False,
        False,
        "",
        reason,
    )


def _literal_dict(value: Any, name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{name} must be a literal dict snapshot")
    if any(type(key) is not str for key in value):
        raise ValueError(f"{name} keys must be literal strings")
    return value


def _field(obj: dict[str, Any], name: str, prefix: str) -> Any:
    if name not in obj:
        raise ValueError(f"missing required field {prefix}.{name}")
    return obj[name]


def _strict_true(obj: dict[str, Any], name: str, prefix: str) -> None:
    value = _field(obj, name, prefix)
    if value is not True or type(value) is not bool:
        raise ValueError(f"{prefix}.{name} must be literal true")


def _strict_false(obj: dict[str, Any], name: str, prefix: str) -> None:
    value = _field(obj, name, prefix)
    if value is not False or type(value) is not bool:
        raise ValueError(f"{prefix}.{name} must be literal false")


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


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _normalize_execution(snapshot: Any, replay_verified: bool) -> dict[str, Any]:
    if replay_verified is not True or type(replay_verified) is not bool:
        raise ValueError("rev2500-style execution binding must be independently replay-verified")
    value = _literal_dict(snapshot, "execution_snapshot")
    if _field(value, "schema_version", "execution") != SCHEMA_VERSION:
        raise ValueError("execution.schema_version mismatch")
    if _strict_str(_field(value, "status", "execution"), "execution.status") != EXECUTION_STATUS:
        raise ValueError("execution.status mismatch")
    for name in ("certified", "exact", "complete", "same_child_execution_certified"):
        _strict_true(value, name, "execution")
    _strict_false(value, "parent_result_identity_equivalence_certified", "execution")

    parent_outcome = _strict_str(_field(value, "parent_outcome_kind", "execution"), "execution.parent_outcome_kind")
    child_outcome = _strict_str(_field(value, "proof_dag_outcome_kind", "execution"), "execution.proof_dag_outcome_kind")
    if parent_outcome not in {"exact_empty", "nonempty"}:
        raise ValueError("execution.parent_outcome_kind mismatch")
    if child_outcome not in {"exact_empty", "nonempty"}:
        raise ValueError("execution.proof_dag_outcome_kind mismatch")
    if child_outcome == "exact_empty" and parent_outcome != "exact_empty":
        raise ValueError("exact-empty child execution cannot bind to nonempty parent result")

    normalized = {
        "parent_outcome_kind": parent_outcome,
        "child_execution_outcome_kind": child_outcome,
        "reduction_identity": _digest(_field(value, "reduction_identity", "execution"), "execution.reduction_identity"),
        "child_result_identity": _digest(_field(value, "child_result_identity", "execution"), "execution.child_result_identity"),
        "parent_result_identity": _digest(_field(value, "parent_filtered_result_identity", "execution"), "execution.parent_filtered_result_identity"),
        "execution_closure_identity": _digest(_field(value, "execution_closure_identity", "execution"), "execution.execution_closure_identity"),
        "execution_result_lift_digest": _digest(_field(value, "execution_result_lift_digest", "execution"), "execution.execution_result_lift_digest"),
        "execution_proof_identity_digest": _digest(_field(value, "execution_proof_identity_digest", "execution"), "execution.execution_proof_identity_digest"),
        "child_proof_identity_digest": _digest(_field(value, "child_proof_identity_digest", "execution"), "execution.child_proof_identity_digest"),
        "child_ground_size": _strict_int(_field(value, "child_ground_size", "execution"), "execution.child_ground_size", minimum=1),
        "same_child_execution_certified": True,
        "parent_result_identity_equivalence_certified": False,
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": EXECUTION_STATUS,
        "parent_outcome_kind": normalized["parent_outcome_kind"],
        "proof_dag_outcome_kind": normalized["child_execution_outcome_kind"],
        "reduction_identity": normalized["reduction_identity"],
        "child_result_identity": normalized["child_result_identity"],
        "parent_filtered_result_identity": normalized["parent_result_identity"],
        "execution_closure_identity": normalized["execution_closure_identity"],
        "execution_result_lift_digest": normalized["execution_result_lift_digest"],
        "execution_proof_identity_digest": normalized["execution_proof_identity_digest"],
        "child_proof_identity_digest": normalized["child_proof_identity_digest"],
        "child_ground_size": normalized["child_ground_size"],
        "same_child_execution_certified": True,
        "parent_result_identity_equivalence_certified": False,
    }
    binding_identity = _digest(_field(value, "binding_identity", "execution"), "execution.binding_identity")
    if _canonical_digest(payload) != binding_identity:
        raise ValueError("execution.binding_identity replay failed")
    normalized["execution_binding_identity"] = binding_identity
    return normalized


def _normalize_proof_accounting(snapshot: Any, replay_verified: bool) -> dict[str, Any]:
    if replay_verified is not True or type(replay_verified) is not bool:
        raise ValueError("rev2800-style proof/accounting certificate must be independently replay-verified")
    value = _literal_dict(snapshot, "proof_accounting_snapshot")
    if _field(value, "schema_version", "proof_accounting") != SCHEMA_VERSION:
        raise ValueError("proof_accounting.schema_version mismatch")
    if _strict_str(_field(value, "status", "proof_accounting"), "proof_accounting.status") != PROOF_ACCOUNTING_STATUS:
        raise ValueError("proof_accounting.status mismatch")
    for name in ("certified", "exact", "complete"):
        _strict_true(value, name, "proof_accounting")

    outcome = _strict_str(_field(value, "outcome_kind", "proof_accounting"), "proof_accounting.outcome_kind")
    source_status = _strict_str(_field(value, "source_status", "proof_accounting"), "proof_accounting.source_status")
    expected_status = PARENT_EMPTY_STATUS if outcome == "exact_empty" else PARENT_NONEMPTY_STATUS if outcome == "nonempty" else None
    if expected_status is None or source_status != expected_status:
        raise ValueError("proof_accounting outcome/source_status mismatch")

    normalized = {
        "parent_outcome_kind": outcome,
        "source_status": source_status,
        "reduction_identity": _digest(_field(value, "reduction_identity", "proof_accounting"), "proof_accounting.reduction_identity"),
        "semantic_binding_identity": _digest(_field(value, "semantic_binding_identity", "proof_accounting"), "proof_accounting.semantic_binding_identity"),
        "child_instance_identity": _digest(_field(value, "child_instance_identity", "proof_accounting"), "proof_accounting.child_instance_identity"),
        "child_result_identity": _digest(_field(value, "child_result_identity", "proof_accounting"), "proof_accounting.child_result_identity"),
        "parent_result_identity": _digest(_field(value, "parent_result_identity", "proof_accounting"), "proof_accounting.parent_result_identity"),
        "parent_result_proof_dag_identity": _digest(_field(value, "proof_dag_identity", "proof_accounting"), "proof_accounting.proof_dag_identity"),
        "accounting_coherence_identity": _digest(_field(value, "accounting_coherence_identity", "proof_accounting"), "proof_accounting.accounting_coherence_identity"),
        "handoff_digest": _digest(_field(value, "handoff_digest", "proof_accounting"), "proof_accounting.handoff_digest"),
        "parent_action_degree": _strict_int(_field(value, "parent_action_degree", "proof_accounting"), "proof_accounting.parent_action_degree", minimum=1),
        "child_ground_size": _strict_int(_field(value, "child_ground_size", "proof_accounting"), "proof_accounting.child_ground_size", minimum=1),
        "candidate_count": _strict_int(_field(value, "candidate_count", "proof_accounting"), "proof_accounting.candidate_count"),
        "accepted_count": _strict_int(_field(value, "accepted_count", "proof_accounting"), "proof_accounting.accepted_count"),
        "parent_filter_work_bound": _strict_int(_field(value, "parent_filter_work_bound", "proof_accounting"), "proof_accounting.parent_filter_work_bound", minimum=1),
        "charged_log2_reduction_cost": _finite_nonnegative_real(_field(value, "charged_log2_reduction_cost", "proof_accounting"), "proof_accounting.charged_log2_reduction_cost"),
    }
    if normalized["child_ground_size"] >= normalized["parent_action_degree"]:
        raise ValueError("proof_accounting must retain strict parent-to-child shrink")
    if normalized["accepted_count"] > normalized["candidate_count"]:
        raise ValueError("proof_accounting accepted_count exceeds candidate_count")
    if outcome == "exact_empty" and normalized["accepted_count"] != 0:
        raise ValueError("exact-empty proof_accounting must have accepted_count == 0")
    if outcome == "nonempty" and normalized["accepted_count"] < 1:
        raise ValueError("nonempty proof_accounting must have accepted_count >= 1")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": PROOF_ACCOUNTING_STATUS,
        "outcome_kind": normalized["parent_outcome_kind"],
        "source_status": normalized["source_status"],
        "reduction_identity": normalized["reduction_identity"],
        "semantic_binding_identity": normalized["semantic_binding_identity"],
        "child_instance_identity": normalized["child_instance_identity"],
        "child_result_identity": normalized["child_result_identity"],
        "parent_result_identity": normalized["parent_result_identity"],
        "proof_dag_identity": normalized["parent_result_proof_dag_identity"],
        "accounting_coherence_identity": normalized["accounting_coherence_identity"],
        "handoff_digest": normalized["handoff_digest"],
        "parent_action_degree": normalized["parent_action_degree"],
        "child_ground_size": normalized["child_ground_size"],
        "candidate_count": normalized["candidate_count"],
        "accepted_count": normalized["accepted_count"],
        "parent_filter_work_bound": normalized["parent_filter_work_bound"],
        "charged_log2_reduction_cost": normalized["charged_log2_reduction_cost"],
    }
    coherence_identity = _digest(_field(value, "coherence_identity", "proof_accounting"), "proof_accounting.coherence_identity")
    if _canonical_digest(payload) != coherence_identity:
        raise ValueError("proof_accounting.coherence_identity replay failed")
    normalized["proof_accounting_coherence_identity"] = coherence_identity
    return normalized


def certify_parent_filtered_execution_proof_accounting_coherence(
    execution_snapshot: Any,
    proof_accounting_snapshot: Any,
    *,
    execution_replay_verified: bool,
    proof_accounting_replay_verified: bool,
) -> ParentFilteredExecutionProofAccountingCoherence:
    """Bind replayed child-execution lineage to replayed exact parent proof/accounting coherence."""
    try:
        execution = _normalize_execution(execution_snapshot, execution_replay_verified)
        proof_accounting = _normalize_proof_accounting(
            proof_accounting_snapshot,
            proof_accounting_replay_verified,
        )
        for name in (
            "parent_outcome_kind",
            "reduction_identity",
            "child_result_identity",
            "parent_result_identity",
            "child_ground_size",
        ):
            if execution[name] != proof_accounting[name] or type(execution[name]) is not type(proof_accounting[name]):
                raise ValueError(f"execution/proof_accounting {name} mismatch")

        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": OUTPUT_STATUS,
            "parent_outcome_kind": proof_accounting["parent_outcome_kind"],
            "child_execution_outcome_kind": execution["child_execution_outcome_kind"],
            "source_status": proof_accounting["source_status"],
            "reduction_identity": proof_accounting["reduction_identity"],
            "semantic_binding_identity": proof_accounting["semantic_binding_identity"],
            "child_instance_identity": proof_accounting["child_instance_identity"],
            "child_result_identity": proof_accounting["child_result_identity"],
            "parent_result_identity": proof_accounting["parent_result_identity"],
            "execution_binding_identity": execution["execution_binding_identity"],
            "execution_closure_identity": execution["execution_closure_identity"],
            "execution_result_lift_digest": execution["execution_result_lift_digest"],
            "execution_proof_identity_digest": execution["execution_proof_identity_digest"],
            "child_proof_identity_digest": execution["child_proof_identity_digest"],
            "parent_result_proof_dag_identity": proof_accounting["parent_result_proof_dag_identity"],
            "accounting_coherence_identity": proof_accounting["accounting_coherence_identity"],
            "handoff_digest": proof_accounting["handoff_digest"],
            "parent_action_degree": proof_accounting["parent_action_degree"],
            "child_ground_size": proof_accounting["child_ground_size"],
            "candidate_count": proof_accounting["candidate_count"],
            "accepted_count": proof_accounting["accepted_count"],
            "parent_filter_work_bound": proof_accounting["parent_filter_work_bound"],
            "charged_log2_reduction_cost": proof_accounting["charged_log2_reduction_cost"],
            "same_child_execution_certified": True,
            "parent_result_identity_equivalence_certified": False,
        }
        identity = _canonical_digest(payload)
        return ParentFilteredExecutionProofAccountingCoherence(
            SCHEMA_VERSION,
            OUTPUT_STATUS,
            True,
            True,
            True,
            payload["parent_outcome_kind"],
            payload["child_execution_outcome_kind"],
            payload["source_status"],
            payload["reduction_identity"],
            payload["semantic_binding_identity"],
            payload["child_instance_identity"],
            payload["child_result_identity"],
            payload["parent_result_identity"],
            payload["execution_binding_identity"],
            payload["execution_closure_identity"],
            payload["execution_result_lift_digest"],
            payload["execution_proof_identity_digest"],
            payload["child_proof_identity_digest"],
            payload["parent_result_proof_dag_identity"],
            payload["accounting_coherence_identity"],
            payload["handoff_digest"],
            payload["parent_action_degree"],
            payload["child_ground_size"],
            payload["candidate_count"],
            payload["accepted_count"],
            payload["parent_filter_work_bound"],
            payload["charged_log2_reduction_cost"],
            True,
            False,
            identity,
            (
                "replayed rev2500 child-execution lineage and replayed rev2800 exact parent proof/accounting "
                "coherence bind to one parent-filtered result/reduction/child-result identity; the child execution "
                "outcome remains distinct from the post-filter parent outcome and unlike accounting units remain separate"
            ),
        )
    except (TypeError, ValueError, OverflowError, KeyError) as exc:
        return _fail(str(exc))


def replay_parent_filtered_execution_proof_accounting_coherence(
    certificate: ParentFilteredExecutionProofAccountingCoherence,
    execution_snapshot: Any,
    proof_accounting_snapshot: Any,
    *,
    execution_replay_verified: bool,
    proof_accounting_replay_verified: bool,
) -> bool:
    if type(certificate) is not ParentFilteredExecutionProofAccountingCoherence:
        return False
    replay = certify_parent_filtered_execution_proof_accounting_coherence(
        execution_snapshot,
        proof_accounting_snapshot,
        execution_replay_verified=execution_replay_verified,
        proof_accounting_replay_verified=proof_accounting_replay_verified,
    )
    return bool(replay.certified and replay == certificate)


__all__ = [
    "EXECUTION_STATUS",
    "OUTPUT_STATUS",
    "PARENT_EMPTY_STATUS",
    "PARENT_NONEMPTY_STATUS",
    "PROOF_ACCOUNTING_STATUS",
    "ParentFilteredExecutionProofAccountingCoherence",
    "certify_parent_filtered_execution_proof_accounting_coherence",
    "replay_parent_filtered_execution_proof_accounting_coherence",
]
