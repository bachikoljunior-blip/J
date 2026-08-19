from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Hashable, Iterable

from design_codegree_refinement import refine_design_codegrees
from master_canonical_reduction import reduce_canonical_pair_structure


@dataclass(frozen=True)
class UniformNeighborhoodRelationDescent:
    status: str
    right_size: int
    arity: int
    decisive_subset_size: int | None
    right_cells: tuple[tuple[int, ...], ...]
    largest_cell: int
    significant_split: bool
    pair_reduction_status: str | None
    johnson_ground_size: int | None
    johnson_subset_size: int | None
    exact: bool
    reason: str


def _canonical_rows(
    right_size: int,
    arity: int,
    coordinates: Iterable[Iterable[int]],
    colors: Iterable[Hashable],
):
    v = int(right_size)
    t = int(arity)
    if v < 2 or not 2 <= t <= v:
        raise ValueError("derived right relation requires right_size>=2 and 2<=arity<=right_size")
    coords = tuple(tuple(sorted(int(x) for x in T)) for T in coordinates)
    palette = tuple(colors)
    if len(coords) != len(palette):
        raise ValueError("coordinate/color length mismatch")
    if any(len(T) != t or len(set(T)) != t for T in coords):
        raise ValueError("every coordinate must be a t-subset without repetitions")
    if any(x < 0 or x >= v for T in coords for x in T):
        raise ValueError("coordinate point outside right ground")
    expected = tuple(combinations(range(v), t))
    if len(coords) != len(expected) or set(coords) != set(expected):
        raise ValueError("coordinates must contain every t-subset exactly once")
    if len(set(coords)) != len(coords):
        raise ValueError("coordinates must not contain duplicates")
    by_coord = {T: color for T, color in zip(coords, palette)}
    return tuple((T, by_coord[T]) for T in expected)


def _integer_pair_weights(rows):
    """Canonically encode arbitrary hashable pair colors for the integer reducer."""
    unique = []
    seen = set()
    for _, value in rows:
        try:
            if value not in seen:
                seen.add(value)
                unique.append(value)
        except TypeError as exc:
            raise ValueError("relation colors must be hashable") from exc
    keyed = sorted(
        ((type(value).__module__, type(value).__qualname__, repr(value)), value)
        for value in unique
    )
    for i in range(1, len(keyed)):
        if keyed[i - 1][0] == keyed[i][0] and keyed[i - 1][1] != keyed[i][1]:
            raise ValueError("distinct pair colors have indistinguishable canonical repr keys")
    ids = {value: i for i, (_, value) in enumerate(keyed)}
    return tuple((tuple(U), ids[value]) for U, value in rows)


