from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Any, Sequence

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from s1_proof_identity_v1 import build_s1_proof_identity, validate_s1_proof_identity
from s1_string_isomorphism_v4 import s1_string_isomorphism_v4

SCHEMA_VERSION = 1
REDUCTION_STATUS = "certified_johnson_ground_relational_reduction"
CHILD_NONEMPTY_STATUS = "exact_recursive_ground_coset"
CHILD_EMPTY_STATUS = "exact_empty_recursive_ground_coset"
OUTPUT_STATUS = "certified_recursive_ground_s1_child_instance_execution"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class RecursiveGroundExactResultSnapshot:
    schema_version: int
    status: str
    exact: bool
    complete: bool
    canonical: bool
    ambient_membership_certified: bool
    action_degree: int
    reduction_identity: str
    representative: tuple[int, ...] | None
    stabilizer_generators: tuple[tuple[int, ...], ...]
    result_identity: str


@dataclass(frozen=True)
class RecursiveChildInstanceExecution:
    schema_version: int
    status: str
    certified: bool
    exact: bool
    complete: bool
    action_degree: int
    reduction_identity: str
    child_instance_identity: str
    parent_child_semantic_transport_certified: bool
    child_result: RecursiveGroundExactResultSnapshot | None
    child_proof: ProofCarryingCoset | None
    reason: str


def _fail(reason: str, *, proof: ProofCarryingCoset | None = None) -> RecursiveChildInstanceExecution:
    return RecursiveChildInstanceExecution(
        SCHEMA_VERSION,
        "recursive_ground_s1_child_instance_execution_not_certified",
        False,
        False,
        False,
        0,
        "",
        "",
        False,
        None,
        proof,
        reason,
    )


def _field(obj: Any, name: str) -> Any:
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


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a finite sequence")
    return value


def _normalize_json(value: Any, path: str = "value") -> Any:
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path} must be finite")
        return value
    if isinstance(value, (list, tuple)):
        return [_normalize_json(item, f"{path}[{i}]") for i, item in enumerate(value)]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{path} dictionary keys must be strings")
            out[key] = _normalize_json(item, f"{path}.{key}")
        return out
    raise ValueError(f"{path} is not replay-stable JSON data")


