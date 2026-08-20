from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from colored_subset_exact_twl_design_v1 import (
    PairedExactTWLDesignFamily,
    paired_exact_twl_design_witness_families,
)
from design_twl_recurrence_progress_v1 import (
    DesignTWLRecurrenceProgress,
    certify_design_twl_recurrence_progress,
)
from relation_twin_restriction_provenance_v1 import (
    PairedRelationTwinRestriction,
    certify_paired_relation_twin_restriction,
)


@dataclass(frozen=True)
class RelationWLDesignProvenance:
    status: str
    parent: PairedRelationTwinRestriction
    relation_arity: int | None
    source_relation_inventory: tuple[tuple[int, int], ...]
    target_relation_inventory: tuple[tuple[int, int], ...]
    source_twin_inventory: tuple[int, ...]
    target_twin_inventory: tuple[int, ...]
    design_family: PairedExactTWLDesignFamily | None
    source_progress: tuple[DesignTWLRecurrenceProgress, ...]
    target_progress: tuple[DesignTWLRecurrenceProgress, ...]
    progress_inventory: tuple[tuple[tuple, int], ...]
    child_aux_sizes: tuple[int, ...]
    exact_empty: bool
    provenance_verified: bool
    recursive_output_complete: bool
    downstream_unresolved: bool
    exact: bool
    reason: str


def _relation_palette(relation) -> tuple[int, ...]:
    if relation.relation_arity is None:
        raise ValueError("containment relation has no arity")
    n = int(relation.right_size)
    k = int(relation.relation_arity)
    coords = tuple(combinations(range(n), k))
    values = {}
    for color, subsets in relation.relation_classes:
        for subset in subsets:
            key = tuple(sorted(int(x) for x in subset))
            if len(key) != k or len(set(key)) != k:
                raise ValueError("relation class contains a malformed subset")
            if key in values:
                raise ValueError("relation classes overlap")
            values[key] = int(color)
    if set(values) != set(coords):
        raise ValueError("relation classes do not color every k-subset exactly once")
    return tuple(values[coord] for coord in coords)


