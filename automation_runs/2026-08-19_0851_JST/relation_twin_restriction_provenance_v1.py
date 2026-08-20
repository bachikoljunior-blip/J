from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from bipartite_reduce_part2_by_color_v1 import (
    ReducePart2ByColorCertificate,
    reduce_part2_by_color_certificate,
)
from uniform_neighborhood_relation_provenance_v1 import (
    UniformNeighborhoodRelation,
    derive_uniform_neighborhood_relation,
)

Subset = tuple[int, ...]


@dataclass(frozen=True)
class RelationTwinRestriction:
    status: str
    relation: UniformNeighborhoodRelation
    twin_classes: tuple[tuple[int, ...], ...]
    twin_class_size_inventory: tuple[int, ...]
    large_twin_class: tuple[int, ...]
    complement: tuple[int, ...]
    restriction: ReducePart2ByColorCertificate | None
    selected_part_index: int | None
    selected_part: tuple[int, ...]
    provenance_verified: bool
    exact: bool
    reason: str


@dataclass(frozen=True)
class PairedRelationTwinRestriction:
    status: str
    source: RelationTwinRestriction
    target: RelationTwinRestriction
    selected_large_class_size: int | None
    restriction_pair_complete: bool
    provenance_verified: bool
    exact: bool
    reason: str


def _relation_color_map(
    right_size: int,
    arity: int,
    classes: tuple[tuple[int, tuple[Subset, ...]], ...],
) -> dict[Subset, int]:
    expected = set(combinations(range(right_size), arity))
    colors: dict[Subset, int] = {}
    for color, subsets in classes:
        for subset in subsets:
            normalized = tuple(sorted(int(x) for x in subset))
            if len(normalized) != arity or len(set(normalized)) != arity:
                raise ValueError("relation class contains a non-distinct or wrong-arity subset")
            if any(not 0 <= x < right_size for x in normalized):
                raise ValueError("relation class contains an out-of-range point")
            if normalized in colors:
                raise ValueError("relation classes overlap")
            colors[normalized] = int(color)
    if set(colors) != expected:
        raise ValueError("relation classes must color every distinct right-ground subset exactly once")
    return colors


def exact_symmetric_relation_twin_classes(
    right_size: int,
    relation_arity: int,
    relation_classes: tuple[tuple[int, tuple[Subset, ...]], ...],
) -> tuple[tuple[int, ...], ...]:
    """Return transposition-twin classes of a symmetric distinct-tuple relation.

    Points x,y are twins iff the transposition (x y) preserves every relation
    color.  For a symmetric d-ary relation it is enough to compare colors of
    T∪{x} and T∪{y} for every (d-1)-subset T disjoint from {x,y}.  Repeated
    tuples have the uniform gray color in the Proposition 5.7 construction and
    therefore add no further condition.
    """
    n = int(right_size)
    d = int(relation_arity)
    if n < 2 or not 1 <= d < n:
        raise ValueError("relation twins require right_size>=2 and 1<=arity<right_size")
    colors = _relation_color_map(n, d, relation_classes)

    twin = [[False] * n for _ in range(n)]
    for x in range(n):
        twin[x][x] = True
    for x in range(n):
        for y in range(x + 1, n):
            rest = [z for z in range(n) if z not in (x, y)]
            same = True
            for context in combinations(rest, d - 1):
                sx = tuple(sorted((*context, x)))
                sy = tuple(sorted((*context, y)))
                if colors[sx] != colors[sy]:
                    same = False
                    break
            twin[x][y] = twin[y][x] = same

    unseen = set(range(n))
    classes = []
    while unseen:
        x = min(unseen)
        cell = tuple(y for y in range(n) if twin[x][y])
        cell_set = set(cell)
        # A transposition-twin relation is an equivalence relation.  Verify that
        # explicitly before using it as a canonical partition.
        if any(not twin[y][z] for y in cell for z in cell):
            raise ValueError("computed relation-twin predicate is not transitive")
        if any(twin[y][z] for y in cell for z in range(n) if z not in cell_set):
            raise ValueError("computed relation-twin classes are not maximal")
        classes.append(cell)
        unseen -= cell_set
    return tuple(sorted(classes, key=lambda cell: (len(cell), cell)))


