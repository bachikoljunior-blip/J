from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Iterable

from bipartite_reduce_part2_by_color_v1 import (
    ReducePart2ByColorCertificate,
    reduce_part2_by_color_certificate,
)
from colored_subset_symmetry_defect_v1 import (
    SymmetryDefectCertificate,
    exact_colored_subset_symmetry_defect,
)
from paired_bipartite_higher_arity_right_relation_v1 import (
    PairedHigherArityRightRelationProvenance,
    certify_paired_higher_arity_right_relation_provenance,
)


@dataclass(frozen=True)
class PairedLargeRelationTwinRestriction:
    status: str
    relation_provenance: PairedHigherArityRightRelationProvenance
    source_symmetry: SymmetryDefectCertificate | None
    target_symmetry: SymmetryDefectCertificate | None
    source_restriction: ReducePart2ByColorCertificate | None
    target_restriction: ReducePart2ByColorCertificate | None
    dominant_twin_size: int | None
    selected_part_index: int | None
    selected_part_size: int | None
    provenance_verified: bool
    restriction_pair_complete: bool
    exact_empty: bool
    exact: bool
    reason: str


def _palette(relation):
    return tuple(signature for _subset, signature in relation.subset_signatures)


def _class_size_profile(certificate: SymmetryDefectCertificate) -> tuple[int, ...]:
    return tuple(sorted(map(len, certificate.twin_classes)))


def _largest_class(certificate: SymmetryDefectCertificate) -> tuple[int, ...]:
    if not certificate.twin_classes:
        return ()
    return max(certificate.twin_classes, key=lambda cell: (len(cell), tuple(-x for x in cell)))