def _sha256(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _normalize_permutation(raw: Any, *, degree: int, name: str) -> tuple[int, ...]:
    seq = _sequence(raw, name)
    if len(seq) != degree:
        raise ValueError(f"{name} has the wrong degree")
    perm = tuple(_strict_int(image, f"{name}[{i}]", minimum=0) for i, image in enumerate(seq))
    if any(image >= degree for image in perm) or len(set(perm)) != degree:
        raise ValueError(f"{name} is not a permutation of 0..{degree - 1}")
    return perm


def _normalize_reduction(reduction: Any, *, reduction_replay_verified: bool) -> dict[str, Any]:
    if type(reduction_replay_verified) is not bool or not reduction_replay_verified:
        raise ValueError("rev287-style reduction must be independently replay-verified before child execution")
    if _field(reduction, "schema_version") != SCHEMA_VERSION:
        raise ValueError("reduction schema_version mismatch")
    if _field(reduction, "status") != REDUCTION_STATUS:
        raise ValueError("reduction status mismatch")
    for name in (
        "certified",
        "canonical",
        "exact",
        "progress_certified",
        "solution_transport_certified",
        "ambient_membership_transport_certified",
        "complement_ambiguity_handled",
    ):
        _strict_true(reduction, name)

    n = _strict_int(_field(reduction, "source_action_degree"), "source_action_degree", minimum=1)
    v = _strict_int(_field(reduction, "johnson_ground_size"), "johnson_ground_size", minimum=4)
    k = _strict_int(_field(reduction, "johnson_subset_size"), "johnson_subset_size", minimum=2)
    child = _strict_int(_field(reduction, "child_ground_size"), "child_ground_size", minimum=1)
    if k > v - 2 or n != comb(v, k) or child != v or n <= v:
        raise ValueError("reduction Johnson dimensions are inconsistent or do not strictly shrink")

    reduction_identity = _field(reduction, "reduction_identity")
    if not isinstance(reduction_identity, str) or _SHA256_RE.fullmatch(reduction_identity) is None:
        raise ValueError("reduction_identity must be canonical sha256:<64-hex>")

    raw_vertices = _sequence(_field(reduction, "canonical_vertex_subsets"), "canonical_vertex_subsets")
    vertices: list[tuple[int, ...]] = []
    for index, raw in enumerate(raw_vertices):
        seq = _sequence(raw, f"canonical_vertex_subsets[{index}]")
        if len(seq) != k:
            raise ValueError("canonical vertex has the wrong subset size")
        subset = tuple(_strict_int(point, f"canonical_vertex_subsets[{index}]", minimum=0) for point in seq)
        if tuple(sorted(subset)) != subset or len(set(subset)) != k or any(point >= v for point in subset):
            raise ValueError("canonical vertex is not a sorted k-subset of the Johnson ground")
        vertices.append(subset)
    if len(vertices) != n or set(vertices) != set(combinations(range(v), k)):
        raise ValueError("canonical_vertex_subsets is not the complete J(v,k) vertex family")

    raw_generators = _sequence(_field(reduction, "induced_ground_generators"), "induced_ground_generators")
    generators = tuple(
        _normalize_permutation(raw, degree=v, name=f"induced_ground_generators[{index}]")
        for index, raw in enumerate(raw_generators)
    )
    construction_work = _strict_int(
        _field(reduction, "construction_work_bound"), "construction_work_bound", minimum=1
    )
    return {
        "source_action_degree": n,
        "ground_size": v,
        "subset_size": k,
        "reduction_identity": reduction_identity,
        "canonical_vertex_subsets": tuple(vertices),
        "induced_ground_generators": generators,
        "construction_work_bound": construction_work,
    }


def _normalize_values(raw: Any, *, degree: int, name: str) -> tuple[Any, ...]:
    seq = _sequence(raw, name)
    if len(seq) != degree:
        raise ValueError(f"{name} must have exactly {degree} entries")
    return tuple(_normalize_json(value, f"{name}[{index}]") for index, value in enumerate(seq))


def _canonical_subgroup_generators(subgroup, *, degree: int) -> tuple[tuple[int, ...], ...]:
    raw = getattr(subgroup, "original_generators", None)
    if raw is None:
        raw = getattr(subgroup, "generators", ())
    normalized = tuple(
        _normalize_permutation(generator, degree=degree, name=f"child_stabilizer_generator[{index}]")
        for index, generator in enumerate(tuple(raw))
    )
    return tuple(sorted(set(normalized)))


def _same_group_from_generators(subgroup, generators: tuple[tuple[int, ...], ...], *, degree: int) -> bool:
    rebuilt = schreier_stabilizer_chain(generators or (identity(degree),))
    if rebuilt.order != subgroup.order:
        return False
    subgroup_generators = tuple(getattr(subgroup, "original_generators", getattr(subgroup, "generators", ())))
    if any(not subgroup.contains(generator) for generator in generators):
        return False
    if any(not rebuilt.contains(tuple(generator)) for generator in subgroup_generators):
        return False
    return True


def _child_result_snapshot(
    proof: ProofCarryingCoset,
    *,
    ambient_group,
    degree: int,
    reduction_identity: str,
) -> RecursiveGroundExactResultSnapshot:
    if proof.coset is None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": CHILD_EMPTY_STATUS,
            "exact": True,
            "complete": True,
            "canonical": True,
            "ambient_membership_certified": True,
            "action_degree": degree,
            "reduction_identity": reduction_identity,
            "representative": None,
            "stabilizer_generators": (),
        }
        return RecursiveGroundExactResultSnapshot(
            SCHEMA_VERSION,
            CHILD_EMPTY_STATUS,
            True,
            True,
            True,
            True,
            degree,
            reduction_identity,
            None,
            (),
            _sha256(payload),
        )

    coset: RightCoset = proof.coset
    representative = _normalize_permutation(coset.representative, degree=degree, name="child_representative")
    if not ambient_group.contains(representative):
        raise ValueError("executed child representative left the induced ground group")
    generators = _canonical_subgroup_generators(coset.subgroup, degree=degree)
    if any(not ambient_group.contains(generator) for generator in generators):
        raise ValueError("executed child stabilizer left the induced ground group")
    if not _same_group_from_generators(coset.subgroup, generators, degree=degree):
        raise ValueError("child stabilizer generators do not reconstruct the executed subgroup exactly")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": CHILD_NONEMPTY_STATUS,
        "exact": True,
        "complete": True,
        "canonical": True,
        "ambient_membership_certified": True,
        "action_degree": degree,
        "reduction_identity": reduction_identity,
        "representative": representative,
        "stabilizer_generators": generators,
    }
    return RecursiveGroundExactResultSnapshot(
        SCHEMA_VERSION,
        CHILD_NONEMPTY_STATUS,
        True,
        True,
        True,
        True,
        degree,
        reduction_identity,
        representative,
        generators,
        _sha256(payload),
    )


