from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = 1
SOURCE_NONEMPTY_STATUS = "exact_parent_filtered_ground_coset"
SOURCE_EMPTY_STATUS = "exact_empty_parent_filtered_ground_coset"
OUTPUT_STATUS = "certified_parent_filtered_result_proof_dag_integrity"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ParentFilteredProofDagIntegrity:
    schema_version: int
    status: str
    certified: bool
    exact: bool
    complete: bool
    source_status: str
    result_identity: str
    action_degree: int
    candidate_count: int
    accepted_count: int
    node_count: int
    edge_count: int
    proof_dag: Mapping[str, Any]
    proof_dag_identity: str
    reason: str


def _fail(reason: str) -> ParentFilteredProofDagIntegrity:
    return ParentFilteredProofDagIntegrity(
        SCHEMA_VERSION,
        "parent_filtered_result_proof_dag_integrity_not_certified",
        False,
        False,
        False,
        "",
        "",
        0,
        0,
        0,
        0,
        0,
        {},
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
    if _field(obj, name) is not True:
        raise ValueError(f"{name} must be literal true")


def _strict_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be a strict integer >= {minimum}")
    return value


def _sha(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _sha_field(obj: Any, name: str) -> str:
    value = _field(obj, name)
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a canonical sha256 identity")
    return value


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a finite sequence")
    return value


def _permutation(value: Any, *, degree: int, name: str) -> tuple[int, ...]:
    seq = _sequence(value, name)
    if len(seq) != degree:
        raise ValueError(f"{name} degree mismatch")
    out = tuple(_strict_int(item, f"{name}[{index}]") for index, item in enumerate(seq))
    if set(out) != set(range(degree)):
        raise ValueError(f"{name} must be a permutation of 0..{degree - 1}")
    return out


def _compose(p: tuple[int, ...], q: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(q[p[index]] for index in range(len(p)))


def _inverse(p: tuple[int, ...]) -> tuple[int, ...]:
    out = [0] * len(p)
    for source, target in enumerate(p):
        out[target] = source
    return tuple(out)


def _validate_subgroup(raw_elements: Any, *, degree: int) -> tuple[tuple[int, ...], ...]:
    seq = _sequence(raw_elements, "parent_stabilizer_elements")
    elements = tuple(
        _permutation(item, degree=degree, name=f"parent_stabilizer_elements[{index}]")
        for index, item in enumerate(seq)
    )
    if elements != tuple(sorted(set(elements))):
        raise ValueError("parent_stabilizer_elements must be unique and canonically sorted")
    identity = tuple(range(degree))
    if identity not in elements:
        raise ValueError("parent_stabilizer_elements must contain the identity")
    element_set = set(elements)
    for element in elements:
        if _inverse(element) not in element_set:
            raise ValueError("parent_stabilizer_elements are not inverse closed")
        for other in elements:
            if _compose(element, other) not in element_set:
                raise ValueError("parent_stabilizer_elements are not composition closed")
    return elements


def _replay_source_result(result: Any) -> dict[str, Any]:
    if _field(result, "schema_version") != SCHEMA_VERSION:
        raise ValueError("source schema_version mismatch")
    status = _field(result, "status")
    if status not in (SOURCE_NONEMPTY_STATUS, SOURCE_EMPTY_STATUS):
        raise ValueError("source status mismatch")
    for flag in ("certified", "exact", "complete"):
        _strict_true(result, flag)

    reduction_identity = _sha_field(result, "reduction_identity")
    semantic_binding_identity = _sha_field(result, "semantic_binding_identity")
    child_instance_identity = _sha_field(result, "child_instance_identity")
    child_result_identity = _sha_field(result, "child_result_identity")
    action_degree = _strict_int(_field(result, "action_degree"), "action_degree", minimum=1)
    candidate_count = _strict_int(_field(result, "candidate_count"), "candidate_count")
    accepted_count = _strict_int(_field(result, "accepted_count"), "accepted_count")
    work_bound = _strict_int(_field(result, "work_bound"), "work_bound", minimum=1)
    if accepted_count > candidate_count:
        raise ValueError("accepted_count exceeds candidate_count")

    if status == SOURCE_EMPTY_STATUS:
        if accepted_count != 0:
            raise ValueError("empty source result must have accepted_count == 0")
        if _field(result, "representative") is not None:
            raise ValueError("empty source result must not carry a representative")
        if tuple(_sequence(_field(result, "parent_stabilizer_elements"), "parent_stabilizer_elements")):
            raise ValueError("empty source result must not carry stabilizer witnesses")
        representative = None
        stabilizer_elements: tuple[tuple[int, ...], ...] = ()
    else:
        if accepted_count < 1:
            raise ValueError("nonempty source result must have accepted_count >= 1")
        representative = _permutation(
            _field(result, "representative"), degree=action_degree, name="representative"
        )
        stabilizer_elements = _validate_subgroup(
            _field(result, "parent_stabilizer_elements"), degree=action_degree
        )
        if len(stabilizer_elements) != accepted_count:
            raise ValueError("stabilizer cardinality must equal accepted_count for the exact right coset")
        reconstructed = tuple(
            sorted({_compose(representative, element) for element in stabilizer_elements})
        )
        if len(reconstructed) != accepted_count:
            raise ValueError("representative/stabilizer reconstruction is not injective")

    source_payload = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "reduction_identity": reduction_identity,
        "semantic_binding_identity": semantic_binding_identity,
        "child_instance_identity": child_instance_identity,
        "child_result_identity": child_result_identity,
        "action_degree": action_degree,
        "candidate_count": candidate_count,
        "accepted_count": accepted_count,
        "representative": representative,
        "parent_stabilizer_elements": stabilizer_elements,
        "work_bound": work_bound,
    }
    result_identity = _sha_field(result, "result_identity")
    if result_identity != _sha(source_payload):
        raise ValueError("source result_identity replay failed")
    return {**source_payload, "result_identity": result_identity}


def certify_parent_filtered_result_proof_dag(result: Any) -> ParentFilteredProofDagIntegrity:
    try:
        source = _replay_source_result(result)
        lineage = (
            ("reduction", source["reduction_identity"]),
            ("semantic_binding", source["semantic_binding_identity"]),
            ("child_instance", source["child_instance_identity"]),
            ("child_result", source["child_result_identity"]),
            ("parent_filtered_result", source["result_identity"]),
        )
        nodes: list[dict[str, Any]] = [
            {"id": f"lineage:{kind}", "kind": kind, "identity": identity}
            for kind, identity in lineage
        ]
        edges: list[dict[str, str]] = [
            {"from": "lineage:reduction", "to": "lineage:semantic_binding"},
            {"from": "lineage:semantic_binding", "to": "lineage:child_instance"},
            {"from": "lineage:child_instance", "to": "lineage:child_result"},
            {"from": "lineage:child_result", "to": "lineage:parent_filtered_result"},
        ]
        if source["status"] == SOURCE_NONEMPTY_STATUS:
            representative = source["representative"]
            assert representative is not None
            nodes.append({
                "id": "witness:representative",
                "kind": "right_coset_representative",
                "identity": _sha(("representative", representative)),
                "permutation": representative,
            })
            edges.append({"from": "lineage:parent_filtered_result", "to": "witness:representative"})
            for index, element in enumerate(source["parent_stabilizer_elements"]):
                node_id = f"witness:stabilizer:{index:06d}"
                nodes.append({
                    "id": node_id,
                    "kind": "parent_stabilizer_element",
                    "identity": _sha(("stabilizer_element", element)),
                    "permutation": element,
                })
                edges.append({"from": "witness:representative", "to": node_id})
        nodes = sorted(nodes, key=lambda item: item["id"])
        edges = sorted(edges, key=lambda item: (item["from"], item["to"]))
        dag = {
            "schema_version": SCHEMA_VERSION,
            "kind": "parent_filtered_result_proof_dag_integrity_v1",
            "source_status": source["status"],
            "result_identity": source["result_identity"],
            "action_degree": source["action_degree"],
            "candidate_count": source["candidate_count"],
            "accepted_count": source["accepted_count"],
            "work_bound": source["work_bound"],
            "nodes": nodes,
            "edges": edges,
        }
        return ParentFilteredProofDagIntegrity(
            SCHEMA_VERSION,
            OUTPUT_STATUS,
            True,
            True,
            True,
            source["status"],
            source["result_identity"],
            source["action_degree"],
            source["candidate_count"],
            source["accepted_count"],
            len(nodes),
            len(edges),
            dag,
            _sha(dag),
            "rev2200-shaped public result identity replayed exactly and its empty/nonempty witness semantics bound into a canonical deterministic proof DAG",
        )
    except (TypeError, ValueError, OverflowError, KeyError) as exc:
        return _fail(str(exc))


def replay_parent_filtered_result_proof_dag(result: Any, certificate: Any) -> ParentFilteredProofDagIntegrity:
    try:
        expected = certify_parent_filtered_result_proof_dag(result)
        if not expected.certified:
            raise ValueError(f"source result did not certify: {expected.reason}")
        if _field(certificate, "schema_version") != SCHEMA_VERSION:
            raise ValueError("certificate schema_version mismatch")
        if _field(certificate, "status") != OUTPUT_STATUS:
            raise ValueError("certificate status mismatch")
        for flag in ("certified", "exact", "complete"):
            _strict_true(certificate, flag)
        for name in (
            "source_status", "result_identity", "action_degree", "candidate_count",
            "accepted_count", "node_count", "edge_count", "proof_dag_identity",
        ):
            if _field(certificate, name) != getattr(expected, name):
                raise ValueError(f"certificate {name} drift")
        proof_dag = _field(certificate, "proof_dag")
        if proof_dag != expected.proof_dag:
            raise ValueError("certificate proof_dag drift")
        if _sha(proof_dag) != expected.proof_dag_identity:
            raise ValueError("certificate proof_dag_identity replay failed")
        return expected
    except (TypeError, ValueError, OverflowError, KeyError) as exc:
        return _fail(str(exc))