def derive_relation_twin_restriction(
    left_size: int,
    right_size: int,
    edges: Iterable[tuple[int, int]],
    *,
    alpha: float = 0.75,
    max_subsets: int = 200000,
) -> RelationTwinRestriction:
    """Derive the unique >half relation-twin class and compose rev200 exactly."""
    edge_tuple = tuple(edges)
    relation = derive_uniform_neighborhood_relation(
        left_size, right_size, edge_tuple, max_subsets=max_subsets
    )
    empty_classes: tuple[tuple[int, ...], ...] = ()
    if relation.status != "nonconstant_containment_relation":
        return RelationTwinRestriction(
            "relation_twin_requires_nonconstant_containment_relation",
            relation,
            empty_classes,
            (),
            (),
            (),
            None,
            None,
            (),
            relation.exact,
            True,
            "the exact local outcome is not the nonconstant containment relation required by this child",
        )

    assert relation.relation_arity is not None
    classes = exact_symmetric_relation_twin_classes(
        right_size, relation.relation_arity, relation.relation_classes
    )
    sizes = tuple(sorted(len(cell) for cell in classes))
    large = tuple(cell for cell in classes if 2 * len(cell) > right_size)
    if not large:
        return RelationTwinRestriction(
            "relation_twin_no_large_class",
            relation,
            classes,
            sizes,
            (),
            (),
            None,
            None,
            (),
            True,
            True,
            "no relation-twin class contains more than half of the right ground; continue to Design/coherent descent",
        )
    if len(large) != 1:
        return RelationTwinRestriction(
            "relation_twin_large_class_invariant_violation",
            relation,
            classes,
            sizes,
            (),
            (),
            None,
            None,
            (),
            False,
            True,
            "more than one disjoint relation-twin class was reported as larger than half",
        )

    large_class = large[0]
    large_set = set(large_class)
    complement = tuple(x for x in range(right_size) if x not in large_set)
    cert = reduce_part2_by_color_certificate(
        left_size,
        right_size,
        edge_tuple,
        large_class,
        complement,
        alpha=alpha,
    )
    if cert.status != "certified_reduce_part2_by_color":
        return RelationTwinRestriction(
            "relation_twin_restriction_no_progress",
            relation,
            classes,
            sizes,
            large_class,
            complement,
            cert,
            None,
            (),
            True,
            True,
            "the unique canonical large relation-twin class was found, but rev200 could not certify a proper restricted child",
        )
    return RelationTwinRestriction(
        "certified_relation_twin_restriction",
        relation,
        classes,
        sizes,
        large_class,
        complement,
        cert,
        cert.selected_part_index,
        cert.selected_part,
        True,
        True,
        "the unique >half relation-twin class is canonical and rev200 certifies the selected proper right restriction",
    )


def certify_paired_relation_twin_restriction(
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    alpha: float = 0.75,
    max_subsets: int = 200000,
) -> PairedRelationTwinRestriction:
    """Pair the unique large relation-twin restriction across source and target."""
    src = derive_relation_twin_restriction(
        left_size, right_size, tuple(source_edges), alpha=alpha, max_subsets=max_subsets
    )
    dst = derive_relation_twin_restriction(
        left_size, right_size, tuple(target_edges), alpha=alpha, max_subsets=max_subsets
    )
    if src.status != dst.status:
        return PairedRelationTwinRestriction(
            "paired_relation_twin_status_mismatch",
            src,
            dst,
            None,
            False,
            False,
            True,
            "a right-ground isomorphism must preserve the exact relation-twin outcome type",
        )
    if src.twin_class_size_inventory != dst.twin_class_size_inventory:
        return PairedRelationTwinRestriction(
            "paired_relation_twin_inventory_mismatch",
            src,
            dst,
            None,
            False,
            False,
            True,
            "a right-ground isomorphism must preserve every exact relation-twin class size",
        )
    if src.status != "certified_relation_twin_restriction":
        return PairedRelationTwinRestriction(
            "paired_relation_twin_no_restriction_progress",
            src,
            dst,
            None,
            False,
            src.provenance_verified and dst.provenance_verified,
            True,
            "the paired exact relation-twin outcome is recorded but has no unique large-class restriction",
        )

    assert src.restriction is not None and dst.restriction is not None
    invariants_src = (
        len(src.large_twin_class),
        src.selected_part_index,
        len(src.selected_part),
        src.restriction.part0_largest_left_twin_class,
        src.restriction.part1_largest_left_twin_class,
        src.restriction.selected_alpha_shrink,
    )
    invariants_dst = (
        len(dst.large_twin_class),
        dst.selected_part_index,
        len(dst.selected_part),
        dst.restriction.part0_largest_left_twin_class,
        dst.restriction.part1_largest_left_twin_class,
        dst.restriction.selected_alpha_shrink,
    )
    if invariants_src != invariants_dst:
        return PairedRelationTwinRestriction(
            "paired_relation_twin_restriction_invariant_mismatch",
            src,
            dst,
            None,
            False,
            False,
            True,
            "the unique large classes correspond, but exact rev200 selection invariants differ",
        )
    return PairedRelationTwinRestriction(
        "paired_relation_twin_restriction",
        src,
        dst,
        len(src.large_twin_class),
        True,
        True,
        True,
        "every right-ground isomorphism maps the unique large relation-twin class to its target counterpart; the paired proper restriction is complete",
    )
