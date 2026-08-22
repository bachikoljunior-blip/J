from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import combinations
from math import comb

from corrected_soj_johnson_construction_cost_binding_v1 import (
    bind_johnson_construction_cost,
    replay_johnson_construction_cost_binding,
)


@dataclass(frozen=True)
class Evidence:
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
    canonical_vertex_subsets: tuple[tuple[int, ...], ...]
    canonical_ground_stars: tuple[tuple[int, ...], ...]
    induced_ground_generators: tuple[tuple[int, ...], ...]
    construction_work_bound: int
    reason: str = "fixture"


def fixture(*, v: int = 5, k: int = 2) -> Evidence:
    vertices = tuple(combinations(range(v), k))
    n = comb(v, k)
    stars = tuple(
        tuple(index for index, subset in enumerate(vertices) if point in subset)
        for point in range(v)
    )
    identity = tuple(range(v))
    cycle = tuple((point + 1) % v for point in range(v))
    generators = (identity, cycle)
    work = (
        (2 + 2 * len(generators)) * n * k
        + len(generators) * n
        + v
    )
    return Evidence(
        1,
        "certified_johnson_ground_relational_reduction",
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        n,
        v,
        k,
        v,
        1.0,
        1.0,
        "sha256:" + "a" * 64,
        vertices,
        stars,
        generators,
        work,
    )


def test_success_and_replay() -> None:
    source = fixture()
    bound = bind_johnson_construction_cost(source)
    assert bound.certified, bound.reason
    assert bound.source_construction_work_bound == 145
    assert bound.conservative_construction_cost_bound == 256.0
    assert bound.multiplicative_cost == 256.0
    assert bound.max_multiplicative_cost == 256.0
    assert bound.reduction_identity == source.reduction_identity
    assert bound.cost_binding_identity.startswith("sha256:")
    assert replay_johnson_construction_cost_binding(bound, source)


def test_source_larger_bound_is_preserved() -> None:
    source = replace(
        fixture(),
        multiplicative_cost=300.0,
        max_multiplicative_cost=512.0,
    )
    bound = bind_johnson_construction_cost(source)
    assert bound.certified, bound.reason
    assert bound.max_multiplicative_cost == 512.0


def test_bad_work_formula_fails_closed() -> None:
    source = fixture()
    bound = bind_johnson_construction_cost(
        replace(
            source,
            construction_work_bound=source.construction_work_bound - 1,
        )
    )
    assert not bound.certified
    assert "work formula" in bound.reason


def test_incomplete_johnson_vertices_fail_closed() -> None:
    source = fixture()
    vertices = (
        source.canonical_vertex_subsets[:-1]
        + (source.canonical_vertex_subsets[-2],)
    )
    bound = bind_johnson_construction_cost(
        replace(source, canonical_vertex_subsets=vertices)
    )
    assert not bound.certified


def test_star_mismatch_fails_closed() -> None:
    source = fixture()
    stars = list(source.canonical_ground_stars)
    stars[0], stars[1] = stars[1], stars[0]
    bound = bind_johnson_construction_cost(
        replace(source, canonical_ground_stars=tuple(stars))
    )
    assert not bound.certified
    assert "disagrees" in bound.reason


def test_nonpermutation_ground_generator_fails_closed() -> None:
    source = fixture()
    generators = list(source.induced_ground_generators)
    generators[0] = (0, 0, 1, 2, 3)
    bound = bind_johnson_construction_cost(
        replace(source, induced_ground_generators=tuple(generators))
    )
    assert not bound.certified
    assert "not a permutation" in bound.reason


def test_transport_flag_failure_fails_closed() -> None:
    source = fixture()
    bound = bind_johnson_construction_cost(
        replace(source, solution_transport_certified=False)
    )
    assert not bound.certified
    assert "transport obligation" in bound.reason


def test_wrong_source_degree_fails_closed() -> None:
    source = fixture()
    bound = bind_johnson_construction_cost(
        replace(source, source_action_degree=source.source_action_degree + 1)
    )
    assert not bound.certified


def test_bad_reduction_identity_fails_closed() -> None:
    source = fixture()
    bound = bind_johnson_construction_cost(
        replace(source, reduction_identity="not-a-digest")
    )
    assert not bound.certified


def test_source_cost_bound_failure_fails_closed() -> None:
    source = fixture()
    bound = bind_johnson_construction_cost(
        replace(
            source,
            multiplicative_cost=2.0,
            max_multiplicative_cost=1.0,
        )
    )
    assert not bound.certified


def test_wrong_schema_fails_closed() -> None:
    source = fixture()
    bound = bind_johnson_construction_cost(replace(source, schema_version=2))
    assert not bound.certified


def test_wrong_child_measure_fails_closed() -> None:
    source = fixture()
    bound = bind_johnson_construction_cost(
        replace(source, child_ground_size=source.child_ground_size + 1)
    )
    assert not bound.certified


if __name__ == "__main__":
    tests = [
        test_success_and_replay,
        test_source_larger_bound_is_preserved,
        test_bad_work_formula_fails_closed,
        test_incomplete_johnson_vertices_fail_closed,
        test_star_mismatch_fails_closed,
        test_nonpermutation_ground_generator_fails_closed,
        test_transport_flag_failure_fails_closed,
        test_wrong_source_degree_fails_closed,
        test_bad_reduction_identity_fails_closed,
        test_source_cost_bound_failure_fails_closed,
        test_wrong_schema_fails_closed,
        test_wrong_child_measure_fails_closed,
    ]
    for test in tests:
        test()
    print(f"rev292 focused regression: {len(tests)}/{len(tests)} passed")