def descend_uniform_neighborhood_test_relation(
    right_size: int,
    arity: int,
    coordinates: Iterable[Iterable[int]],
    colors: Iterable[Hashable],
    *,
    max_class_fraction: float = 0.9,
    max_subsets: int = 200000,
    max_johnson_nodes: int = 500000,
) -> UniformNeighborhoodRelationDescent:
    """Exact rev205 bridge from rev204's V2 relation into existing split/Johnson machinery.

    The input must be the complete controlled-arity colored subset relation produced
    by ``build_uniform_neighborhood_hypergraph``. The routine first refuses a
    constant relation. For arity two it hands the complete weighted pair relation
    directly to the existing coherent/Johnson reducer. For higher arity it runs
    exact codegree/incidence refinement. A significant point split is accepted as
    strict right-ground progress. If the first nonconstant lower relation is a pair
    relation, that exact pair relation is handed to the same reducer. Higher-arity
    homogeneous structure is deliberately preserved as an unresolved Design-Lemma
    obligation rather than being called solved.

    This is a reduction bridge, not the full corrected Split-or-Johnson theorem.
    """
    if not (0.0 < max_class_fraction < 1.0):
        raise ValueError("max_class_fraction must lie in (0,1)")
    if max_subsets < 1 or max_johnson_nodes < 1:
        raise ValueError("search/subset limits must be positive")

    rows = _canonical_rows(right_size, arity, coordinates, colors)
    v = int(right_size)
    t = int(arity)
    palette = tuple(value for _, value in rows)
    try:
        color_count = len(set(palette))
    except TypeError as exc:
        raise ValueError("relation colors must be hashable") from exc
    if color_count <= 1:
        return UniformNeighborhoodRelationDescent(
            "constant_right_relation_unresolved", v, t, None,
            (tuple(range(v)),), v, False, None, None, None, True,
            "the controlled-arity right-ground relation is constant; rev204 correctly leaves the design-bound case unresolved",
        )

    if t == 2:
        pair = reduce_canonical_pair_structure(
            v,
            _integer_pair_weights(rows),
            max_class_fraction=max_class_fraction,
            max_johnson_nodes=max_johnson_nodes,
        )
        if pair.status == "certified_coherent_point_split" and pair.progress_verified:
            largest = max(map(len, pair.split_classes), default=v)
            return UniformNeighborhoodRelationDescent(
                "certified_right_pair_coherent_split", v, t, 2,
                tuple(pair.split_classes), largest, True, pair.status,
                None, None, True,
                "the exact rev204 pair relation yields a canonical significant point split via the existing coherent reducer",
            )
        if pair.status == "exact_johnson_ground_reduction_available" and pair.progress_verified:
            return UniformNeighborhoodRelationDescent(
                "certified_right_pair_johnson_reduction", v, t, 2,
                tuple(pair.split_classes), max(map(len, pair.split_classes), default=v),
                False, pair.status, int(pair.johnson_ground_size), int(pair.johnson_subset_size), True,
                "the exact rev204 pair relation is a certified Johnson distance scheme on a strictly smaller ground",
            )
        return UniformNeighborhoodRelationDescent(
            "right_pair_relation_unresolved", v, t, 2,
            tuple(pair.split_classes), max(map(len, pair.split_classes), default=v),
            False, pair.status, pair.johnson_ground_size, pair.johnson_subset_size, True,
            "the exact pair relation is stable but neither a certified significant split nor a verified Johnson ground reduction",
        )

    design = refine_design_codegrees(
        v,
        rows,
        max_class_fraction=max_class_fraction,
        max_subsets=max_subsets,
    )
    if design.status == "undetermined_subset_limit":
        return UniformNeighborhoodRelationDescent(
            "undetermined_right_design_subset_limit", v, t, design.decisive_subset_size,
            (), v, False, None, None, None, False,
            "the exact codegree descent exceeded the configured subset enumeration limit",
        )
    if design.significant_split:
        return UniformNeighborhoodRelationDescent(
            "certified_right_design_codegree_split", v, t, design.decisive_subset_size,
            tuple(design.color_classes), design.largest_class, True,
            None, None, None, True,
            "exact lower-arity codegrees and incidence refinement yield a canonical alpha-bounded split of V2",
        )

    if design.decisive_subset_size == 2 and design.subset_signatures:
        pair_rows = tuple((tuple(U), tuple(signature)) for U, signature in design.subset_signatures)
        pair = reduce_canonical_pair_structure(
            v,
            _integer_pair_weights(pair_rows),
            max_class_fraction=max_class_fraction,
            max_johnson_nodes=max_johnson_nodes,
        )
        if pair.status == "certified_coherent_point_split" and pair.progress_verified:
            largest = max(map(len, pair.split_classes), default=v)
            return UniformNeighborhoodRelationDescent(
                "certified_right_codegree_pair_coherent_split", v, t, 2,
                tuple(pair.split_classes), largest, True, pair.status,
                None, None, True,
                "the first nonconstant exact lower relation is a pair relation and its coherent closure significantly splits V2",
            )
        if pair.status == "exact_johnson_ground_reduction_available" and pair.progress_verified:
            return UniformNeighborhoodRelationDescent(
                "certified_right_codegree_pair_johnson_reduction", v, t, 2,
                tuple(pair.split_classes), max(map(len, pair.split_classes), default=v),
                False, pair.status, int(pair.johnson_ground_size), int(pair.johnson_subset_size), True,
                "the first nonconstant exact lower relation is a certified Johnson distance scheme on a smaller ground",
            )
        return UniformNeighborhoodRelationDescent(
            "right_codegree_pair_unresolved", v, t, 2,
            tuple(pair.split_classes), max(map(len, pair.split_classes), default=v),
            False, pair.status, pair.johnson_ground_size, pair.johnson_subset_size, True,
            "the exact lower-arity pair relation remains a non-Johnson coherent obstruction",
        )

    return UniformNeighborhoodRelationDescent(
        "right_higher_arity_design_unresolved", v, t, design.decisive_subset_size,
        tuple(design.color_classes), design.largest_class, False,
        None, None, None, True,
        (
            "the rev204 relation is nonconstant but existing exact codegree/incidence machinery neither significantly splits V2 nor reaches a certified pair/Johnson reduction; "
            "the remaining higher-arity homogeneous Design/coherent conclusion is the next W1R-H6 leaf"
        ),
    )
