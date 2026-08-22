from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = 1
PROOF_STATUS = "certified_parent_filtered_result_proof_dag_integrity"
ACCOUNTING_STATUS = "certified_parent_filtered_result_accounting_coherence"
OUTPUT_STATUS = "certified_parent_filtered_proof_accounting_coherence"
PARENT_NONEMPTY_STATUS = "exact_parent_filtered_ground_coset"
PARENT_EMPTY_STATUS = "exact_empty_parent_filtered_ground_coset"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ParentFilteredProofAccountingCoherence:
    schema_version: int
    status: str
    certified: bool
    exact: bool
    complete: bool
    outcome_kind: str
    source_status: str
    reduction_identity: str
    semantic_binding_identity: str
    child_instance_identity: str
    child_result_identity: str
    parent_result_identity: str
    proof_dag_identity: str
    accounting_coherence_identity: str
    handoff_digest: str
    parent_action_degree: int
    child_ground_size: int
    candidate_count: int
    accepted_count: int
    parent_filter_work_bound: int
    charged_log2_reduction_cost: float
    coherence_identity: str
    reason: str


def _fail(reason: str) -> ParentFilteredProofAccountingCoherence:
    return ParentFilteredProofAccountingCoherence(
        SCHEMA_VERSION, "parent_filtered_proof_accounting_coherence_not_certified",
        False, False, False, "undetermined", "", "", "", "", "", "", "", "", "",
        0, 0, 0, 0, 0, 0.0, "", reason,
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


def _strict_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be a strict integer >= {minimum}")
    return value


def _strict_schema_version(value: Any, name: str) -> int:
    version = _strict_int(value, name, minimum=1)
    if version != SCHEMA_VERSION:
        raise ValueError(f"{name} mismatch")
    return version


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
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _literal_json(value: Any, name: str) -> Any:
    if value is None or type(value) in (bool, int, float, str):
        if type(value) is float and not math.isfinite(value):
            raise ValueError(f"{name} contains a non-finite float")
        return value
    if type(value) is list:
        return [_literal_json(item, f"{name}[{index}]") for index, item in enumerate(value)]
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise ValueError(f"{name} has a nonliteral string key")
        return {key: _literal_json(item, f"{name}.{key}") for key, item in value.items()}
    raise ValueError(f"{name} must contain only literal JSON values")


def _strict_permutation(value: Any, *, degree: int, name: str) -> tuple[int, ...]:
    if type(value) is not list or len(value) != degree:
        raise ValueError(f"{name} must be a literal permutation list of degree {degree}")
    permutation = tuple(_strict_int(item, f"{name}[{index}]") for index, item in enumerate(value))
    if set(permutation) != set(range(degree)):
        raise ValueError(f"{name} must be a permutation of 0..{degree - 1}")
    return permutation


def _compose(p: tuple[int, ...], q: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(q[p[index]] for index in range(len(p)))


def _inverse(p: tuple[int, ...]) -> tuple[int, ...]:
    out = [0] * len(p)
    for source, target in enumerate(p):
        out[target] = source
    return tuple(out)


def _normalize_proof(proof_snapshot: Any, replay_verified: bool) -> dict[str, Any]:
    if replay_verified is not True or type(replay_verified) is not bool:
        raise ValueError("rev2707-style proof-DAG certificate must be independently replay-verified")
    proof = _literal_dict(proof_snapshot, "proof_snapshot")
    expected_proof_keys = {
        "schema_version", "status", "certified", "exact", "complete", "source_status",
        "result_identity", "action_degree", "candidate_count", "accepted_count", "node_count",
        "edge_count", "proof_dag", "proof_dag_identity", "reason",
    }
    if set(proof) != expected_proof_keys:
        raise ValueError("proof top-level fields drift")
    _strict_str(proof["reason"], "proof.reason")
    _strict_schema_version(_field(proof, "schema_version", "proof"), "proof.schema_version")
    if _strict_str(_field(proof, "status", "proof"), "proof.status") != PROOF_STATUS:
        raise ValueError("proof.status mismatch")
    for flag in ("certified", "exact", "complete"):
        _strict_true(proof, flag, "proof")
    source_status = _strict_str(_field(proof, "source_status", "proof"), "proof.source_status")
    if source_status not in {PARENT_NONEMPTY_STATUS, PARENT_EMPTY_STATUS}:
        raise ValueError("proof.source_status is not an exact parent-filtered status")
    parent_result_identity = _digest(_field(proof, "result_identity", "proof"), "proof.result_identity")
    action_degree = _strict_int(_field(proof, "action_degree", "proof"), "proof.action_degree", minimum=1)
    candidate_count = _strict_int(_field(proof, "candidate_count", "proof"), "proof.candidate_count")
    accepted_count = _strict_int(_field(proof, "accepted_count", "proof"), "proof.accepted_count")
    node_count = _strict_int(_field(proof, "node_count", "proof"), "proof.node_count", minimum=1)
    edge_count = _strict_int(_field(proof, "edge_count", "proof"), "proof.edge_count", minimum=0)
    if accepted_count > candidate_count:
        raise ValueError("proof.accepted_count exceeds proof.candidate_count")
    outcome_kind = "exact_empty" if source_status == PARENT_EMPTY_STATUS else "nonempty"
    if outcome_kind == "exact_empty" and accepted_count != 0:
        raise ValueError("exact-empty proof must have accepted_count == 0")
    if outcome_kind == "nonempty" and accepted_count < 1:
        raise ValueError("nonempty proof must have accepted_count >= 1")
    dag = _literal_json(_field(proof, "proof_dag", "proof"), "proof.proof_dag")
    if type(dag) is not dict:
        raise ValueError("proof.proof_dag must be a literal JSON object")
    proof_dag_identity = _digest(_field(proof, "proof_dag_identity", "proof"), "proof.proof_dag_identity")
    if _canonical_digest(dag) != proof_dag_identity:
        raise ValueError("proof.proof_dag_identity replay failed")
    _strict_schema_version(dag.get("schema_version"), "proof.proof_dag.schema_version")
    if dag.get("kind") != "parent_filtered_result_proof_dag_integrity_v1":
        raise ValueError("proof.proof_dag kind mismatch")
    expected_dag_keys = {
        "schema_version", "kind", "source_status", "result_identity", "action_degree",
        "candidate_count", "accepted_count", "work_bound", "nodes", "edges",
    }
    if set(dag) != expected_dag_keys:
        raise ValueError("proof.proof_dag fields drift")
    for name, expected in (("source_status", source_status), ("result_identity", parent_result_identity), ("action_degree", action_degree), ("candidate_count", candidate_count), ("accepted_count", accepted_count)):
        if dag.get(name) != expected or type(dag.get(name)) is not type(expected):
            raise ValueError(f"proof.proof_dag {name} drift")
    work_bound = _strict_int(dag.get("work_bound"), "proof.proof_dag.work_bound", minimum=1)
    nodes, edges = dag.get("nodes"), dag.get("edges")
    if type(nodes) is not list or type(edges) is not list:
        raise ValueError("proof.proof_dag nodes/edges must be literal lists")
    if len(nodes) != node_count or len(edges) != edge_count:
        raise ValueError("proof node/edge count drift")
    if nodes != sorted(nodes, key=lambda item: item.get("id") if type(item) is dict else ""):
        raise ValueError("proof nodes are not canonically sorted")
    if edges != sorted(edges, key=lambda item: (item.get("from"), item.get("to")) if type(item) is dict else ("", "")):
        raise ValueError("proof edges are not canonically sorted")
    node_by_id: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(nodes):
        node = _literal_dict(raw, f"proof.proof_dag.nodes[{index}]")
        node_id = _strict_str(node.get("id"), f"proof node {index} id")
        if node_id in node_by_id:
            raise ValueError("proof node ids must be unique")
        node_by_id[node_id] = node
    lineage_names = ("reduction", "semantic_binding", "child_instance", "child_result", "parent_filtered_result")
    identities: dict[str, str] = {}
    for kind in lineage_names:
        node_id = f"lineage:{kind}"
        node = node_by_id.get(node_id)
        if node is None or node.get("kind") != kind:
            raise ValueError(f"proof missing canonical {node_id}")
        if set(node) != {"id", "kind", "identity"}:
            raise ValueError(f"proof {node_id} fields drift")
        identities[kind] = _digest(node.get("identity"), f"proof {node_id}.identity")
    if identities["parent_filtered_result"] != parent_result_identity:
        raise ValueError("proof parent-filtered lineage identity drift")
    expected_node_ids = {f"lineage:{kind}" for kind in lineage_names}
    expected_edges = {("lineage:reduction", "lineage:semantic_binding"), ("lineage:semantic_binding", "lineage:child_instance"), ("lineage:child_instance", "lineage:child_result"), ("lineage:child_result", "lineage:parent_filtered_result")}
    representative: tuple[int, ...] | None = None
    stabilizer_elements: list[tuple[int, ...]] = []
    if outcome_kind == "nonempty":
        expected_node_ids.add("witness:representative")
        expected_edges.add(("lineage:parent_filtered_result", "witness:representative"))
        representative_node = node_by_id.get("witness:representative")
        if representative_node is None or representative_node.get("kind") != "right_coset_representative":
            raise ValueError("proof missing canonical representative witness")
        if set(representative_node) != {"id", "kind", "identity", "permutation"}:
            raise ValueError("proof representative witness fields drift")
        representative = _strict_permutation(
            representative_node.get("permutation"),
            degree=action_degree,
            name="proof representative witness permutation",
        )
        if _digest(representative_node.get("identity"), "proof representative witness identity") != _canonical_digest(("representative", representative)):
            raise ValueError("proof representative witness identity replay failed")
        for index in range(accepted_count):
            node_id = f"witness:stabilizer:{index:06d}"
            expected_node_ids.add(node_id)
            expected_edges.add(("witness:representative", node_id))
            node = node_by_id.get(node_id)
            if node is None or node.get("kind") != "parent_stabilizer_element":
                raise ValueError(f"proof missing canonical {node_id}")
            if set(node) != {"id", "kind", "identity", "permutation"}:
                raise ValueError(f"proof {node_id} fields drift")
            element = _strict_permutation(
                node.get("permutation"),
                degree=action_degree,
                name=f"proof {node_id} permutation",
            )
            if _digest(node.get("identity"), f"proof {node_id}.identity") != _canonical_digest(("stabilizer_element", element)):
                raise ValueError(f"proof {node_id} identity replay failed")
            stabilizer_elements.append(element)
        if stabilizer_elements != sorted(set(stabilizer_elements)):
            raise ValueError("proof stabilizer witnesses must be unique and canonically sorted")
        stabilizer_set = set(stabilizer_elements)
        identity = tuple(range(action_degree))
        if identity not in stabilizer_set:
            raise ValueError("proof stabilizer witnesses must contain the identity")
        for element in stabilizer_elements:
            if _inverse(element) not in stabilizer_set:
                raise ValueError("proof stabilizer witnesses are not inverse closed")
            for other in stabilizer_elements:
                if _compose(element, other) not in stabilizer_set:
                    raise ValueError("proof stabilizer witnesses are not composition closed")
        if len({_compose(representative, element) for element in stabilizer_elements}) != accepted_count:
            raise ValueError("proof representative/stabilizer reconstruction is not injective")
    if set(node_by_id) != expected_node_ids:
        raise ValueError("proof carries missing or unexpected proof-DAG nodes")
    actual_edges: set[tuple[str, str]] = set()
    for index, raw in enumerate(edges):
        edge = _literal_dict(raw, f"proof.proof_dag.edges[{index}]")
        if set(edge) != {"from", "to"}:
            raise ValueError("proof edges must have exactly from/to fields")
        actual_edges.add((_strict_str(edge["from"], "proof edge.from"), _strict_str(edge["to"], "proof edge.to")))
    if len(actual_edges) != len(edges) or actual_edges != expected_edges:
        raise ValueError("proof-DAG edge structure drift")
    source_payload = {
        "schema_version": SCHEMA_VERSION,
        "status": source_status,
        "reduction_identity": identities["reduction"],
        "semantic_binding_identity": identities["semantic_binding"],
        "child_instance_identity": identities["child_instance"],
        "child_result_identity": identities["child_result"],
        "action_degree": action_degree,
        "candidate_count": candidate_count,
        "accepted_count": accepted_count,
        "representative": representative,
        "parent_stabilizer_elements": tuple(stabilizer_elements),
        "work_bound": work_bound,
    }
    if _canonical_digest(source_payload) != parent_result_identity:
        raise ValueError("proof parent result identity source replay failed")
    return {"outcome_kind": outcome_kind, "source_status": source_status, "reduction_identity": identities["reduction"], "semantic_binding_identity": identities["semantic_binding"], "child_instance_identity": identities["child_instance"], "child_result_identity": identities["child_result"], "parent_result_identity": parent_result_identity, "child_ground_size": action_degree, "candidate_count": candidate_count, "accepted_count": accepted_count, "parent_filter_work_bound": work_bound, "proof_dag_identity": proof_dag_identity}


def _normalize_accounting(accounting_snapshot: Any, replay_verified: bool) -> dict[str, Any]:
    if replay_verified is not True or type(replay_verified) is not bool:
        raise ValueError("rev2600-style accounting certificate must be independently replay-verified")
    account = _literal_dict(accounting_snapshot, "accounting_snapshot")
    expected_accounting_keys = {
        "schema_version", "status", "certified", "exact", "complete", "outcome_kind",
        "reduction_identity", "semantic_binding_identity", "child_instance_identity",
        "child_result_identity", "parent_result_identity", "handoff_digest", "parent_action_degree",
        "child_ground_size", "candidate_count", "accepted_count", "parent_filter_work_bound",
        "charged_log2_reduction_cost", "coherence_identity", "reason",
    }
    if set(account) != expected_accounting_keys:
        raise ValueError("accounting top-level fields drift")
    _strict_str(account["reason"], "accounting.reason")
    _strict_schema_version(_field(account, "schema_version", "accounting"), "accounting.schema_version")
    if _strict_str(_field(account, "status", "accounting"), "accounting.status") != ACCOUNTING_STATUS:
        raise ValueError("accounting.status mismatch")
    for flag in ("certified", "exact", "complete"):
        _strict_true(account, flag, "accounting")
    outcome_kind = _strict_str(_field(account, "outcome_kind", "accounting"), "accounting.outcome_kind")
    if outcome_kind not in {"exact_empty", "nonempty"}:
        raise ValueError("accounting.outcome_kind mismatch")
    normalized = {
        "outcome_kind": outcome_kind,
        "reduction_identity": _digest(_field(account, "reduction_identity", "accounting"), "accounting.reduction_identity"),
        "semantic_binding_identity": _digest(_field(account, "semantic_binding_identity", "accounting"), "accounting.semantic_binding_identity"),
        "child_instance_identity": _digest(_field(account, "child_instance_identity", "accounting"), "accounting.child_instance_identity"),
        "child_result_identity": _digest(_field(account, "child_result_identity", "accounting"), "accounting.child_result_identity"),
        "parent_result_identity": _digest(_field(account, "parent_result_identity", "accounting"), "accounting.parent_result_identity"),
        "handoff_digest": _digest(_field(account, "handoff_digest", "accounting"), "accounting.handoff_digest"),
        "parent_action_degree": _strict_int(_field(account, "parent_action_degree", "accounting"), "accounting.parent_action_degree", minimum=1),
        "child_ground_size": _strict_int(_field(account, "child_ground_size", "accounting"), "accounting.child_ground_size", minimum=1),
        "candidate_count": _strict_int(_field(account, "candidate_count", "accounting"), "accounting.candidate_count"),
        "accepted_count": _strict_int(_field(account, "accepted_count", "accounting"), "accounting.accepted_count"),
        "parent_filter_work_bound": _strict_int(_field(account, "parent_filter_work_bound", "accounting"), "accounting.parent_filter_work_bound", minimum=1),
        "charged_log2_reduction_cost": _finite_nonnegative_real(_field(account, "charged_log2_reduction_cost", "accounting"), "accounting.charged_log2_reduction_cost"),
    }
    if normalized["child_ground_size"] >= normalized["parent_action_degree"]:
        raise ValueError("accounting must retain strict parent-to-child shrink")
    if normalized["accepted_count"] > normalized["candidate_count"]:
        raise ValueError("accounting.accepted_count exceeds candidate_count")
    if outcome_kind == "exact_empty" and normalized["accepted_count"] != 0:
        raise ValueError("exact-empty accounting must have accepted_count == 0")
    if outcome_kind == "nonempty" and normalized["accepted_count"] < 1:
        raise ValueError("nonempty accounting must have accepted_count >= 1")
    payload = {"schema_version": SCHEMA_VERSION, "status": ACCOUNTING_STATUS, **normalized}
    accounting_identity = _digest(_field(account, "coherence_identity", "accounting"), "accounting.coherence_identity")
    if _canonical_digest(payload) != accounting_identity:
        raise ValueError("accounting.coherence_identity replay failed")
    normalized["accounting_coherence_identity"] = accounting_identity
    return normalized


def certify_parent_filtered_proof_accounting_coherence(proof_snapshot: Any, accounting_snapshot: Any, *, proof_replay_verified: bool, accounting_replay_verified: bool) -> ParentFilteredProofAccountingCoherence:
    """Seal replayed rev2707 proof-DAG evidence to replayed rev2600 accounting evidence."""
    try:
        proof = _normalize_proof(proof_snapshot, proof_replay_verified)
        account = _normalize_accounting(accounting_snapshot, accounting_replay_verified)
        for name in ("outcome_kind", "reduction_identity", "semantic_binding_identity", "child_instance_identity", "child_result_identity", "parent_result_identity", "child_ground_size", "candidate_count", "accepted_count", "parent_filter_work_bound"):
            if proof[name] != account[name] or type(proof[name]) is not type(account[name]):
                raise ValueError(f"proof/accounting {name} mismatch")
        payload = {
            "schema_version": SCHEMA_VERSION, "status": OUTPUT_STATUS,
            "outcome_kind": proof["outcome_kind"], "source_status": proof["source_status"],
            "reduction_identity": proof["reduction_identity"], "semantic_binding_identity": proof["semantic_binding_identity"],
            "child_instance_identity": proof["child_instance_identity"], "child_result_identity": proof["child_result_identity"],
            "parent_result_identity": proof["parent_result_identity"], "proof_dag_identity": proof["proof_dag_identity"],
            "accounting_coherence_identity": account["accounting_coherence_identity"], "handoff_digest": account["handoff_digest"],
            "parent_action_degree": account["parent_action_degree"], "child_ground_size": account["child_ground_size"],
            "candidate_count": account["candidate_count"], "accepted_count": account["accepted_count"],
            "parent_filter_work_bound": account["parent_filter_work_bound"], "charged_log2_reduction_cost": account["charged_log2_reduction_cost"],
        }
        identity = _canonical_digest(payload)
        return ParentFilteredProofAccountingCoherence(
            SCHEMA_VERSION, OUTPUT_STATUS, True, True, True, payload["outcome_kind"], payload["source_status"],
            payload["reduction_identity"], payload["semantic_binding_identity"], payload["child_instance_identity"], payload["child_result_identity"],
            payload["parent_result_identity"], payload["proof_dag_identity"], payload["accounting_coherence_identity"], payload["handoff_digest"],
            payload["parent_action_degree"], payload["child_ground_size"], payload["candidate_count"], payload["accepted_count"],
            payload["parent_filter_work_bound"], payload["charged_log2_reduction_cost"], identity,
            "replayed proof-DAG lineage and replayed recurrence-accounting coherence share one exact parent-filtered result/reduction lineage; accounting units remain separately exposed",
        )
    except (TypeError, ValueError, OverflowError, KeyError) as exc:
        return _fail(str(exc))


def replay_parent_filtered_proof_accounting_coherence(certificate: ParentFilteredProofAccountingCoherence, proof_snapshot: Any, accounting_snapshot: Any, *, proof_replay_verified: bool, accounting_replay_verified: bool) -> bool:
    if type(certificate) is not ParentFilteredProofAccountingCoherence:
        return False
    replay = certify_parent_filtered_proof_accounting_coherence(proof_snapshot, accounting_snapshot, proof_replay_verified=proof_replay_verified, accounting_replay_verified=accounting_replay_verified)
    return bool(replay.certified and replay == certificate)


__all__ = ["ACCOUNTING_STATUS", "OUTPUT_STATUS", "PARENT_EMPTY_STATUS", "PARENT_NONEMPTY_STATUS", "PROOF_STATUS", "ParentFilteredProofAccountingCoherence", "certify_parent_filtered_proof_accounting_coherence", "replay_parent_filtered_proof_accounting_coherence"]
