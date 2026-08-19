from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log2

from colored_subset_symmetry_defect_v1 import (
    SymmetryDefectCertificate,
    exact_colored_subset_symmetry_defect,
)
from johnson_ground_relational_lift_v1 import lift_primitive_johnson_to_ground_relation
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from signed_johnson_complement_safe_image_si_v1 import complement_safe_t_relation_signatures
from signed_johnson_ground_profile_partition_si_v1 import _color_token
from signed_johnson_log_certificate_design_descent_si_v1 import (
    SignedJohnsonLogCertificateProof,
    signed_johnson_log_certificate_design_descent_si,
)


@dataclass(frozen=True)
class PairedSymmetryDefectGate:
    status: str
    source: SymmetryDefectCertificate
    target: SymmetryDefectCertificate
    source_twin_class_sizes: tuple[int, ...]
    target_twin_class_sizes: tuple[int, ...]
    invariant_compatible: bool
    exact_empty: bool
    design_gate_certified: bool
    relation_entries_checked: int
    reason: str


@dataclass(frozen=True)
class SignedJohnsonSymmetryDefectGateProof(SignedJohnsonLogCertificateProof):
    source_largest_symmetric_class: int = 0
    target_largest_symmetric_class: int = 0
    source_symmetry_defect: int = 0
    target_symmetry_defect: int = 0
    symmetry_alpha: float = 0.9
    symmetry_defect_gate_certified: bool = False
    source_twin_class_sizes: tuple[int, ...] = ()
    target_twin_class_sizes: tuple[int, ...] = ()
    transpositions_checked: int = 0
    symmetry_relation_entries_checked: int = 0


def paired_colored_subset_symmetry_defect_gate(
    vertex_count: int,
    arity: int,
    source_colors,
    target_colors,
    *,
    alpha: float = 0.9,
) -> PairedSymmetryDefectGate:
    """Compare exact Design-Lemma symmetry-defect certificates canonically.

    Any color-preserving isomorphism of the two complete colored t-subset
    relations conjugates color-preserving transpositions.  It must therefore map
    twin classes to twin classes and preserve their size multiset.  A mismatch of
    either relation-color multiplicities or twin-class sizes is an exact empty
    invariant.  Matching certificates establish the symmetry-defect hypothesis
    only when it holds on both sides; they do not by themselves implement the
    subsequent individualization/WL Design-Lemma descent.
    """
    source_palette = tuple(source_colors)
    target_palette = tuple(target_colors)
    source = exact_colored_subset_symmetry_defect(
        vertex_count, arity, source_palette, alpha=alpha
    )
    target = exact_colored_subset_symmetry_defect(
        vertex_count, arity, target_palette, alpha=alpha
    )
    source_sizes = tuple(sorted(len(cell) for cell in source.twin_classes))
    target_sizes = tuple(sorted(len(cell) for cell in target.twin_classes))
    color_compatible = Counter(source_palette) == Counter(target_palette)
    twin_compatible = source_sizes == target_sizes
    compatible = color_compatible and twin_compatible
    entries = source.relation_entries_checked + target.relation_entries_checked

    if not color_compatible:
        return PairedSymmetryDefectGate(
            "exact_empty_symmetry_relation_color_multiplicity",
            source,
            target,
            source_sizes,
            target_sizes,
            False,
            True,
            False,
            entries,
            "complete colored test-set relations have different color multiplicities",
        )
    if not twin_compatible:
        return PairedSymmetryDefectGate(
            "exact_empty_symmetry_defect_twin_shape",
            source,
            target,
            source_sizes,
            target_sizes,
            False,
            True,
            False,
            entries,
            "exact twin-class size multisets differ, so no color-preserving relation isomorphism exists",
        )

    gate = source.design_gate_certified and target.design_gate_certified
    if gate:
        return PairedSymmetryDefectGate(
            "verified_paired_symmetry_defect_gate",
            source,
            target,
            source_sizes,
            target_sizes,
            True,
            False,
            True,
            entries,
            "source and target have compatible exact twin invariants and both satisfy the configured symmetry-defect hypothesis",
        )

    return PairedSymmetryDefectGate(
        "symmetry_defect_gate_closed",
        source,
        target,
        source_sizes,
        target_sizes,
        True,
        False,
        False,
        entries,
        "exact compatible twin invariants were computed, but the largest symmetric subset exceeds the configured Design-Lemma threshold",
    )


