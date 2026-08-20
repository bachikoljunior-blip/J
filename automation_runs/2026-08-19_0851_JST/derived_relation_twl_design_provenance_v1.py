from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from colored_subset_exact_twl_design_v1 import (
    PairedExactTWLDesignFamily,
    paired_exact_twl_design_witness_families,
)
from relation_twin_restriction_provenance_v1 import (
    RelationTwinRestriction,
    derive_relation_twin_restriction,
)


@dataclass(frozen=True)
class DerivedRelationTWLDesignProvenance:
    status: str
    source_relation_twin: RelationTwinRestriction
    target_relation_twin: RelationTwinRestriction
    source_direct_partition: tuple[tuple[int, ...], ...]
    target_direct_partition: tuple[tuple[int, ...], ...]
    paired_design_family: PairedExactTWLDesignFamily | None
    parent_relation_provenance_verified: bool
    structural_family_complete: bool
    exact_empty: bool
    exact: bool
    reason: str


def _unary_relation_partition(
    restriction: RelationTwinRestriction,
) -> tuple[tuple[int, ...], ...]:
    """Return unary color cells in exact relation-color order, not label order."""
    relation = restriction.relation
    if relation.relation_arity != 1:
        raise ValueError("unary relation partition requires arity one")
    cells = []
    seen = set()
    for _color, subsets in relation.relation_classes:
        cell = tuple(sorted(int(subset[0]) for subset in subsets))
        if any(len(subset) != 1 for subset in subsets):
            raise ValueError("unary relation class contains a non-singleton coordinate")
        if not cell:
            raise ValueError("unary relation classes must be nonempty")
        if seen.intersection(cell):
            raise ValueError("unary relation classes overlap")
        seen.update(cell)
        cells.append(cell)
    if seen != set(range(relation.right_size)):
        raise ValueError("unary relation classes must cover the right ground")
    return tuple(cells)


def _relation_palette(restriction: RelationTwinRestriction) -> tuple[int, ...]:
    relation = restriction.relation
    if relation.relation_arity is None:
        raise ValueError("derived relation has no arity")
    colors = {}
    for color, subsets in relation.relation_classes:
        for subset in subsets:
            key = tuple(sorted(int(x) for x in subset))
            if key in colors:
                raise ValueError("derived relation classes overlap")
            colors[key] = int(color)
    coords = tuple(combinations(range(relation.right_size), relation.relation_arity))
    if set(colors) != set(coords):
        raise ValueError("derived relation classes do not color every subset")
    return tuple(colors[subset] for subset in coords)


