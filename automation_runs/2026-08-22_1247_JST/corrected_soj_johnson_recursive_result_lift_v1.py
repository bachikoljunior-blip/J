from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Any, Sequence

SCHEMA_VERSION = 1
REDUCTION_STATUS = "certified_johnson_ground_relational_reduction"
CHILD_NONEMPTY_STATUS = "exact_recursive_ground_coset"
CHILD_EMPTY_STATUS = "exact_empty_recursive_ground_coset"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class RecursiveGroundExactResultEvidence:
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
class JohnsonRecursiveResultLiftCertificate:
    schema_version: int
    status: str
    certified: bool
    exact: bool
    complete: bool
    parent_action_degree: int
    child_ground_size: int
    reduction_identity: str
    child_result_identity: str
    parent_representative: tuple[int, ...] | None
    parent_stabilizer_generators: tuple[tuple[int, ...], ...]
    transcript_digest: str
    reason: str


def _fail(reason: str, *, n: int = 0, v: int = 0, reduction_identity: str = "", child_identity: str = "") -> JohnsonRecursiveResultLiftCertificate:
    return JohnsonRecursiveResultLiftCertificate(
        SCHEMA_VERSION,
        "johnson_recursive_result_lift_not_certified",
        False,
        False,
        False,
        n,
        v,
        reduction_identity,
        child_identity,
        None,
        (),
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


def _strict_int_value(value: Any, name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be a strict integer")
    return value


def _strict_int(obj: Any, name: str) -> int:
    return _strict_int_value(_field(obj, name), name)


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a finite sequence")
    return value


def _normalize_permutation(raw: Any, *, degree: int, name: str) -> tuple[int, ...]:
    seq = _sequence(raw, name)
    if len(seq) != degree:
        raise ValueError(f"{name} has the wrong action degree")
    perm = tuple(_strict_int_value(image, f"{name}[{i}]") for i, image in enumerate(seq))
    if any(image < 0 or image >= degree for image in perm) or len(set(perm)) != degree:
        raise ValueError(f"{name} is not a permutation of 0..{degree - 1}")
    return perm


def _json_value(value: Any, path: str = "value") -> Any:
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{path} must be finite")
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(item, f"{path}[{i}]") for i, item in enumerate(value)]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{path} dictionary keys must be strings")
            normalized[key] = _json_value(item, f"{path}.{key}")
        return normalized
    raise ValueError(f"{path} is not replay-stable JSON data")


def _sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _normalize_values(raw: Any, *, degree: int, name: str) -> tuple[Any, ...]:
    seq = _sequence(raw, name)
    if len(seq) != degree:
        raise ValueError(f"{name} has the wrong parent action degree")
    return tuple(_json_value(value, f"{name}[{i}]") for i, value in enumerate(seq))


def _normalize_reduction(reduction: Any, *, reduction_replay_verified: bool) -> tuple[int, int, int, str, tuple[tuple[int, ...], ...]]:
    if type(reduction_replay_verified) is not bool or not reduction_replay_verified:
        raise ValueError("rev287-style reduction evidence must be replay-verified independently before lifting")
    if str(_field(reduction, "status")) != REDUCTION_STATUS:
        raise ValueError("result lift requires certified Johnson-ground relational-reduction evidence")
    for field in (
        "certified",
        "canonical",
        "exact",
        "progress_certified",
        "solution_transport_certified",
        "ambient_membership_transport_certified",
        "complement_ambiguity_handled",
    ):
        if not _strict_bool(reduction, field):
            raise ValueError(f"reduction field {field} must be true")
    n = _strict_int(reduction, "source_action_degree")
    v = _strict_int(reduction, "johnson_ground_size")
    k = _strict_int(reduction, "johnson_subset_size")
    child = _strict_int(reduction, "child_ground_size")
    if v < 4 or not 2 <= k <= v - 2 or n != comb(v, k) or child != v or n <= v:
        raise ValueError("reduction Johnson dimensions are inconsistent or do not strictly shrink")
    reduction_identity = str(_field(reduction, "reduction_identity"))
    if not _SHA256_RE.fullmatch(reduction_identity):
        raise ValueError("reduction_identity must be a canonical sha256 digest")

    raw_subsets = _sequence(_field(reduction, "canonical_vertex_subsets"), "canonical_vertex_subsets")
    if len(raw_subsets) != n:
        raise ValueError("canonical_vertex_subsets length differs from source_action_degree")
    subsets: list[tuple[int, ...]] = []
    for i, raw in enumerate(raw_subsets):
        seq = _sequence(raw, f"canonical_vertex_subsets[{i}]")
        if len(seq) != k:
            raise ValueError(f"canonical_vertex_subsets[{i}] has the wrong subset size")
        subset = tuple(_strict_int_value(point, f"canonical_vertex_subsets[{i}][{j}]") for j, point in enumerate(seq))
        if tuple(sorted(subset)) != subset or len(set(subset)) != k or any(point < 0 or point >= v for point in subset):
            raise ValueError(f"canonical_vertex_subsets[{i}] is not a canonical k-subset")
        subsets.append(subset)
    if len(set(subsets)) != n or set(subsets) != set(combinations(range(v), k)):
        raise ValueError("canonical_vertex_subsets is not a complete J(v,k) vertex family")
    return n, v, k, reduction_identity, tuple(subsets)


def _child_payload(child: RecursiveGroundExactResultEvidence) -> dict[str, Any]:
    return {
        "schema_version": child.schema_version,
        "status": child.status,
        "exact": child.exact,
        "complete": child.complete,
        "canonical": child.canonical,
        "ambient_membership_certified": child.ambient_membership_certified,
        "action_degree": child.action_degree,
        "reduction_identity": child.reduction_identity,
        "representative": child.representative,
        "stabilizer_generators": child.stabilizer_generators,
    }


def child_result_identity(child: RecursiveGroundExactResultEvidence) -> str:
    """Return the deterministic identity required for a child-result snapshot.

    This hashes the supplied snapshot; it does not itself certify the semantic
    exactness flags. Those remain an upstream proof obligation.
    """
    return _sha256(_child_payload(child))


def _normalize_child(child: Any, *, v: int, reduction_identity: str) -> RecursiveGroundExactResultEvidence:
    if not isinstance(child, RecursiveGroundExactResultEvidence):
        raise ValueError("child_result must be RecursiveGroundExactResultEvidence")
    if child.schema_version != SCHEMA_VERSION:
        raise ValueError("child_result schema version mismatch")
    if child.status not in {CHILD_NONEMPTY_STATUS, CHILD_EMPTY_STATUS}:
        raise ValueError("child_result has an unsupported exact-result status")
    for field in ("exact", "complete", "canonical", "ambient_membership_certified"):
        if type(getattr(child, field)) is not bool or not getattr(child, field):
            raise ValueError(f"child_result field {field} must be strict true")
    if type(child.action_degree) is not int or child.action_degree != v:
        raise ValueError("child_result action degree differs from the certified Johnson ground")
    if child.reduction_identity != reduction_identity:
        raise ValueError("child_result is not bound to the same reduction identity")
    if not _SHA256_RE.fullmatch(child.result_identity):
        raise ValueError("child_result result_identity must be a canonical sha256 digest")

    if child.status == CHILD_EMPTY_STATUS:
        if child.representative is not None or child.stabilizer_generators != ():
            raise ValueError("exact-empty child result may not carry a representative or stabilizer generators")
        normalized = child
    else:
        if child.representative is None:
            raise ValueError("nonempty child result requires a representative")
        representative = _normalize_permutation(child.representative, degree=v, name="child_result.representative")
        raw_generators = _sequence(child.stabilizer_generators, "child_result.stabilizer_generators")
        generators = tuple(
            _normalize_permutation(raw, degree=v, name=f"child_result.stabilizer_generators[{i}]")
            for i, raw in enumerate(raw_generators)
        )
        canonical_generators = tuple(sorted(set(generators)))
        if generators != canonical_generators:
            raise ValueError("child_result stabilizer_generators must be unique and lexicographically canonical")
        normalized = RecursiveGroundExactResultEvidence(
            child.schema_version,
            child.status,
            child.exact,
            child.complete,
            child.canonical,
            child.ambient_membership_certified,
            child.action_degree,
            child.reduction_identity,
            representative,
            generators,
            child.result_identity,
        )
    if child_result_identity(normalized) != normalized.result_identity:
        raise ValueError("child_result identity does not replay from its exact snapshot")
    return normalized


def _lift_ground_permutation(
    ground_perm: tuple[int, ...],
    *,
    vertex_subsets: tuple[tuple[int, ...], ...],
) -> tuple[int, ...]:
    subset_to_vertex = {subset: index for index, subset in enumerate(vertex_subsets)}
    lifted: list[int] = []
    for subset in vertex_subsets:
        image_subset = tuple(sorted(ground_perm[point] for point in subset))
        image_vertex = subset_to_vertex.get(image_subset)
        if image_vertex is None:
            raise ValueError("ground permutation does not induce a complete permutation of Johnson vertices")
        lifted.append(image_vertex)
    if len(set(lifted)) != len(vertex_subsets):
        raise ValueError("lifted Johnson action is not a permutation")
    return tuple(lifted)


def _transports(source: tuple[Any, ...], target: tuple[Any, ...], permutation: tuple[int, ...]) -> bool:
    return all(source[index] == target[permutation[index]] for index in range(len(source)))


def _stabilizes(values: tuple[Any, ...], permutation: tuple[int, ...]) -> bool:
    return all(values[index] == values[permutation[index]] for index in range(len(values)))


def certify_johnson_recursive_child_result_lift(
    reduction: Any,
    child_result: RecursiveGroundExactResultEvidence,
    *,
    reduction_replay_verified: bool,
    parent_source_values: Sequence[Any],
    parent_target_values: Sequence[Any],
) -> JohnsonRecursiveResultLiftCertificate:
    """Lift an exact recursive Johnson-ground result back to J(v,k).

    The reduction itself must have been replayed independently. The child result
    must be exact/complete/canonical and explicitly bound to that same reduction
    identity. For a nonempty child coset, every ground permutation is induced on
    the full Johnson vertex family and then checked against the original parent
    strings. For an exact-empty child, exact solution transport from the replayed
    reduction promotes emptiness without inventing a representative.

    The routine performs no recursive String Isomorphism and no recurrence/cost
    accounting. It only certifies the post-recursion solution transport boundary.
    """
    try:
        n, v, _k, reduction_identity, subsets = _normalize_reduction(
            reduction, reduction_replay_verified=reduction_replay_verified
        )
        source = _normalize_values(parent_source_values, degree=n, name="parent_source_values")
        target = _normalize_values(parent_target_values, degree=n, name="parent_target_values")
        child = _normalize_child(child_result, v=v, reduction_identity=reduction_identity)
    except (TypeError, ValueError) as exc:
        return _fail(str(exc))

    values_digest = _sha256({"source": source, "target": target})
    if child.status == CHILD_EMPTY_STATUS:
        transcript = _sha256(
            {
                "schema_version": SCHEMA_VERSION,
                "status": "certified_exact_empty_parent_johnson_result",
                "reduction_identity": reduction_identity,
                "child_result_identity": child.result_identity,
                "parent_values_digest": values_digest,
                "parent_action_degree": n,
                "child_ground_size": v,
            }
        )
        return JohnsonRecursiveResultLiftCertificate(
            SCHEMA_VERSION,
            "certified_exact_empty_parent_johnson_result",
            True,
            True,
            True,
            n,
            v,
            reduction_identity,
            child.result_identity,
            None,
            (),
            transcript,
            "exact-empty recursive ground result is promoted through independently replayed exact solution transport",
        )

    assert child.representative is not None
    try:
        parent_rep = _lift_ground_permutation(child.representative, vertex_subsets=subsets)
        parent_gens = tuple(
            _lift_ground_permutation(generator, vertex_subsets=subsets)
            for generator in child.stabilizer_generators
        )
    except ValueError as exc:
        return _fail(
            str(exc), n=n, v=v, reduction_identity=reduction_identity, child_identity=child.result_identity
        )
    if not _transports(source, target, parent_rep):
        return _fail(
            "lifted child representative does not transport the original parent source string to the target string",
            n=n,
            v=v,
            reduction_identity=reduction_identity,
            child_identity=child.result_identity,
        )
    for index, generator in enumerate(parent_gens):
        if not _stabilizes(target, generator):
            return _fail(
                f"lifted child stabilizer generator {index} does not stabilize the original parent target string",
                n=n,
                v=v,
                reduction_identity=reduction_identity,
                child_identity=child.result_identity,
            )

    transcript = _sha256(
        {
            "schema_version": SCHEMA_VERSION,
            "status": "certified_exact_parent_johnson_coset_lift",
            "reduction_identity": reduction_identity,
            "child_result_identity": child.result_identity,
            "parent_values_digest": values_digest,
            "parent_action_degree": n,
            "child_ground_size": v,
            "parent_representative": parent_rep,
            "parent_stabilizer_generators": parent_gens,
        }
    )
    return JohnsonRecursiveResultLiftCertificate(
        SCHEMA_VERSION,
        "certified_exact_parent_johnson_coset_lift",
        True,
        True,
        True,
        n,
        v,
        reduction_identity,
        child.result_identity,
        parent_rep,
        parent_gens,
        transcript,
        "complete exact recursive ground coset is induced on every J(v,k) vertex and independently verified against the original parent strings",
    )


def replay_johnson_recursive_child_result_lift(
    certificate: JohnsonRecursiveResultLiftCertificate,
    reduction: Any,
    child_result: RecursiveGroundExactResultEvidence,
    **kwargs: Any,
) -> bool:
    if not isinstance(certificate, JohnsonRecursiveResultLiftCertificate) or not certificate.certified:
        return False
    replay = certify_johnson_recursive_child_result_lift(reduction, child_result, **kwargs)
    return bool(
        replay.certified
        and replay == certificate
        and replay.transcript_digest == certificate.transcript_digest
    )


__all__ = [
    "RecursiveGroundExactResultEvidence",
    "JohnsonRecursiveResultLiftCertificate",
    "child_result_identity",
    "certify_johnson_recursive_child_result_lift",
    "replay_johnson_recursive_child_result_lift",
]
