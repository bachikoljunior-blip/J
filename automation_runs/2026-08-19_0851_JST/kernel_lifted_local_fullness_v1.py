from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log2
from typing import Optional, Tuple

from block_action_preimage_coset_v1 import block_action_preimage_coset
from coset_stabilizer_primitives import RightCoset
from giant_block_action_certificates import analyze_giant_block_action
from local_fullness_certificates import _alternating_test_generators, _young_group
from permutation_group_schreier import Permutation, group_orbit, identity
from recursive_point_image_coset_intersection import right_coset_intersection_recursive


@dataclass(frozen=True)
class KernelLiftedLocalFullness:
    status: str
    test_set: Tuple[int, ...]
    full: Optional[bool]
    giant_type: Optional[str]
    alternating_generators_checked: int
    missing_generator: Optional[Permutation]
    lift_witnesses: Tuple[Permutation, ...]
    kernel_order: int
    largest_affected_kernel_orbit: int
    affected_orbit_bound_verified: bool
    recursive_intersection_nodes: int
    recursive_intersection_node_cap: int
    logarithmic_test_bound: int
    reason: str


def kernel_lifted_local_fullness(
    group,
    blocks,
    values,
    test_set,
    *,
    max_test_size_factor=2.0,
    max_intersection_nodes=200000,
) -> KernelLiftedLocalFullness:
    """Certify one logarithmic test set via quotient lifts and kernel recursion.

    For every standard 3-cycle generator of A(T), compute the exact G-preimage
    coset under the designated giant block action, then intersect that coset with
    the Young subgroup preserving the full input string.  Nonempty intersection
    gives a genuine global automorphism lift; one empty intersection is an exact
    non-fullness witness.  This avoids constructing Aut_G(x) globally before the
    local test.

    The test-set size is explicitly capped at O(log n), and the giant-action
    certificate audits the affected-kernel orbit theorem.  The recursive node cap
    is recorded as evidence but is not yet a complete asymptotic cost certificate
    for all underlying permutation-group operations; K1 remains responsible for
    closing that accounting gap.
    """
    blocks = tuple(tuple(b) for b in blocks)
    k = len(blocks)
    T = tuple(sorted(set(int(x) for x in test_set)))
    if any(x < 0 or x >= k for x in T):
        raise ValueError("test-set point outside quotient")
    if len(T) < 3:
        raise ValueError("local fullness test requires at least three quotient points")
    n = group.degree
    logarithmic_bound = max(3, ceil(max_test_size_factor * log2(max(2, n))))
    if len(T) > logarithmic_bound:
        return KernelLiftedLocalFullness(
            "test_set_not_logarithmic", T, None, None, 0, None, (), 0, 0,
            False, 0, max_intersection_nodes, logarithmic_bound,
            "test set exceeds the configured O(log n) locality bound",
        )

    giant = analyze_giant_block_action(group, blocks)
    if giant.giant_type is None:
        return KernelLiftedLocalFullness(
            "giant_action_required", T, None, None, 0, None, (), 0, 0,
            False, 0, max_intersection_nodes, logarithmic_bound,
            "designated quotient action is not certified S_k/A_k",
        )
    if not giant.affected_orbit_lemma_verified:
        return KernelLiftedLocalFullness(
            "affected_kernel_bound_unverified", T, None, giant.giant_type,
            0, None, (), giant.kernel_order, 0, False, 0,
            max_intersection_nodes, logarithmic_bound,
            "rev114 affected-orbit kernel bound audit failed",
        )

    young = _young_group(tuple(values))
    string_preservers = RightCoset(young, identity(n))
    alt_gens = _alternating_test_generators(k, T)
    witnesses = []
    total_nodes = 0
    kernel = None

    for q in alt_gens:
        lift = block_action_preimage_coset(group, blocks, q)
        if lift.status != "exact_block_action_preimage_coset":
            return KernelLiftedLocalFullness(
                "giant_generator_lift_failure", T, None, giant.giant_type,
                len(witnesses), q, tuple(witnesses), lift.kernel_order, 0,
                giant.affected_orbit_lemma_verified, total_nodes,
                max_intersection_nodes, logarithmic_bound,
                "a required alternating generator unexpectedly had no certified quotient lift",
            )
        kernel = lift.kernel
        inter = right_coset_intersection_recursive(
            lift.coset, string_preservers, max_nodes=max_intersection_nodes
        )
        total_nodes += inter.search_nodes
        if inter.status == "undetermined_node_limit":
            return KernelLiftedLocalFullness(
                "undetermined_kernel_intersection_limit", T, None,
                giant.giant_type, len(witnesses), q, tuple(witnesses),
                kernel.order, 0, giant.affected_orbit_lemma_verified,
                total_nodes, max_intersection_nodes, logarithmic_bound,
                "kernel/value-preserving coset intersection exhausted its exact node budget",
            )
        if inter.status == "empty_intersection":
            largest = 0
            if kernel is not None:
                largest = max(
                    (len(group_orbit(kernel, x)) for x in giant.affected_points),
                    default=0,
                )
            return KernelLiftedLocalFullness(
                "certified_nonfull_kernel_lift", T, False, giant.giant_type,
                len(witnesses) + 1, q, tuple(witnesses), kernel.order,
                largest, giant.affected_orbit_lemma_verified, total_nodes,
                max_intersection_nodes, logarithmic_bound,
                "one A(T) generator has no global string-automorphism lift inside its exact kernel coset",
            )
        if inter.status != "exact_intersection_coset" or inter.coset is None:
            return KernelLiftedLocalFullness(
                "undetermined_kernel_intersection_status", T, None,
                giant.giant_type, len(witnesses), q, tuple(witnesses),
                kernel.order, 0, giant.affected_orbit_lemma_verified,
                total_nodes, max_intersection_nodes, logarithmic_bound,
                "unexpected exact-intersection status; fail closed",
            )
        witnesses.append(inter.coset.representative)

    if kernel is None:
        raise AssertionError("A(T) generator set unexpectedly empty")
    largest = max(
        (len(group_orbit(kernel, x)) for x in giant.affected_points),
        default=0,
    )
    return KernelLiftedLocalFullness(
        "certified_full_kernel_lift", T, True, giant.giant_type,
        len(alt_gens), None, tuple(witnesses), kernel.order, largest,
        giant.affected_orbit_lemma_verified, total_nodes,
        max_intersection_nodes, logarithmic_bound,
        "every standard A(T) generator has an exact global string-automorphism lift obtained through its quotient-kernel preimage coset",
    )