def certify_paired_large_relation_twin_restriction(
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    source_left_colors: Iterable[Hashable] | None = None,
    target_left_colors: Iterable[Hashable] | None = None,
    source_right_colors: Iterable[Hashable] | None = None,
    target_right_colors: Iterable[Hashable] | None = None,
    relation_max_arity: int | None = None,
    max_relation_subsets: int = 200000,
    relation_alpha: float = 0.75,
    restriction_alpha: float = 0.75,
) -> PairedLargeRelationTwinRestriction:
    """Exploit the exact large-twin residual when the Design symmetry gate fails.

    A nonconstant canonical right relation with a twin class larger than
    ``relation_alpha * |V2|`` has a unique dominant twin class for
    ``relation_alpha >= 1/2``. That class and its complement form a canonical
    ordered right partition. We feed this partition back into rev200's exact
    Exercise-5.5 restriction certificate and pair every numerical invariant
    across source and target.

    Thus Design-gate failure is treated as structural information, not as a
    reason to stop. Ambient transport/full-string intersection remain later
    obligations.
    """
    if not 0.5 <= relation_alpha < 1.0:
        raise ValueError("relation_alpha must lie in [1/2,1)")
    source_edges = tuple(source_edges)
    target_edges = tuple(target_edges)
    relation = certify_paired_higher_arity_right_relation_provenance(
        left_size,
        right_size,
        source_edges,
        target_edges,
        source_left_colors=source_left_colors,
        target_left_colors=target_left_colors,
        source_right_colors=source_right_colors,
        target_right_colors=target_right_colors,
        max_arity=relation_max_arity,
        max_relation_subsets=max_relation_subsets,
    )

    exact_mismatch = {
        "left_color_inventory_mismatch",
        "first_order_right_signature_inventory_mismatch",
        "higher_arity_relation_inventory_mismatch",
    }
    if relation.status in exact_mismatch:
        return PairedLargeRelationTwinRestriction(
            "exact_empty_right_relation_invariant",
            relation,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
            False,
            True,
            True,
            relation.reason,
        )
    if relation.status != "paired_higher_arity_right_relation_provenance":
        return PairedLargeRelationTwinRestriction(
            "undetermined_large_relation_twin_restriction",
            relation,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
            False,
            False,
            False,
            "a paired nonconstant higher-arity right relation is required before inspecting its exact twin classes",
        )

    t = relation.selected_arity
    if t is None:
        raise AssertionError("paired right relation has no selected arity")
    src_sym = exact_colored_subset_symmetry_defect(
        right_size, t, _palette(relation.source_relation), alpha=relation_alpha
    )
    dst_sym = exact_colored_subset_symmetry_defect(
        right_size, t, _palette(relation.target_relation), alpha=relation_alpha
    )
    if _class_size_profile(src_sym) != _class_size_profile(dst_sym):
        return PairedLargeRelationTwinRestriction(
            "exact_empty_relation_twin_profile",
            relation,
            src_sym,
            dst_sym,
            None,
            None,
            None,
            None,
            None,
            False,
            False,
            True,
            True,
            "relation isomorphisms preserve exact transposition-twin class sizes, but the source/target profiles differ",
        )
    if src_sym.design_gate_certified != dst_sym.design_gate_certified:
        return PairedLargeRelationTwinRestriction(
            "exact_empty_relation_symmetry_gate_invariant",
            relation,
            src_sym,
            dst_sym,
            None,
            None,
            None,
            None,
            None,
            False,
            False,
            True,
            True,
            "paired relation isomorphisms cannot disagree on the exact symmetry-defect gate",
        )
    if src_sym.design_gate_certified:
        return PairedLargeRelationTwinRestriction(
            "design_gate_available_not_large_twin_residual",
            relation,
            src_sym,
            dst_sym,
            None,
            None,
            None,
            None,
            None,
            True,
            False,
            False,
            True,
            "the exact relation symmetry-defect gate already holds; continue through the k-WL/Design branch instead of the large-twin residual",
        )

    src_dom = _largest_class(src_sym)
    dst_dom = _largest_class(dst_sym)
    if len(src_dom) != len(dst_dom) or len(src_dom) <= relation_alpha * right_size:
        return PairedLargeRelationTwinRestriction(
            "large_relation_twin_invariant_violation",
            relation,
            src_sym,
            dst_sym,
            None,
            None,
            None,
            None,
            None,
            False,
            False,
            False,
            False,
            "failed symmetry gate did not yield matching unique dominant twin classes above the configured alpha threshold",
        )
    src_rest = tuple(sorted(set(range(int(right_size))) - set(src_dom)))
    dst_rest = tuple(sorted(set(range(int(right_size))) - set(dst_dom)))
    if not src_rest or not dst_rest:
        return PairedLargeRelationTwinRestriction(
            "large_relation_twin_complement_empty",
            relation,
            src_sym,
            dst_sym,
            None,
            None,
            len(src_dom),
            None,
            0,
            False,
            False,
            False,
            False,
            "a nonconstant selected relation should not have the entire right ground as one transposition-twin class",
        )

    src_cert = reduce_part2_by_color_certificate(
        left_size,
        right_size,
        source_edges,
        src_dom,
        src_rest,
        alpha=restriction_alpha,
        left_colors=source_left_colors,
    )
    dst_cert = reduce_part2_by_color_certificate(
        left_size,
        right_size,
        target_edges,
        dst_dom,
        dst_rest,
        alpha=restriction_alpha,
        left_colors=target_left_colors,
    )

    src_profile = tuple(sorted(map(len, src_cert.full_left_twin_classes)))
    dst_profile = tuple(sorted(map(len, dst_cert.full_left_twin_classes)))
    if src_profile != dst_profile:
        return PairedLargeRelationTwinRestriction(
            "exact_empty_full_left_twin_profile",
            relation, src_sym, dst_sym, src_cert, dst_cert, len(src_dom), None, None,
            False, False, True, True,
            "color-preserving bipartite isomorphisms preserve the full left twin-class size profile",
        )
    if src_cert.status != dst_cert.status:
        return PairedLargeRelationTwinRestriction(
            "exact_empty_large_twin_restriction_status",
            relation, src_sym, dst_sym, src_cert, dst_cert, len(src_dom), None, None,
            False, False, True, True,
            "canonical large-twin partitions produced different exact rev200 restriction statuses",
        )
    if src_cert.status != "certified_reduce_part2_by_color":
        return PairedLargeRelationTwinRestriction(
            "large_twin_partition_restriction_no_progress",
            relation, src_sym, dst_sym, src_cert, dst_cert, len(src_dom), None, None,
            True, False, False, True,
            "the canonical dominant-twin partition is paired, but rev200's full-left-twin-free / Exercise-5.5 restriction gate does not fire",
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
        return PairedLargeRelationTwinRestriction(
            "exact_empty_large_twin_restriction_invariant",
            relation, src_sym, dst_sym, src_cert, dst_cert, len(src_dom), None, None,
            False, False, True, True,
            "paired canonical dominant-twin restrictions disagree on exact rev200 selection invariants",
        )

    return PairedLargeRelationTwinRestriction(
        "certified_paired_large_relation_twin_restriction",
        relation,
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
        "the failed Design symmetry gate yields a unique canonical dominant right-relation twin class; its proper ordered partition is paired and rev200 certifies the same exact Exercise-5.5 restriction on both sides",
    )
