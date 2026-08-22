from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from itertools import combinations
from math import comb, isfinite
import re
from typing import Any, Sequence

SCHEMA_VERSION = 1
SOURCE_SCHEMA_VERSION = 1
SOURCE_STATUS = "certified_johnson_ground_relational_reduction"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class JohnsonConstructionCostBinding:
    schema_version: int
    status: str
    certified: bool
    canonical: bool
    exact: bool
    progress_certified: bool
    solution_transport_certified: bool
    ambient_membership_transport_certified: bool
    complement_ambiguity_handled: bool
    source_action_degree: int
    johnson_ground_size: int
    johnson_subset_size: int
    child_ground_size: int
    multiplicative_cost: float
    max_multiplicative_cost: float
    reduction_identity: str
    source_construction_work_bound: int
    conservative_construction_cost_bound: float
    cost_binding_identity: str
    reason: str


def _fail(reason: str) -> JohnsonConstructionCostBinding:
    return JohnsonConstructionCostBinding(
        SCHEMA_VERSION,
        "johnson_construction_cost_binding_not_certified",
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        0,
        0,
        0,
        0,
        0.0,
        0.0,
        "",
        0,
        0.0,
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


def _strict_sequence(obj: Any, name: str) -> Sequence[Any]:
    value = _field(obj, name)
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a finite sequence")
    return value


def _strict_cost(obj: Any, name: str) -> float:
    value = _field(obj, name)
    if type(value) not in (int, float) or type(value) is bool:
        raise ValueError(f"{name} must be a real number")
    result = float(value)
    if not isfinite(result) or result < 1.0:
        raise ValueError(f"{name} must be finite and at least one")
    return result


def _canonical_vertex_subsets(
    evidence: Any,
    *,
    v: int,
    k: int,
    n: int,
) -> tuple[tuple[int, ...], ...]:
    raw_vertices = _strict_sequence(evidence, "canonical_vertex_subsets")
    if len(raw_vertices) != n:
        raise ValueError("canonical_vertex_subsets length does not equal C(v,k)")
    vertices: list[tuple[int, ...]] = []
    for index, raw in enumerate(raw_vertices):
        if isinstance(raw, (str, bytes, bytearray)) or not isinstance(raw, Sequence):
            raise ValueError(f"canonical_vertex_subsets[{index}] must be a finite sequence")
        if len(raw) != k:
            raise ValueError(f"canonical_vertex_subsets[{index}] has the wrong subset size")
        points: list[int] = []
        for offset, point in enumerate(raw):
            if type(point) is not int:
                raise ValueError(
                    f"canonical_vertex_subsets[{index}][{offset}] must be a strict integer"
                )
            if not 0 <= point < v:
                raise ValueError(
                    f"canonical_vertex_subsets[{index}] contains an out-of-ground point"
                )
            points.append(point)
        subset = tuple(points)
        if tuple(sorted(subset)) != subset or len(set(subset)) != k:
            raise ValueError(
                f"canonical_vertex_subsets[{index}] is not a canonical k-subset"
            )
        vertices.append(subset)
    result = tuple(vertices)
    if len(set(result)) != n or set(result) != set(combinations(range(v), k)):
        raise ValueError("canonical_vertex_subsets is not a complete copy of J(v,k)")
    return result


def _canonical_ground_stars(
    evidence: Any,
    *,
    vertices: tuple[tuple[int, ...], ...],
    v: int,
    k: int,
    n: int,
) -> tuple[tuple[int, ...], ...]:
    raw_stars = _strict_sequence(evidence, "canonical_ground_stars")
    if len(raw_stars) != v:
        raise ValueError("canonical_ground_stars must contain exactly v stars")
    expected_size = comb(v - 1, k - 1)
    stars: list[tuple[int, ...]] = []
    for point, raw in enumerate(raw_stars):
        if isinstance(raw, (str, bytes, bytearray)) or not isinstance(raw, Sequence):
            raise ValueError(f"canonical_ground_stars[{point}] must be a finite sequence")
        indices: list[int] = []
        for offset, vertex in enumerate(raw):
            if type(vertex) is not int:
                raise ValueError(
                    f"canonical_ground_stars[{point}][{offset}] must be a strict integer"
                )
            if not 0 <= vertex < n:
                raise ValueError(
                    f"canonical_ground_stars[{point}] contains an out-of-range vertex"
                )
            indices.append(vertex)
        star = tuple(indices)
        if tuple(sorted(star)) != star or len(set(star)) != len(star):
            raise ValueError(f"canonical_ground_stars[{point}] is not canonical")
        if len(star) != expected_size:
            raise ValueError(
                f"canonical_ground_stars[{point}] has the wrong incidence size"
            )
        expected = tuple(
            index for index, subset in enumerate(vertices) if point in subset
        )
        if star != expected:
            raise ValueError(
                f"canonical_ground_stars[{point}] disagrees with canonical_vertex_subsets"
            )
        stars.append(star)
    if len(set(stars)) != v:
        raise ValueError("canonical_ground_stars does not distinguish every ground point")
    return tuple(stars)


def _induced_ground_generators(
    evidence: Any,
    *,
    v: int,
) -> tuple[tuple[int, ...], ...]:
    raw_generators = _strict_sequence(evidence, "induced_ground_generators")
    generators: list[tuple[int, ...]] = []
    for index, raw in enumerate(raw_generators):
        if isinstance(raw, (str, bytes, bytearray)) or not isinstance(raw, Sequence):
            raise ValueError(f"induced_ground_generators[{index}] must be a finite sequence")
        if len(raw) != v:
            raise ValueError(
                f"induced_ground_generators[{index}] has the wrong ground degree"
            )
        images: list[int] = []
        for offset, image in enumerate(raw):
            if type(image) is not int:
                raise ValueError(
                    f"induced_ground_generators[{index}][{offset}] must be a strict integer"
                )
            if not 0 <= image < v:
                raise ValueError(
                    f"induced_ground_generators[{index}] contains an out-of-ground image"
                )
            images.append(image)
        generator = tuple(images)
        if len(set(generator)) != v:
            raise ValueError(f"induced_ground_generators[{index}] is not a permutation")
        generators.append(generator)
    return tuple(generators)


def _power_of_two_upper_bound(work: int) -> float:
    if type(work) is not int or work < 1:
        raise ValueError("construction_work_bound must be a positive strict integer")
    power = 1 << (work - 1).bit_length()
    try:
        result = float(power)
    except OverflowError as exc:
        raise ValueError(
            "construction work exceeds the finite recurrence-cost range"
        ) from exc
    if not isfinite(result) or result < work:
        raise ValueError(
            "could not encode a finite conservative construction-cost bound"
        )
    return result


def _sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def bind_johnson_construction_cost(evidence: Any) -> JohnsonConstructionCostBinding:
    """Bind retained rev287 construction work into the rev291 cost contract.

    rev287 already emits the exact/canonical Johnson transport certificate and
    a deterministic ``construction_work_bound``. This adapter consumes only
    that retained certificate. It does not import or replay rev287 branch-only
    code and does not execute rev291. Instead it verifies the complete retained
    Johnson incidence structure and exact work formula, then exposes a finite
    power-of-two upper bound so the later recurrence handoff cannot silently
    account nonzero construction work as unit cost. The source reduction
    identity is preserved unchanged.
    """
    try:
        schema_version = _strict_int(evidence, "schema_version")
        status = str(_field(evidence, "status"))
        certified = _strict_bool(evidence, "certified")
        canonical = _strict_bool(evidence, "canonical")
        exact = _strict_bool(evidence, "exact")
        progress = _strict_bool(evidence, "progress_certified")
        solution_transport = _strict_bool(evidence, "solution_transport_certified")
        ambient_transport = _strict_bool(
            evidence, "ambient_membership_transport_certified"
        )
        complement = _strict_bool(evidence, "complement_ambiguity_handled")
        n = _strict_int(evidence, "source_action_degree")
        v = _strict_int(evidence, "johnson_ground_size")
        k = _strict_int(evidence, "johnson_subset_size")
        child = _strict_int(evidence, "child_ground_size")
        source_cost = _strict_cost(evidence, "multiplicative_cost")
        source_max_cost = _strict_cost(evidence, "max_multiplicative_cost")
        reduction_identity = str(_field(evidence, "reduction_identity"))
        work = _strict_int(evidence, "construction_work_bound")
    except (TypeError, ValueError) as exc:
        return _fail(str(exc))

    if (
        schema_version != SOURCE_SCHEMA_VERSION
        or status != SOURCE_STATUS
        or not certified
    ):
        return _fail(
            "source evidence is not a certified rev287 Johnson-ground reduction"
        )
    if not (
        canonical
        and exact
        and progress
        and solution_transport
        and ambient_transport
        and complement
    ):
        return _fail(
            "source evidence does not retain every exact/canonical transport obligation"
        )
    if v < 4 or not 2 <= k <= v - 2:
        return _fail("source Johnson parameters are malformed")
    if comb(v, k) != n or n <= v or child != v:
        return _fail(
            "source action/child measures do not certify C(v,k) -> v progress"
        )
    if source_cost > source_max_cost:
        return _fail("source multiplicative cost exceeds its source upper bound")
    if not _SHA256_RE.fullmatch(reduction_identity):
        return _fail("source reduction identity is not a canonical sha256 digest")

    try:
        vertices = _canonical_vertex_subsets(evidence, v=v, k=k, n=n)
        _canonical_ground_stars(
            evidence,
            vertices=vertices,
            v=v,
            k=k,
            n=n,
        )
        generators = _induced_ground_generators(evidence, v=v)
    except ValueError as exc:
        return _fail(str(exc))

    expected_work = (
        (2 + 2 * len(generators)) * n * k
        + len(generators) * n
        + v
    )
    if work != expected_work:
        return _fail(
            "construction_work_bound does not match the rev287 deterministic work formula"
        )

    try:
        work_cost_bound = _power_of_two_upper_bound(work)
    except ValueError as exc:
        return _fail(str(exc))
    final_cost_bound = max(source_max_cost, work_cost_bound)
    if not isfinite(final_cost_bound):
        return _fail("combined construction-cost bound is not finite")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "source_schema_version": schema_version,
        "source_status": status,
        "source_reduction_identity": reduction_identity,
        "source_action_degree": n,
        "johnson_ground_size": v,
        "johnson_subset_size": k,
        "child_ground_size": child,
        "source_construction_work_bound": work,
        "source_max_multiplicative_cost": source_max_cost,
        "conservative_construction_cost_bound": work_cost_bound,
        "handoff_max_multiplicative_cost": final_cost_bound,
    }
    binding_identity = _sha256(payload)

    return JohnsonConstructionCostBinding(
        SCHEMA_VERSION,
        SOURCE_STATUS,
        True,
        canonical,
        exact,
        progress,
        solution_transport,
        ambient_transport,
        complement,
        n,
        v,
        k,
        child,
        final_cost_bound,
        final_cost_bound,
        reduction_identity,
        work,
        work_cost_bound,
        binding_identity,
        "rev287 retained incidence structure and deterministic work formula are valid; construction work is conservatively charged before rev291 recurrence handoff without changing the source reduction identity",
    )


def replay_johnson_construction_cost_binding(
    binding: JohnsonConstructionCostBinding,
    evidence: Any,
) -> bool:
    if not isinstance(binding, JohnsonConstructionCostBinding) or not binding.certified:
        return False
    replay = bind_johnson_construction_cost(evidence)
    return bool(
        replay.certified
        and replay == binding
        and replay.cost_binding_identity == binding.cost_binding_identity
    )


__all__ = [
    "JohnsonConstructionCostBinding",
    "bind_johnson_construction_cost",
    "replay_johnson_construction_cost_binding",
]
