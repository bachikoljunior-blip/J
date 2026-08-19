from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from master_canonical_reduction_v3 import master_canonical_reduction_v3
from primitive_orbital_reduction import reduce_primitive_quotient_by_orbital_sizes


@dataclass(frozen=True)
class PrimitiveExtendedReduction:
    status: str
    original_domain_size: int
    reduced_domain_size: Optional[int]
    branch_count: int
    split_classes: Tuple[Tuple[int, ...], ...]
    progress_kind: str
    progress_verified: bool
    terminal_canonical_code: Optional[bytes]
    johnson_ground_size: Optional[int]
    johnson_subset_size: Optional[int]
    reason: str


def master_canonical_reduction_v4(
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
) -> PrimitiveExtendedReduction:
    """Extend rev132's primitive child with canonical orbital-size structure."""
    base = master_canonical_reduction_v3(
        group, blocks, values,
        max_nodes=max_nodes,
        max_test_sets=max_test_sets,
        max_class_fraction=max_class_fraction,
        max_johnson_nodes=max_johnson_nodes,
        exact_terminal_size=exact_terminal_size,
        max_terminal_states=max_terminal_states,
        max_terminal_group_nodes=max_terminal_group_nodes,
    )
    if base.status != "primitive_quotient_action":
        return PrimitiveExtendedReduction(
            base.status, base.original_domain_size, base.reduced_domain_size,
            base.branch_count, base.split_classes, base.progress_kind,
            base.progress_verified, base.terminal_canonical_code,
            None, None, base.reason,
        )

    primitive = reduce_primitive_quotient_by_orbital_sizes(
        group, blocks, values,
        max_nodes=max_nodes,
        max_class_fraction=max_class_fraction,
        max_johnson_nodes=max_johnson_nodes,
    )
    if primitive.progress_verified:
        return PrimitiveExtendedReduction(
            primitive.status,
            base.original_domain_size,
            primitive.reduced_domain_size,
            1,
            primitive.split_classes,
            "primitive_orbital_structure",
            True,
            None,
            primitive.johnson_ground_size,
            primitive.johnson_subset_size,
            primitive.reason,
        )
    return PrimitiveExtendedReduction(
        primitive.status,
        base.original_domain_size,
        None,
        0,
        primitive.split_classes,
        "none",
        False,
        None,
        None,
        None,
        primitive.reason,
    )