def execute_recursive_ground_s1_child_instance(
    reduction: Any,
    *,
    reduction_replay_verified: bool,
    child_source_values: Sequence[Any],
    child_target_values: Sequence[Any],
    original_root_n: int,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 4096,
    max_partition_states: int = 4096,
    max_recognition_nodes: int = 500000,
    max_depth: int = 64,
) -> RecursiveChildInstanceExecution:
    """Execute one explicit induced-ground S1 child and freeze its exact instance.

    The reduction contract supplies the represented ground group, while the caller
    supplies the child source/target strings.  This routine *actually executes*
    the main-integrated S1 v4 dispatcher on that exact group/string instance and
    validates the attached S1ProofIdentity against the complete execution inputs
    and resource gates.  If S1 remains unresolved, or if its identity is unstable,
    certification fails closed.

    The returned child-result snapshot deliberately matches rev293's public
    result/hash shape so downstream adapters can compare exact coset semantics
    without importing branch-only code.

    Crucially, this routine does NOT prove that the supplied child strings are the
    mathematically correct reduction of a parent colored Johnson relation.  The
    output therefore exposes parent_child_semantic_transport_certified=False.
    A separate constructive semantic bridge remains mandatory before this child
    execution can close corrected Split-or-Johnson production.
    """
    try:
        normalized = _normalize_reduction(
            reduction, reduction_replay_verified=reduction_replay_verified
        )
        v = normalized["ground_size"]
        source = _normalize_values(child_source_values, degree=v, name="child_source_values")
        target = _normalize_values(child_target_values, degree=v, name="child_target_values")
        root_n = _strict_int(original_root_n, "original_root_n", minimum=1)
        if root_n < normalized["source_action_degree"]:
            raise ValueError("original_root_n must dominate the parent Johnson action degree")
        for value, name in (
            (polylog_power, "polylog_power"),
            (max_explicit_degree, "max_explicit_degree"),
            (group_order_poly_power, "group_order_poly_power"),
            (max_group_order, "max_group_order"),
            (max_partition_states, "max_partition_states"),
            (max_recognition_nodes, "max_recognition_nodes"),
        ):
            _strict_int(value, name, minimum=1)
        _strict_int(max_depth, "max_depth", minimum=0)
    except (TypeError, ValueError, OverflowError) as exc:
        return _fail(str(exc))

    try:
        group = schreier_stabilizer_chain(
            normalized["induced_ground_generators"] or (identity(v),)
        )
        proof = s1_string_isomorphism_v4(
            group,
            source,
            target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
            group_order_poly_power=group_order_poly_power,
            max_group_order=max_group_order,
            max_partition_states=max_partition_states,
            max_recognition_nodes=max_recognition_nodes,
            max_depth=max_depth,
        )
    except Exception as exc:  # execution failures are fail-closed evidence, never exactness
        return _fail(f"child S1 execution failed closed: {type(exc).__name__}: {exc}")

    if not isinstance(proof, ProofCarryingCoset):
        return _fail("main S1 dispatcher did not return ProofCarryingCoset", proof=proof)
    if type(proof.exact) is not bool or not proof.exact:
        return _fail("main S1 dispatcher left this explicit child instance unresolved", proof=proof)
    if type(proof.canonical) is not bool or not proof.canonical:
        return _fail("exact child proof is not canonical", proof=proof)
    if type(proof.local_cost_certified) is not bool or not proof.local_cost_certified:
        return _fail("exact child proof lacks certified local execution cost", proof=proof)

    try:
        expected_identity = build_s1_proof_identity(
            group,
            source,
            target,
            root_n=root_n,
            recursion_depth=0,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
            group_order_poly_power=group_order_poly_power,
            max_group_order=max_group_order,
            max_partition_states=max_partition_states,
            max_recognition_nodes=max_recognition_nodes,
            max_depth=max_depth,
        )
        identity_validation = validate_s1_proof_identity(proof, expected_identity)
        if not identity_validation.certified:
            raise ValueError(identity_validation.reason)
        snapshot = _child_result_snapshot(
            proof,
            ambient_group=group,
            degree=v,
            reduction_identity=normalized["reduction_identity"],
        )
        child_instance_identity = _sha256(
            {
                "schema_version": SCHEMA_VERSION,
                "scope": "corrected-soj-recursive-ground-s1-child-instance-v1",
                "reduction_identity": normalized["reduction_identity"],
                "source_action_degree": normalized["source_action_degree"],
                "ground_size": v,
                "subset_size": normalized["subset_size"],
                "induced_ground_generators": normalized["induced_ground_generators"],
                "child_source_values": source,
                "child_target_values": target,
                "original_root_n": root_n,
                "resources": {
                    "polylog_power": polylog_power,
                    "max_explicit_degree": max_explicit_degree,
                    "group_order_poly_power": group_order_poly_power,
                    "max_group_order": max_group_order,
                    "max_partition_states": max_partition_states,
                    "max_recognition_nodes": max_recognition_nodes,
                    "max_depth": max_depth,
                },
                "child_result_identity": snapshot.result_identity,
            }
        )
    except (TypeError, ValueError, OverflowError) as exc:
        return _fail(str(exc), proof=proof)

    return RecursiveChildInstanceExecution(
        SCHEMA_VERSION,
        OUTPUT_STATUS,
        True,
        True,
        True,
        v,
        normalized["reduction_identity"],
        child_instance_identity,
        False,
        snapshot,
        proof,
        (
            "one explicit induced-ground S1 instance executed exactly and its full S1 identity/result snapshot replay; "
            "parent-to-child string semantics remain deliberately uncertified"
        ),
    )


__all__ = [
    "RecursiveGroundExactResultSnapshot",
    "RecursiveChildInstanceExecution",
    "execute_recursive_ground_s1_child_instance",
]
