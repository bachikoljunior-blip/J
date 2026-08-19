from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from aggregate_local_certificate_relation import aggregate_fullness_relation
from pair_codegree_canonical_refinement import refine_pair_codegrees
from master_canonical_reduction import master_canonical_reduction
from coherent_relation_exact_terminal import canonicalize_pair_relation_terminal


@dataclass(frozen=True)
class ExtendedCanonicalReduction:
    status: str
    original_domain_size: int
    reduced_domain_size: Optional[int]
    branch_count: int
    split_classes: Tuple[Tuple[int, ...], ...]
    progress_kind: str
    progress_verified: bool
    terminal_canonical_code: Optional[bytes]
    reason: str


def master_canonical_reduction_v2(
    group,
    blocks,
    values,
    *,
    max_nodes=500000,
    max_test_sets=200000,
    max_class_fraction=0.9,
    max_johnson_nodes=500000,
    exact_terminal_size=24,
    max_terminal_states=500000,
    max_terminal_group_nodes=500000,
) -> ExtendedCanonicalReduction:
    """Add an exact bounded terminal to rev127 without weakening its large-case gate.

    All rev127 structural reductions are attempted first. Only its explicitly
    unresolved homogeneous design/coherent case is eligible for the O(m^2)
    incidence-graph terminal, and only when m<=`exact_terminal_size`. Larger
    cases remain unresolved for the genuine worst-case quasipolynomial child.
    """
    base = master_canonical_reduction(
        group, blocks, values,
        max_nodes=max_nodes,
        max_test_sets=max_test_sets,
        max_class_fraction=max_class_fraction,
        max_johnson_nodes=max_johnson_nodes,
    )
    if base.status != "unresolved_homogeneous_design_or_coherent_obstruction":
        return ExtendedCanonicalReduction(
            base.status, base.original_domain_size, base.reduced_domain_size,
            base.branch_count, base.split_classes, base.progress_kind,
            base.progress_verified, None, base.reason,
        )

    m = base.original_domain_size
    if m > exact_terminal_size:
        return ExtendedCanonicalReduction(
            "unresolved_large_homogeneous_design_or_coherent_obstruction",
            m, None, 0, base.split_classes, "none", False, None,
            "homogeneous obstruction exceeds exact terminal size; worst-case structural recurrence remains required",
        )

    agg = aggregate_fullness_relation(
        group, blocks, values,
        test_size=3,
        max_test_sets=max_test_sets,
        max_nodes=max_nodes,
        max_class_fraction=max_class_fraction,
    )
    if agg.status in {"undetermined_testset_limit", "undetermined_search_limit"}:
        return ExtendedCanonicalReduction(
            agg.status, m, None, 0, (), "none", False, None, agg.reason,
        )
    pair = refine_pair_codegrees(m, agg.relation, max_class_fraction=max_class_fraction)
    terminal = canonicalize_pair_relation_terminal(
        m, pair.pair_weights,
        max_quotient_size=exact_terminal_size,
        max_states=max_terminal_states,
        max_group_nodes=max_terminal_group_nodes,
    )
    if terminal.status == "exact_pair_relation_canonical_code":
        return ExtendedCanonicalReduction(
            "exact_homogeneous_pair_terminal", m, 1, 1,
            base.split_classes, "exact_terminal", True,
            terminal.canonical_code,
            "small homogeneous pair obstruction resolved by an exact relabeling-invariant canonical code",
        )
    return ExtendedCanonicalReduction(
        terminal.status, m, None, 0, base.split_classes,
        "none", False, None, terminal.reason,
    )
