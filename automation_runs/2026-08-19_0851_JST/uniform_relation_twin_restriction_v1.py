from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from bipartite_reduce_part2_by_color_v1 import (
    ReducePart2ByColorCertificate,
    reduce_part2_by_color_certificate,
)
from colored_subset_symmetry_defect_v1 import (
    SymmetryDefectCertificate,
    exact_colored_subset_symmetry_defect,
)
from uniform_neighborhood_relation_provenance_v1 import (
    PairedUniformNeighborhoodProvenance,
    UniformNeighborhoodRelation,
    certify_paired_uniform_neighborhood_provenance,
)


@dataclass(frozen=True)
class PairedUniformRelationTwinRestriction:
    status: str
    provenance: PairedUniformNeighborhoodProvenance
    source_symmetry: SymmetryDefectCertificate | None
    target_symmetry: SymmetryDefectCertificate | None
    source_restriction: ReducePart2ByColorCertificate | None
    target_restriction: ReducePart2ByColorCertificate | None
    dominant_twin_size: int | None
    selected_part_index: int | None
    selected_part_size: int | None
    relation_twin_provenance_verified: bool
    restriction_pair_complete: bool
    exact_empty: bool
    exact: bool
    reason: str


def _relation_palette(relation: UniformNeighborhoodRelation) -> tuple[int, ...]:
    t = relation.relation_arity
    if t is None:
        return ()
    color_of = {
        tuple(subset): int(color)
        for color, subsets in relation.relation_classes
        for subset in subsets
    }
    coords = tuple(combinations(range(relation.right_size), t))
    if set(color_of) != set(coords):
        raise AssertionError("uniform-neighborhood relation classes do not cover every t-subset exactly")
    return tuple(color_of[S] for S in coords)


def _size_profile(cert: SymmetryDefectCertificate) -> tuple[int, ...]:
    return tuple(sorted(map(len, cert.twin_classes)))


def _largest_class(cert: SymmetryDefectCertificate) -> tuple[int, ...]:
    return max(cert.twin_classes, key=lambda cell: (len(cell), tuple(-x for x in cell)))