def _enriched_proof(
    base: SignedJohnsonLogCertificateProof,
    paired: PairedSymmetryDefectGate,
    *,
    status: str,
    operation_kind: str,
    exact: bool,
    terminal: bool,
    local_bound: float,
    accounting: RecurrenceAccountingNode,
    reason: str,
) -> SignedJohnsonSymmetryDefectGateProof:
    transpositions = (
        paired.source.transpositions_checked + paired.target.transpositions_checked
    )
    return SignedJohnsonSymmetryDefectGateProof(
        status=status,
        coset=None,
        operation_kind=operation_kind,
        root_n=base.root_n,
        domain_size=base.domain_size,
        canonical=True,
        exact=exact,
        local_cost_certified=True,
        local_log2_cost_bound=local_bound,
        terminal_certified=terminal,
        children=(),
        accounting=accounting,
        permutation_candidates_checked=(
            base.permutation_candidates_checked + transpositions
        ),
        reason=reason,
        ground_size=base.ground_size,
        subset_size=base.subset_size,
        test_arity=base.test_arity,
        test_count=base.test_count,
        theorem_arity_cap=base.theorem_arity_cap,
        theorem_parameter_gate=base.theorem_parameter_gate,
        arity_path=base.arity_path,
        source_ground_cells=base.source_ground_cells,
        target_ground_cells=base.target_ground_cells,
        significant_ground_split=base.significant_ground_split,
        johnson_ground_size=base.johnson_ground_size,
        johnson_subset_size=base.johnson_subset_size,
        partition_orbit_states=base.partition_orbit_states,
        source_largest_symmetric_class=paired.source.largest_symmetric_class,
        target_largest_symmetric_class=paired.target.largest_symmetric_class,
        source_symmetry_defect=paired.source.defect,
        target_symmetry_defect=paired.target.defect,
        symmetry_alpha=paired.source.alpha,
        symmetry_defect_gate_certified=paired.design_gate_certified,
        source_twin_class_sizes=paired.source_twin_class_sizes,
        target_twin_class_sizes=paired.target_twin_class_sizes,
        transpositions_checked=transpositions,
        symmetry_relation_entries_checked=paired.relation_entries_checked,
    )


