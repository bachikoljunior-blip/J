from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from master_canonical_reduction_v2 import master_canonical_reduction_v2
from quotient_imprimitivity_reduction import reduce_quotient_imprimitivity


@dataclass(frozen=True)
class ImprimitivityExtendedReduction:
    status: str
    original_domain_size: int
    reduced_domain_size: Optional[int]
    branch_count: int
    split_classes: Tuple[Tuple[int, ...], ...]
    progress_kind: str
    progress_verified: bool
    terminal_canonical_code: Optional[bytes]
    reason: str


def master_canonical_reduction_v3(
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
) -> ImprimitivityExtendedReduction:
    """Extend rev129's large homogeneous branch with exact quotient imprimitivity.

    rev129 is left unchanged for all already solved branches. Only a large
    homogeneous design/coherent obstruction proceeds to the exact quotient
    automorphism action. Intransitive quotient orbits and a unique canonical
    minimum block system both give a strict domain decomposition. Primitive
    actions and multiple equally minimal block systems remain explicit children.
    """
    base = master_canonical_reduction_v2(
        group, blocks, values,
        max_nodes=max_nodes,
        max_test_sets=max_test_sets,
        max_class_fraction=max_class_fraction,
        max_johnson_nodes=max_johnson_nodes,
        exact_terminal_size=exact_terminal_size,
        max_terminal_states=max_terminal_states,
        max_terminal_group_nodes=max_terminal_group_nodes,
    )
    if base.status != "unresolved_large_homogeneous_design_or_coherent_obstruction":
        return ImprimitivityExtendedReduction(
            base.status, base.original_domain_size, base.reduced_domain_size,
            base.branch_count, base.split_classes, base.progress_kind,
            base.progress_verified, base.terminal_canonical_code, base.reason,
        )

    reduction = reduce_quotient_imprimitivity(
        group, blocks, values, max_nodes=max_nodes
    )
    m = base.original_domain_size
    if reduction.status in {
        "canonical_intransitive_quotient_split",
        "unique_canonical_imprimitive_quotient",
    }:
        partition = reduction.block_system
        largest = max(map(len, partition), default=m)
        return ImprimitivityExtendedReduction(
            reduction.status, m, largest, len(partition), partition,
            "quotient_block_decomposition", largest < m,
            None, reduction.reason,
        )
    if reduction.status == "multiple_minimal_quotient_block_systems":
        return ImprimitivityExtendedReduction(
            reduction.status, m, None, reduction.alternative_minimal_system_count,
            (), "none", False, None, reduction.reason,
        )
    return ImprimitivityExtendedReduction(
        reduction.status, m, None, 0, (), "none", False, None, reduction.reason,
    )