def certify_paired_uniform_relation_twin_restriction(
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    relation_alpha: float = 0.75,
    restriction_alpha: float = 0.75,
    max_subsets: int = 200000,
) -> PairedUniformRelationTwinRestriction:
    """H6-R3b2: turn a large exact relation-twin class into a paired restriction.

    rev202 first derives the theorem-faithful uniform-neighborhood containment
    relation and requires the original left neighborhoods to be pairwise distinct.
    On a paired nonconstant relation, rev203 computes exact transposition-twin
    classes. If the Design symmetry-defect gate fails for alpha>=1/2, there is a
    unique dominant twin class larger than alpha*|V2|. That class and its
    complement are therefore a canonical ordered proper right partition.

    The partition is fed back to rev200's exact Exercise-5.5 restriction on the
    *original* bipartite incidence state. Because the rev202 relation path already
    certified full-left twin-freeness, failure of rev200's theorem precondition is
    treated as an implementation invariant violation rather than silently ignored.

    If the relation symmetry gate already holds, this routine deliberately does
    not restrict: the next branch is exact WL/Design/coherent descent. Johnson
    outcomes likewise bypass this relation-twin leaf.
    """
    if not 0.5 <= relation_alpha < 1.0:
        raise ValueError("relation_alpha must lie in [1/2,1)")
    source_edges = tuple(source_edges)
    target_edges = tuple(target_edges)
    provenance = certify_paired_uniform_neighborhood_provenance(
        left_size,
        right_size,
        source_edges,
        target_edges,
        max_subsets=max_subsets,
    )

    if provenance.status in {
        "paired_uniform_outcome_mismatch",
        "paired_uniform_relation_inventory_mismatch",
    }:
        return PairedUniformRelationTwinRestriction(
            "exact_empty_uniform_relation_invariant",
            provenance,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
            True,
            True,
            True,
            provenance.reason,
        )
    if provenance.status == "paired_explicit_johnson_provenance":
        return PairedUniformRelationTwinRestriction(
            "explicit_johnson_transport_required",
            provenance,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            True,
            False,
            False,
            True,
            "rev202 already produced explicit Johnson coordinates; relation-twin restriction is not the applicable child",
        )
    if provenance.status != "paired_nonconstant_containment_relation_provenance":
        return PairedUniformRelationTwinRestriction(
            "uniform_relation_twin_restriction_no_progress",
            provenance,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            provenance.provenance_verified,
            False,
            False,
            False,
            "a paired nonconstant containment relation is required before relation-twin restriction can be attempted",
        )

    t = provenance.source.relation_arity
    if t is None or t != provenance.target.relation_arity:
        raise AssertionError("paired containment relation lacks a common arity")
    src_sym = exact_colored_subset_symmetry_defect(
        right_size,
        t,
        _relation_palette(provenance.source),
        alpha=relation_alpha,
    )
    dst_sym = exact_colored_subset_symmetry_defect(
        right_size,
        t,
        _relation_palette(provenance.target),
        alpha=relation_alpha,
    )

    if _size_profile(src_sym) != _size_profile(dst_sym):
        return PairedUniformRelationTwinRestriction(
            "exact_empty_relation_twin_profile",
            provenance,
            src_sym,
            dst_sym,
            None,
            None,
            None,
            None,
            None,
            False,
            True,
            True,
            True,
            "a right-ground relation isomorphism preserves the exact transposition-twin class-size profile",
        )
    if src_sym.design_gate_certified != dst_sym.design_gate_certified:
        return PairedUniformRelationTwinRestriction(
            "exact_empty_relation_symmetry_gate",
            provenance,
            src_sym,
            dst_sym,
            None,
            None,
            None,
            None,
            None,
            False,
            True,
            True,
            True,
            "paired relation isomorphisms cannot disagree on the exact symmetry-defect theorem gate",
        )
    if src_sym.design_gate_certified:
        return PairedUniformRelationTwinRestriction(
            "relation_design_gate_available",
            provenance,
            src_sym,
            dst_sym,
            None,
            None,
            src_sym.largest_symmetric_class,
            None,
            None,
            True,
            False,
            False,
            True,
            "all exact relation twin classes obey the configured alpha bound; continue through the WL/Design/coherent child instead of forcing a restriction",
        )

    src_dom = _largest_class(src_sym)
    dst_dom = _largest_class(dst_sym)
    if len(src_dom) != len(dst_dom):
        raise AssertionError("equal twin-size profiles produced different largest sizes")
    if len(src_dom) <= relation_alpha * int(right_size):
        raise AssertionError("failed symmetry gate lacks a dominant class above alpha")
    src_rest = tuple(sorted(set(range(int(right_size))) - set(src_dom)))
    dst_rest = tuple(sorted(set(range(int(right_size))) - set(dst_dom)))
    if not src_rest or not dst_rest:
        raise AssertionError("a nonconstant relation cannot have the full right ground as one twin class")

    src_cert = reduce_part2_by_color_certificate(
        left_size,
        right_size,
        source_edges,
        src_dom,
        src_rest,
        alpha=restriction_alpha,
    )
    dst_cert = reduce_part2_by_color_certificate(
        left_size,
        right_size,
        target_edges,
        dst_dom,
        dst_rest,
        alpha=restriction_alpha,
    )
    if src_cert.status != dst_cert.status:
        return PairedUniformRelationTwinRestriction(
            "exact_empty_relation_twin_restriction_status",
            provenance,
            src_sym,
            dst_sym,
            src_cert,
            dst_cert,
            len(src_dom),
            None,
            None,
            False,
            False,
            True,
            True,
            "the canonical paired relation-twin partitions produced different exact rev200 restriction statuses",
        )
    if src_cert.status != "certified_reduce_part2_by_color":
        return PairedUniformRelationTwinRestriction(
            "relation_twin_restriction_invariant_violation",
            provenance,
            src_sym,
            dst_sym,
            src_cert,
            dst_cert,
            len(src_dom),
            None,
            None,
            True,
            False,
            False,
            False,
            "rev202 certified pairwise-distinct full left neighborhoods, so the canonical proper partition should satisfy rev200's exact Exercise-5.5 alternative; fail closed",
        )

    src_invariants = (
        src_cert.selected_part_index,
        src_cert.part0_largest_left_twin_class,
        src_cert.part1_largest_left_twin_class,
        src_cert.part0_exercise55_gate,
        src_cert.part1_exercise55_gate,
        src_cert.selected_alpha_shrink,
        len(src_cert.selected_part),
    )
    dst_invariants = (
        dst_cert.selected_part_index,
        dst_cert.part0_largest_left_twin_class,
        dst_cert.part1_largest_left_twin_class,
        dst_cert.part0_exercise55_gate,
        dst_cert.part1_exercise55_gate,
        dst_cert.selected_alpha_shrink,
        len(dst_cert.selected_part),
    )
    if src_invariants != dst_invariants:
        return PairedUniformRelationTwinRestriction(
            "exact_empty_relation_twin_restriction_invariant",
            provenance,
            src_sym,
            dst_sym,
            src_cert,
            dst_cert,
            len(src_dom),
            None,
            None,
            False,
            False,
            True,
            True,
            "paired canonical restrictions disagree on exact twin/Exercise-5.5 selection invariants",
        )

    return PairedUniformRelationTwinRestriction(
        "certified_paired_uniform_relation_twin_restriction",
        provenance,
        src_sym,
        dst_sym,
        src_cert,
        dst_cert,
        len(src_dom),
        src_cert.selected_part_index,
        len(src_cert.selected_part),
        True,
        True,
        False,
        True,
        "the failed relation symmetry-defect gate yields a unique canonical dominant twin class; rev200 certifies the same proper right restriction on both paired original bipartite inputs",
    )