def _point_cells(colors: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    buckets = defaultdict(list)
    for point, color in enumerate(colors):
        buckets[int(color)].append(point)
    return tuple(sorted((tuple(cell) for cell in buckets.values()), key=lambda C: (len(C), C)))


def _reduction_token(progress: DesignTWLRecurrenceProgress):
    reduction = progress.split_or_johnson_result
    if reduction is None:
        return None
    return (
        reduction.status,
        bool(reduction.progress_verified),
        reduction.reduced_domain_size,
        reduction.johnson_ground_size,
        reduction.johnson_subset_size,
        tuple(sorted(map(len, reduction.split_classes))),
    )


def _progress_token(progress: DesignTWLRecurrenceProgress) -> tuple:
    return (
        progress.status,
        progress.design_status,
        tuple(progress.child_aux_sizes),
        progress.max_child_aux_size,
        bool(progress.aux_shrink_certified),
        _reduction_token(progress),
        bool(progress.canonical),
        bool(progress.cost_certified),
    )


def _inventory(progresses: Iterable[DesignTWLRecurrenceProgress]) -> Counter:
    return Counter(_progress_token(progress) for progress in progresses)


def _freeze_inventory(counter: Counter) -> tuple[tuple[tuple, int], ...]:
    return tuple(sorted(counter.items(), key=repr))


def _empty_result(
    status: str,
    parent: PairedRelationTwinRestriction,
    *,
    exact_empty: bool,
    provenance_verified: bool,
    recursive_output_complete: bool,
    reason: str,
) -> RelationWLDesignProvenance:
    src = parent.source.relation
    dst = parent.target.relation
    return RelationWLDesignProvenance(
        status,
        parent,
        src.relation_arity if src.relation_arity == dst.relation_arity else None,
        tuple(src.relation_inventory),
        tuple(dst.relation_inventory),
        tuple(parent.source.twin_class_size_inventory),
        tuple(parent.target.twin_class_size_inventory),
        None,
        (),
        (),
        (),
        (),
        exact_empty,
        provenance_verified,
        recursive_output_complete,
        not exact_empty and not recursive_output_complete,
        True,
        reason,
    )


def certify_relation_wl_design_provenance(
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    relation_alpha: float = 0.75,
    design_alpha: float = 0.9,
    root_n: int | None = None,
    max_subsets: int = 200000,
    max_states: int = 200000,
    max_tuple_states: int = 250000,
    max_rounds: int | None = None,
    max_work_units: int = 500000000,
    max_johnson_nodes: int = 500000,
) -> RelationWLDesignProvenance:
    """Wire rev203's no-large-twin relation into exact Design/WL recurrence output.

    This routine is deliberately a provenance bridge, not the missing general
    Split-or-Johnson theorem-conclusion producer. It consumes the paired rev203
    certificate. On the no-large-relation-twin branch it reconstructs the exact
    colored containment relation on the right ground and passes the full relation
    to the existing exact k-WL Design-Lemma machinery.

    The unary case is discharged directly: transposition twins of a unary relation
    are exactly its color classes, so rev203's no->half-class certificate is already
    a canonical alpha-bounded point partition for every design_alpha>=1/2.

    For arity >=2 the complete first-successful individualization family is used.
    Every witness is translated through certify_design_twl_recurrence_progress.
    The source/target multisets of typed recursive outputs must agree. This keeps
    arbitrary individualized tuples out of the paired invariant while preserving
    all canonical structural child measures.

    A requires_full_split_or_johnson output is a complete output of this bridge but
    remains an unresolved downstream child. Resource/theorem gates fail closed. No
    global recurrence or AGI claim is made here.
    """
    source_edges = tuple(source_edges)
    target_edges = tuple(target_edges)
    if root_n is None:
        root_n = max(int(left_size), int(right_size))
    if root_n < max(int(left_size), int(right_size)):
        raise ValueError("root_n must dominate both bipartite parts")
    if not 0.5 <= design_alpha < 1.0:
        raise ValueError("design_alpha must lie in [1/2,1)")

    parent = certify_paired_relation_twin_restriction(
        left_size,
        right_size,
        source_edges,
        target_edges,
        alpha=relation_alpha,
        max_subsets=max_subsets,
    )

    if parent.status in {
        "paired_relation_twin_status_mismatch",
        "paired_relation_twin_inventory_mismatch",
        "paired_relation_twin_restriction_invariant_mismatch",
    }:
        return _empty_result(
            "exact_empty_parent_relation_twin_invariant",
            parent,
            exact_empty=True,
            provenance_verified=bool(parent.exact),
            recursive_output_complete=True,
            reason="rev203 found an exact paired invariant mismatch, so no right-ground relation isomorphism survives",
        )

    if parent.status == "paired_relation_twin_restriction":
        return _empty_result(
            "relation_large_twin_restriction_branch_already_selected",
            parent,
            exact_empty=False,
            provenance_verified=parent.provenance_verified,
            recursive_output_complete=True,
            reason="rev203 selected the canonical proper right restriction; the no-large-twin Design branch is not the active child",
        )

    if not (
        parent.status == "paired_relation_twin_no_restriction_progress"
        and parent.source.status == "relation_twin_no_large_class"
        and parent.target.status == "relation_twin_no_large_class"
        and parent.provenance_verified
    ):
        return _empty_result(
            "relation_wl_design_parent_gate_not_met",
            parent,
            exact_empty=False,
            provenance_verified=parent.provenance_verified,
            recursive_output_complete=False,
            reason="the paired rev203 parent did not certify the exact no-large-relation-twin branch required by W1R-H6-R3c1",
        )

    src = parent.source.relation
    dst = parent.target.relation
    src_meta = (
        src.original_common_degree,
        src.normalized_degree,
        src.complemented,
        src.relation_arity,
        tuple(src.relation_inventory),
    )
    dst_meta = (
        dst.original_common_degree,
        dst.normalized_degree,
        dst.complemented,
        dst.relation_arity,
        tuple(dst.relation_inventory),
    )
    if src_meta != dst_meta:
        return _empty_result(
            "exact_empty_containment_relation_inventory",
            parent,
            exact_empty=True,
            provenance_verified=True,
            recursive_output_complete=True,
            reason="degree normalization, relation arity, or exact containment-count multiplicities differ across the paired inputs",
        )

    if src.status != "nonconstant_containment_relation" or dst.status != "nonconstant_containment_relation":
        return _empty_result(
            "relation_wl_design_requires_nonconstant_containment_relation",
            parent,
            exact_empty=False,
            provenance_verified=True,
            recursive_output_complete=False,
            reason="the rev203 no-large-twin branch must carry a materialized nonconstant containment relation",
        )

    source_colors = _relation_palette(src)
    target_colors = _relation_palette(dst)
    k = int(src.relation_arity)
    n = int(right_size)

    # Unary containment relations already are canonical point colorings.
    if k == 1:
        source_cells = _point_cells(source_colors)
        target_cells = _point_cells(target_colors)
        source_sizes = tuple(sorted(map(len, source_cells)))
        target_sizes = tuple(sorted(map(len, target_cells)))
        if source_sizes != target_sizes:
            return _empty_result(
                "exact_empty_unary_relation_partition_invariant",
                parent,
                exact_empty=True,
                provenance_verified=True,
                recursive_output_complete=True,
                reason="unary containment color-cell sizes differ across the paired inputs",
            )
        largest = max(source_sizes, default=0)
        if largest > design_alpha * n + 1e-12:
            return _empty_result(
                "unary_relation_alpha_bound_invariant_failure",
                parent,
                exact_empty=False,
                provenance_verified=False,
                recursive_output_complete=False,
                reason="rev203 no->half relation twins should force every unary color class to be alpha-bounded",
            )
        inventory = ((("certified_unary_relation_alpha_split_progress", source_sizes), 1),)
        return RelationWLDesignProvenance(
            "certified_unary_relation_alpha_split_progress",
            parent,
            k,
            tuple(src.relation_inventory),
            tuple(dst.relation_inventory),
            tuple(parent.source.twin_class_size_inventory),
            tuple(parent.target.twin_class_size_inventory),
            None,
            (),
            (),
            inventory,
            source_sizes,
            False,
            True,
            True,
            False,
            True,
            "the exact unary containment relation is itself a paired canonical alpha-bounded partition; no k-WL invocation is required",
        )

    family = paired_exact_twl_design_witness_families(
        n,
        k,
        source_colors,
        target_colors,
        alpha=design_alpha,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_rounds=max_rounds,
        max_work_units=max_work_units,
    )
    if family.exact_empty:
        return RelationWLDesignProvenance(
            "exact_empty_paired_relation_twl_design_invariant",
            parent,
            k,
            tuple(src.relation_inventory),
            tuple(dst.relation_inventory),
            tuple(parent.source.twin_class_size_inventory),
            tuple(parent.target.twin_class_size_inventory),
            family,
            (),
            (),
            (),
            (),
            True,
            True,
            True,
            False,
            True,
            family.reason,
        )
    if not family.complete or not family.invariant_compatible:
        return RelationWLDesignProvenance(
            "relation_twl_design_gate_or_resource_closed",
            parent,
            k,
            tuple(src.relation_inventory),
            tuple(dst.relation_inventory),
            tuple(parent.source.twin_class_size_inventory),
            tuple(parent.target.twin_class_size_inventory),
            family,
            (),
            (),
            (),
            (),
            False,
            True,
            False,
            True,
            True,
            family.reason,
        )

    source_progress = tuple(
        certify_design_twl_recurrence_progress(
            n,
            k,
            source_colors,
            outcome.individualized,
            root_n=root_n,
            alpha=design_alpha,
            max_tuple_states=max_tuple_states,
            max_rounds=max_rounds,
            max_work_units=max_work_units,
            max_johnson_nodes=max_johnson_nodes,
        )
        for outcome in family.source.witness_outcomes
    )
    target_progress = tuple(
        certify_design_twl_recurrence_progress(
            n,
            k,
            target_colors,
            outcome.individualized,
            root_n=root_n,
            alpha=design_alpha,
            max_tuple_states=max_tuple_states,
            max_rounds=max_rounds,
            max_work_units=max_work_units,
            max_johnson_nodes=max_johnson_nodes,
        )
        for outcome in family.target.witness_outcomes
    )
    source_inventory = _inventory(source_progress)
    target_inventory = _inventory(target_progress)
    if source_inventory != target_inventory:
        return RelationWLDesignProvenance(
            "exact_empty_relation_twl_recursive_output_invariant",
            parent,
            k,
            tuple(src.relation_inventory),
            tuple(dst.relation_inventory),
            tuple(parent.source.twin_class_size_inventory),
            tuple(parent.target.twin_class_size_inventory),
            family,
            source_progress,
            target_progress,
            (),
            (),
            True,
            True,
            True,
            False,
            True,
            "paired exact Design witness families agree, but their canonical typed recurrence-output multisets differ",
        )

    if not source_progress:
        return RelationWLDesignProvenance(
            "relation_twl_design_missing_recurrence_witness",
            parent,
            k,
            tuple(src.relation_inventory),
            tuple(dst.relation_inventory),
            tuple(parent.source.twin_class_size_inventory),
            tuple(parent.target.twin_class_size_inventory),
            family,
            (),
            (),
            (),
            (),
            False,
            True,
            False,
            True,
            True,
            "the paired Design family was marked complete without a first-successful witness",
        )

    allowed = {
        "certified_design_auxiliary_split_progress",
        "certified_design_upcc_split_or_johnson_progress",
        "requires_full_split_or_johnson",
    }
    if any(progress.status not in allowed for progress in source_progress + target_progress):
        return RelationWLDesignProvenance(
            "relation_twl_design_recursive_output_fail_closed",
            parent,
            k,
            tuple(src.relation_inventory),
            tuple(dst.relation_inventory),
            tuple(parent.source.twin_class_size_inventory),
            tuple(parent.target.twin_class_size_inventory),
            family,
            source_progress,
            target_progress,
            _freeze_inventory(source_inventory),
            (),
            False,
            True,
            False,
            True,
            True,
            "an accepted exact Design witness did not translate to a certified split/Johnson progress measure or the explicit full-Split-or-Johnson child",
        )

    child_sizes = tuple(sorted(
        size
        for progress in source_progress
        for size in progress.child_aux_sizes
    ))
    downstream = any(
        progress.status == "requires_full_split_or_johnson"
        for progress in source_progress
    )
    return RelationWLDesignProvenance(
        (
            "certified_relation_twl_design_to_full_split_or_johnson_child"
            if downstream
            else "certified_relation_twl_design_recursive_progress"
        ),
        parent,
        k,
        tuple(src.relation_inventory),
        tuple(dst.relation_inventory),
        tuple(parent.source.twin_class_size_inventory),
        tuple(parent.target.twin_class_size_inventory),
        family,
        source_progress,
        target_progress,
        _freeze_inventory(source_inventory),
        child_sizes,
        False,
        True,
        True,
        downstream,
        True,
        (
            "rev203 no-large-twin provenance is wired through the complete paired exact k-WL Design family to the explicit full Split-or-Johnson downstream child"
            if downstream
            else "rev203 no-large-twin provenance is wired through the complete paired exact k-WL Design family to canonical alpha-shrinking recursive progress outputs"
        ),
    )