def signed_johnson_log_certificate_symmetry_defect_gate_si(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    max_class_fraction: float = 0.9,
    max_test_sets: int = 200000,
    max_recognition_nodes: int = 500000,
    max_johnson_nodes: int = 500000,
    partition_state_poly_power: int = 2,
    max_partition_states: int = 4096,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    candidate_group_order_poly_power: int = 2,
    max_candidate_group_order: int = 256,
    max_depth: int = 64,
    symmetry_alpha: float = 0.9,
):
    """W1R-H6 bridge from rev184 homogeneous relations to the rev185 gate.

    All non-homogeneous rev184 outcomes pass through unchanged.  Only the
    fail-closed `undetermined_log_certificate_design_gate` boundary is reopened:
    the exact complete logarithmic relation is reconstructed in the same Johnson
    gauge and checked with paired exact symmetry-defect certificates.  Invariant
    mismatch is an exact empty terminal.  A certified defect gate is proof-carrying
    structural progress, not a claim that individualization/WL Design-Lemma
    descent has already been executed.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    base = signed_johnson_log_certificate_design_descent_si(
        group,
        source,
        target,
        root_n=root_n,
        max_class_fraction=max_class_fraction,
        max_test_sets=max_test_sets,
        max_recognition_nodes=max_recognition_nodes,
        max_johnson_nodes=max_johnson_nodes,
        partition_state_poly_power=partition_state_poly_power,
        max_partition_states=max_partition_states,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        candidate_group_order_poly_power=candidate_group_order_poly_power,
        max_candidate_group_order=max_candidate_group_order,
        max_depth=max_depth,
    )
    if base.status != "undetermined_log_certificate_design_gate":
        return base

    lift = lift_primitive_johnson_to_ground_relation(
        group,
        source,
        target,
        max_recognition_nodes=max_recognition_nodes,
    )
    if (
        lift.status != "exact_johnson_ground_relational_lift"
        or not lift.strict_auxiliary_progress
        or lift.ground_size != base.ground_size
        or lift.subset_size != base.subset_size
    ):
        raise AssertionError(
            "rev184 design-gate output could not be reconstructed in the same exact Johnson gauge"
        )

    v = int(lift.ground_size)
    k = int(lift.subset_size)
    t = int(base.test_arity)
    complement = any(bool(g.complement) for g in lift.lifted_generators)
    source_tokens = tuple(_color_token(x) for x in lift.source_on_standard_subsets)
    target_tokens = tuple(_color_token(x) for x in lift.target_on_standard_subsets)
    source_relation = complement_safe_t_relation_signatures(
        v, k, source_tokens, t, complement_in_image=complement
    )
    target_relation = complement_safe_t_relation_signatures(
        v, k, target_tokens, t, complement_in_image=complement
    )
    paired = paired_colored_subset_symmetry_defect_gate(
        v,
        t,
        source_relation,
        target_relation,
        alpha=symmetry_alpha,
    )

    executed = (
        paired.relation_entries_checked
        + paired.source.transpositions_checked
        + paired.target.transpositions_checked
        + lift.recognition_search_nodes
        + base.test_count
    )
    local_bound = (
        log2(max(1, executed))
        + 64.0 * log2(max(2, base.root_n))
        + 96.0
    )
    if local_bound + 1e-12 < log2(max(1, executed)):
        raise AssertionError("symmetry-defect accounting does not dominate executed checks")

    if paired.exact_empty:
        accounting = RecurrenceAccountingNode(
            n=base.root_n,
            m=max(1, v),
            operation_kind="log_certificate_symmetry_defect_invariant_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local_bound,
            children=(),
            terminal_certified=True,
            reason=paired.reason,
        )
        return _enriched_proof(
            base,
            paired,
            status=paired.status,
            operation_kind="log_certificate_symmetry_defect_invariant_terminal",
            exact=True,
            terminal=True,
            local_bound=local_bound,
            accounting=accounting,
            reason=paired.reason,
        )

    if paired.design_gate_certified:
        accounting = RecurrenceAccountingNode(
            n=base.root_n,
            m=max(1, v),
            operation_kind="log_certificate_symmetry_defect_gate",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=local_bound,
            children=(),
            terminal_certified=False,
            reason=(
                paired.reason
                + "; canonical individualization/WL Design-Lemma descent remains the next proof-carrying child"
            ),
        )
        return _enriched_proof(
            base,
            paired,
            status="verified_log_certificate_symmetry_defect_gate",
            operation_kind="log_certificate_symmetry_defect_gate",
            exact=False,
            terminal=False,
            local_bound=local_bound,
            accounting=accounting,
            reason=accounting.reason,
        )

    accounting = RecurrenceAccountingNode(
        n=base.root_n,
        m=max(1, v),
        operation_kind="unresolved_log_certificate_symmetry_defect_gate",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=(),
        terminal_certified=False,
        reason=paired.reason,
    )
    return _enriched_proof(
        base,
        paired,
        status="undetermined_log_certificate_symmetry_defect_gate_closed",
        operation_kind="unresolved_log_certificate_symmetry_defect_gate",
        exact=False,
        terminal=False,
        local_bound=local_bound,
        accounting=accounting,
        reason=paired.reason,
    )
