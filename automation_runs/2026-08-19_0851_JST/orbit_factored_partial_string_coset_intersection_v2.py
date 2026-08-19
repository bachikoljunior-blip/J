from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from coset_stabilizer_primitives import RightCoset
from orbit_action_preimage_coset_v1 import orbit_action_preimage_coset
from orbit_factored_string_coset_intersection_v1 import _group_orbits, _image_chain
from permutation_group_schreier import compose, inverse
from proof_carrying_string_child_dispatch_v1 import (
    ProofCarryingStringChild,
    proof_carrying_string_child_dispatch,
)


@dataclass(frozen=True)
class OrbitFactoredPartialStringIntersectionV2:
    status: str
    coset: Optional[RightCoset]
    active_points: Tuple[int, ...]
    active_orbit_children: Tuple[Tuple[int, ...], ...]
    skipped_orbits: Tuple[Tuple[int, ...], ...]
    child_proofs: Tuple[ProofCarryingStringChild, ...]
    largest_active_child_domain: int
    all_children_proof_carrying: bool
    reason: str


def orbit_factored_partial_string_coset_intersection_v2(
    candidate: RightCoset,
    values,
    active_points,
    *,
    primary_domain_size: Optional[int] = None,
    polylog_power: int = 2,
    max_terminal_nodes: int = 500000,
) -> OrbitFactoredPartialStringIntersectionV2:
    """rev161 affected-orbit executor with mandatory proof-carrying child dispatch.

    The exact orbit factoring/lifting semantics are unchanged.  The difference is
    at the actual child SI call: every local orbit child is passed to rev163's
    typed dispatcher.  A mechanically small child may terminate with an exact
    coset and closed-form cost node.  A larger child returns a structural recursive
    obligation and this parent fails closed with `requires_recursive_child_dispatch`.
    It never silently falls back to the old node-capped exact SI terminal.
    """
    vals = tuple(values)
    H0 = candidate.subgroup
    n = H0.degree
    primary_n = n if primary_domain_size is None else int(primary_domain_size)
    if primary_n < n:
        raise ValueError("primary domain must be at least the current domain")
    if len(vals) != n or len(candidate.representative) != n:
        raise ValueError("string/coset degree mismatch")

    active = tuple(sorted(set(int(x) for x in active_points)))
    if any(x < 0 or x >= n for x in active):
        raise ValueError("active point outside domain")
    A = set(active)
    if {candidate.representative[x] for x in A} != A:
        return OrbitFactoredPartialStringIntersectionV2(
            "active_domain_not_coset_invariant", None, active, (), (), (),
            0, False,
            "candidate representative does not preserve the active segment setwise",
        )

    initial_orbits = _group_orbits(H0)
    for O in initial_orbits:
        overlap = set(O) & A
        if overlap and overlap != set(O):
            return OrbitFactoredPartialStringIntersectionV2(
                "active_domain_not_subgroup_invariant", None, active, (), (), (),
                0, False,
                "active set cuts an initial subgroup orbit; orbit factoring is invalid",
            )

    active_orbits = tuple(O for O in initial_orbits if set(O) <= A)
    skipped = tuple(O for O in initial_orbits if set(O).isdisjoint(A))
    H = H0
    r = candidate.representative
    proofs = []
    largest = 0

    for O in active_orbits:
        largest = max(largest, len(O))
        image = _image_chain(H, O)
        rinv = inverse(r)
        local_source = tuple(vals[rinv[j]] for j in O)
        local_target = tuple(vals[j] for j in O)
        child = proof_carrying_string_child_dispatch(
            RightCoset(image, tuple(range(len(O)))),
            local_source,
            local_target,
            primary_domain_size=primary_n,
            polylog_power=polylog_power,
            max_terminal_nodes=max_terminal_nodes,
        )
        proofs.append(child)

        if child.status in {
            "exact_empty_value_multiplicity",
            "exact_empty_small_terminal",
        }:
            return OrbitFactoredPartialStringIntersectionV2(
                "empty_intersection", None, active, active_orbits, skipped,
                tuple(proofs), largest, True,
                "one active child is exactly empty with its proof-carrying terminal evidence",
            )
        if not child.exact:
            return OrbitFactoredPartialStringIntersectionV2(
                "requires_recursive_child_dispatch", None, active,
                active_orbits, skipped, tuple(proofs), largest, False,
                "a non-small active child requires structural R1 recursion; no opaque exact terminal was executed",
            )
        if child.coset is None:
            return OrbitFactoredPartialStringIntersectionV2(
                "undetermined_child_proof_status", None, active,
                active_orbits, skipped, tuple(proofs), largest, False,
                "exact nonempty child omitted its coset; fail closed",
            )

        lifted = orbit_action_preimage_coset(H, O, child.coset)
        if lifted.status != "exact_orbit_action_coset_preimage" or lifted.coset is None:
            return OrbitFactoredPartialStringIntersectionV2(
                "undetermined_child_preimage", None, active,
                active_orbits, skipped, tuple(proofs), largest, False,
                "proof-carrying child coset could not be lifted exactly",
            )
        H = lifted.subgroup
        r = compose(r, lifted.representative)

    return OrbitFactoredPartialStringIntersectionV2(
        "exact_proof_carrying_partial_string_intersection",
        RightCoset(H, r), active, active_orbits, skipped, tuple(proofs),
        largest, all(p.exact and p.terminal_cost_certified for p in proofs),
        "every executed active child returned an exact proof-carrying terminal object; inactive orbits were skipped",
    )
