from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from master_canonical_reduction_v4 import master_canonical_reduction_v4
from regular_prime_quotient_terminal import regular_prime_quotient_terminal


@dataclass(frozen=True)
class RegularPrimeExtendedReduction:
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
    regular_prime_coordinate_systems: int
    reason: str


def master_canonical_reduction_v5(
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
    max_regular_coordinate_systems=200000,
    max_regular_group_elements=200000,
) -> RegularPrimeExtendedReduction:
    """Resolve rev135's regular-prime primitive child with an exact affine terminal.

    Every rev135 branch remains unchanged unless it ends in the explicit
    `primitive_orbital_relation_unresolved` state.  That child is then tested for
    an exact transitive prime-order quotient and, if present, the canonical
    3-subset local-certificate relation is minimized over all p(p-1) affine
    coordinate systems.  Failure of any resource/certification gate remains
    fail-closed and does not manufacture progress.
    """
    base = master_canonical_reduction_v4(
        group, blocks, values,
        max_nodes=max_nodes,
        max_test_sets=max_test_sets,
        max_class_fraction=max_class_fraction,
        max_johnson_nodes=max_johnson_nodes,
        exact_terminal_size=exact_terminal_size,
        max_terminal_states=max_terminal_states,
        max_terminal_group_nodes=max_terminal_group_nodes,
    )
    if base.status != "primitive_orbital_relation_unresolved":
        return RegularPrimeExtendedReduction(
            base.status,
            base.original_domain_size,
            base.reduced_domain_size,
            base.branch_count,
            base.split_classes,
            base.progress_kind,
            base.progress_verified,
            base.terminal_canonical_code,
            base.johnson_ground_size,
            base.johnson_subset_size,
            0,
            base.reason,
        )

    terminal = regular_prime_quotient_terminal(
        group, blocks, values,
        max_nodes=max_nodes,
        max_test_sets=max_test_sets,
        max_coordinate_systems=max_regular_coordinate_systems,
        max_group_elements=max_regular_group_elements,
    )
    if terminal.status == "exact_regular_prime_quotient_terminal":
        return RegularPrimeExtendedReduction(
            "primitive_regular_prime_exact_terminal",
            base.original_domain_size,
            1,
            1,
            base.split_classes,
            "regular_prime_affine_terminal",
            True,
            terminal.canonical_code,
            None,
            None,
            terminal.coordinate_systems_checked,
            terminal.reason,
        )

    return RegularPrimeExtendedReduction(
        base.status,
        base.original_domain_size,
        None,
        0,
        base.split_classes,
        "none",
        False,
        None,
        None,
        None,
        terminal.coordinate_systems_checked,
        base.reason + "; regular-prime terminal unavailable: " + terminal.status + " — " + terminal.reason,
    )
