from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log2
from typing import Optional, Tuple

from block_action_preimage_coset_v1 import block_action_preimage_coset
from giant_block_action_certificates import analyze_giant_block_action
from local_fullness_certificates import _alternating_test_generators
from orbit_factored_string_coset_intersection_v1 import (
    OrbitFactoredStringIntersection,
    orbit_factored_string_coset_intersection,
)
from permutation_group_schreier import Permutation, group_orbit


@dataclass(frozen=True)
class KernelLiftedLocalFullnessV2:
    status: str
    test_set: Tuple[int, ...]
    full: Optional[bool]
    giant_type: Optional[str]
    alternating_generators_checked: int
    missing_generator: Optional[Permutation]
    lift_witnesses: Tuple[Permutation, ...]
    kernel_order: int
    logarithmic_test_bound: int
    largest_recursive_child_domain: int
    certified_affected_child_bound: int
    all_recursive_children_affected: bool
    recurrence_child_bound_verified: bool
    child_intersection_nodes: Tuple[int, ...]
    reason: str


def _child_cost_evidence(giant, factor: OrbitFactoredStringIntersection):
    affected = set(giant.affected_points)
    all_affected = all(set(O) <= affected for O in factor.orbit_children)
    bound = ceil(giant.largest_group_orbit / giant.block_count)
    verified = (
        giant.affected_orbit_lemma_verified
        and all_affected
        and factor.largest_child_domain <= bound
    )
    return all_affected, bound, verified


def kernel_lifted_local_fullness_v2(
    group,
    blocks,
    values,
    test_set,
    *,
    max_test_size_factor=2.0,
    max_child_nodes=200000,
) -> KernelLiftedLocalFullnessV2:
    """Local fullness with the hard string intersection executed by orbit children.

    As in rev153, every standard generator of A(T) is lifted through the exact
    quotient-kernel preimage coset.  Unlike rev153, the lift coset is *not*
    intersected with the full-domain Young group by the opaque global point-image
    recursion.  rev157 factors that exact intersection over invariant kernel-orbit
    String-Isomorphism children and rev156 lifts every exact child coset back to
    the full domain before the next child is imposed.

    Correctness of fullness/non-fullness is exact independently of the complexity
    flag.  `recurrence_child_bound_verified` is stricter: it is true only when all
    actual child orbits lie in the certified affected set and obey rev114's
    affected-kernel orbit bound.  Inputs with unaffected children remain exact but
    are not accepted as quasipolynomial recurrence evidence; Q1 must route those
    through the Unaffected Stabilizers path rather than hiding them in a flat cost.
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
        return KernelLiftedLocalFullnessV2(
            "test_set_not_logarithmic", T, None, None, 0, None, (), 0,
            logarithmic_bound, 0, 0, False, False, (),
            "test set exceeds the configured O(log n) locality bound",
        )

    giant = analyze_giant_block_action(group, blocks)
    if giant.giant_type is None:
        return KernelLiftedLocalFullnessV2(
            "giant_action_required", T, None, None, 0, None, (), 0,
            logarithmic_bound, 0, 0, False, False, (),
            "designated quotient action is not certified S_k/A_k",
        )
    if not giant.affected_orbit_lemma_verified:
        return KernelLiftedLocalFullnessV2(
            "affected_kernel_bound_unverified", T, None, giant.giant_type,
            0, None, (), giant.kernel_order, logarithmic_bound, 0, 0,
            False, False, (),
            "rev114 affected-kernel orbit bound audit failed",
        )

    alt_gens = _alternating_test_generators(k, T)
    witnesses = []
    all_nodes = []
    kernel_order = giant.kernel_order
    max_child = 0
    child_bound = ceil(giant.largest_group_orbit / k)
    all_children_affected = True
    recurrence_verified = True

    for q in alt_gens:
        lift = block_action_preimage_coset(group, blocks, q)
        if lift.status != "exact_block_action_preimage_coset" or lift.coset is None:
            return KernelLiftedLocalFullnessV2(
                "giant_generator_lift_failure", T, None, giant.giant_type,
                len(witnesses), q, tuple(witnesses), lift.kernel_order,
                logarithmic_bound, max_child, child_bound,
                all_children_affected, False, tuple(all_nodes),
                "a required alternating generator had no certified quotient lift",
            )
        kernel_order = lift.kernel_order
        factored = orbit_factored_string_coset_intersection(
            lift.coset, values, max_child_nodes=max_child_nodes
        )
        max_child = max(max_child, factored.largest_child_domain)
        all_nodes.extend(factored.child_search_nodes)
        current_all_affected, current_bound, current_verified = _child_cost_evidence(
            giant, factored
        )
        child_bound = current_bound
        all_children_affected = all_children_affected and current_all_affected
        recurrence_verified = recurrence_verified and current_verified

        if factored.status == "undetermined_child_intersection_limit":
            return KernelLiftedLocalFullnessV2(
                "undetermined_orbit_child_limit", T, None, giant.giant_type,
                len(witnesses), q, tuple(witnesses), kernel_order,
                logarithmic_bound, max_child, child_bound,
                all_children_affected, False, tuple(all_nodes),
                "an exact invariant-orbit child SI search exceeded max_child_nodes",
            )
        if factored.status in {
            "empty_intersection",
            "empty_intersection_local_value_multiplicity",
        }:
            return KernelLiftedLocalFullnessV2(
                "certified_nonfull_orbit_factored", T, False, giant.giant_type,
                len(witnesses) + 1, q, tuple(witnesses), kernel_order,
                logarithmic_bound, max_child, child_bound,
                all_children_affected, recurrence_verified, tuple(all_nodes),
                "one A(T) generator has no global string-automorphism lift; exact emptiness was proved through invariant-orbit child SI cosets",
            )
        if factored.status != "exact_orbit_factored_string_intersection" or factored.coset is None:
            return KernelLiftedLocalFullnessV2(
                "undetermined_orbit_factored_status", T, None,
                giant.giant_type, len(witnesses), q, tuple(witnesses),
                kernel_order, logarithmic_bound, max_child, child_bound,
                all_children_affected, False, tuple(all_nodes),
                "unexpected orbit-factored exact-intersection status; fail closed",
            )
        witnesses.append(factored.coset.representative)

    return KernelLiftedLocalFullnessV2(
        "certified_full_orbit_factored", T, True, giant.giant_type,
        len(alt_gens), None, tuple(witnesses), kernel_order,
        logarithmic_bound, max_child, child_bound,
        all_children_affected, recurrence_verified, tuple(all_nodes),
        "every A(T) generator has a genuine global string-automorphism lift, with the hard exact intersection executed by invariant-orbit child SI cosets",
    )