def certify_paired_parent_derived_twl_design(
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    alpha: float = 2 / 3,
    max_subsets: int = 200000,
    max_states: int = 200000,
    max_tuple_states: int = 250000,
    max_rounds: int | None = None,
    max_work_units: int = 500000000,
) -> DerivedRelationTWLDesignProvenance:
    """Wire the parent-derived relation into exact k-WL/Design machinery.

    The wrapper recomputes the rev202 relation and rev203 relation-twin boundary
    from each parent incidence graph.  Only the no-large-relation-twin case may
    enter the exact rev193 k-WL/Design family.  Thus the Design input is data with
    mechanically checked parent provenance, not a caller assertion.

    Arity one is handled directly: its relation-twin color classes already form a
    1/2-bounded canonical partition.  For arity at least two, the complete first
    successful <=k-1 individualization family is retained.  No witness
    representative, ambient transporter, or final string-isomorphism coset is
    selected here.
    """
    src = derive_relation_twin_restriction(
        left_size,
        right_size,
        tuple(source_edges),
        alpha=alpha,
        max_subsets=max_subsets,
    )
    dst = derive_relation_twin_restriction(
        left_size,
        right_size,
        tuple(target_edges),
        alpha=alpha,
        max_subsets=max_subsets,
    )
    empty_partition: tuple[tuple[int, ...], ...] = ()

    if src.status != dst.status:
        return DerivedRelationTWLDesignProvenance(
            "exact_empty_parent_derived_relation_status_mismatch",
            src,
            dst,
            empty_partition,
            empty_partition,
            None,
            False,
            False,
            True,
            True,
            "a parent incidence isomorphism must preserve the exact relation-twin outcome type",
        )
    if src.status != "relation_twin_no_large_class":
        return DerivedRelationTWLDesignProvenance(
            "parent_derived_twl_design_not_applicable",
            src,
            dst,
            empty_partition,
            empty_partition,
            None,
            src.provenance_verified and dst.provenance_verified,
            False,
            False,
            True,
            "this child applies only after the unique-large-relation-twin restriction case has been excluded",
        )

    src_relation = src.relation
    dst_relation = dst.relation
    invariants_src = (
        src_relation.relation_arity,
        src_relation.relation_inventory,
        src.twin_class_size_inventory,
    )
    invariants_dst = (
        dst_relation.relation_arity,
        dst_relation.relation_inventory,
        dst.twin_class_size_inventory,
    )
    if invariants_src != invariants_dst:
        return DerivedRelationTWLDesignProvenance(
            "exact_empty_parent_derived_relation_invariant_mismatch",
            src,
            dst,
            empty_partition,
            empty_partition,
            None,
            False,
            False,
            True,
            True,
            "relation arity, color multiplicities, or exact relation-twin class sizes differ",
        )

    arity = src_relation.relation_arity
    assert arity is not None
    if arity == 1:
        # Unary twin classes are the relation color classes, but rev203 stores
        # them in a label-dependent display order.  Reconstruct cells in exact
        # integer relation-color order so source cell i and target cell i have
        # a mechanically justified correspondence even when sizes tie.
        src_partition = _unary_relation_partition(src)
        dst_partition = _unary_relation_partition(dst)
        if tuple(map(len, src_partition)) != tuple(map(len, dst_partition)):
            return DerivedRelationTWLDesignProvenance(
                "exact_empty_parent_derived_point_partition_mismatch",
                src,
                dst,
                src_partition,
                dst_partition,
                None,
                False,
                False,
                True,
                True,
                "the exact arity-one relation-color-ordered partitions have different corresponding cell sizes",
            )
        if max(map(len, src_partition), default=0) > alpha * right_size + 1e-12:
            return DerivedRelationTWLDesignProvenance(
                "parent_derived_point_partition_alpha_invariant_violation",
                src,
                dst,
                src_partition,
                dst_partition,
                None,
                False,
                False,
                False,
                True,
                "no-large-twin arity-one relation unexpectedly failed the alpha bound",
            )
        return DerivedRelationTWLDesignProvenance(
            "certified_paired_parent_derived_point_partition",
            src,
            dst,
            src_partition,
            dst_partition,
            None,
            True,
            True,
            False,
            True,
            "the exact parent-derived unary relation supplies corresponding source/target cells in relation-color order and an alpha-bounded partition",
        )

    source_palette = _relation_palette(src)
    target_palette = _relation_palette(dst)
    paired = paired_exact_twl_design_witness_families(
        right_size,
        arity,
        source_palette,
        target_palette,
        alpha=alpha,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_rounds=max_rounds,
        max_work_units=max_work_units,
    )
    if paired.status == "exact_empty_paired_twl_design_invariant":
        return DerivedRelationTWLDesignProvenance(
            "exact_empty_parent_derived_twl_design_invariant",
            src,
            dst,
            empty_partition,
            empty_partition,
            paired,
            True,
            True,
            True,
            True,
            "the parent-derived relations reach incompatible complete first-successful-level exact k-WL Design invariants",
        )
    if paired.status != "certified_paired_exact_twl_design_family":
        return DerivedRelationTWLDesignProvenance(
            "undetermined_parent_derived_twl_design_family",
            src,
            dst,
            empty_partition,
            empty_partition,
            paired,
            True,
            False,
            False,
            paired.source.exact and paired.target.exact,
            "the parent provenance is exact, but the exact k-WL/Design family did not pass every theorem/resource/mechanical gate",
        )
    return DerivedRelationTWLDesignProvenance(
        "certified_paired_parent_derived_twl_design_family",
        src,
        dst,
        empty_partition,
        empty_partition,
        paired,
        True,
        True,
        False,
        True,
        "the complete paired exact k-WL/Design witness family is mechanically derived from the parent incidence relation; ambient witness transport and full-string integration remain unresolved",
    )
