from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from orbit_action_preimage_coset_v1 import orbit_action_preimage_coset
from orbit_factored_string_coset_intersection_v1 import _group_orbits, _image_chain
from permutation_group_schreier import compose, inverse
from proof_carrying_si_v1 import ProofCarryingCoset, r1_string_isomorphism_child


@dataclass(frozen=True)
class OrbitFactoredPartialStringIntersectionV2:
    status: str
    coset: Optional[RightCoset]
    active_points: Tuple[int, ...]
    orbit_children: Tuple[Tuple[int, ...], ...]
    active_orbit_children: Tuple[Tuple[int, ...], ...]
    skipped_orbits: Tuple[Tuple[int, ...], ...]
    child_proofs: Tuple[ProofCarryingCoset, ...]
    largest_active_child_domain: int
    initial_subgroup_order: int
    final_subgroup_order: int
    exact: bool
    reason: str


def orbit_factored_partial_string_coset_intersection_v2(
    candidate: RightCoset,
    values,
    active_points,
    *,
    root_n: Optional[int] = None,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
) -> OrbitFactoredPartialStringIntersectionV2:
    """Proof-carrying replacement for rev161's affected kernel-orbit executor.

    The exact coset algebra is unchanged from v1, but every active kernel-orbit
    child is now executed by R1 and the returned proof object is retained.  A
    child outside the certified small terminal window is *not* sent to the old
    resource-bounded point-image terminal.  The whole parent fails closed with
    the unresolved child proof attached, so execution and recurrence evidence
    cannot drift apart.
    """
    vals = tuple(values)
    H0 = candidate.subgroup
    n = H0.degree
    if len(vals) != n or len(candidate.representative) != n:
        raise ValueError("string/coset degree mismatch")
    if root_n is None:
        root_n = n
    if root_n < n:
        raise ValueError("root_n must dominate the current domain")

    active = tuple(sorted(set(int(x) for x in active_points)))
    if any(x < 0 or x >= n for x in active):
        raise ValueError("active point outside domain")
    A = set(active)
    r0 = candidate.representative
    if {r0[x] for x in A} != A:
        return OrbitFactoredPartialStringIntersectionV2(
            "active_domain_not_coset_invariant", None, active, (), (), (), (),
            0, H0.order, 0, False,
            "candidate representative does not preserve the active string segment setwise",
        )

    initial_orbits = _group_orbits(H0)
    for O in initial_orbits:
        overlap = set(O) & A
        if overlap and overlap != set(O):
            return OrbitFactoredPartialStringIntersectionV2(
                "active_domain_not_subgroup_invariant", None, active,
                initial_orbits, (), (), (), 0, H0.order, 0, False,
                "active set cuts an initial subgroup orbit; exact orbit factoring would not be valid",
            )

    active_orbits = tuple(O for O in initial_orbits if set(O) <= A)
    skipped = tuple(O for O in initial_orbits if set(O).isdisjoint(A))
    H = H0
    r = r0
    proofs = []

    for O in active_orbits:
        image = _image_chain(H, O)
        rinv = inverse(r)
        local_source = tuple(vals[rinv[j]] for j in O)
        local_target = tuple(vals[j] for j in O)
        # Fast canonical multiplicity rejection remains duplicated here only to
        # avoid constructing an irrelevant R1 group child when no value map exists.
        if _all_value_preserving_maps(local_source, local_target) is None:
            proof = r1_string_isomorphism_child(
                image, local_source, local_target, root_n=root_n,
                polylog_power=polylog_power,
                max_explicit_degree=max_explicit_degree,
            )
            proofs.append(proof)
            return OrbitFactoredPartialStringIntersectionV2(
                "empty_intersection_local_value_multiplicity", None, active,
                initial_orbits, active_orbits, skipped, tuple(proofs),
                max(map(len, active_orbits), default=0), H0.order, 0, True,
                "one active invariant orbit has an exact proof-carrying value-multiplicity obstruction",
            )

        child = r1_string_isomorphism_child(
            image, local_source, local_target, root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
        )
        proofs.append(child)
        if not child.exact:
            return OrbitFactoredPartialStringIntersectionV2(
                child.status, None, active, initial_orbits, active_orbits, skipped,
                tuple(proofs), max(map(len, active_orbits), default=0),
                H0.order, 0, False,
                "an actual affected kernel-orbit child requires unresolved structural R1 recursion; no opaque exact terminal was substituted",
            )
        if child.coset is None:
            return OrbitFactoredPartialStringIntersectionV2(
                "empty_intersection", None, active, initial_orbits,
                active_orbits, skipped, tuple(proofs),
                max(map(len, active_orbits), default=0), H0.order, 0, True,
                "one proof-carrying active invariant-orbit child is exactly empty",
            )

        lifted = orbit_action_preimage_coset(H, O, child.coset)
        if lifted.status != "exact_orbit_action_coset_preimage" or lifted.coset is None:
            return OrbitFactoredPartialStringIntersectionV2(
                "undetermined_child_preimage", None, active, initial_orbits,
                active_orbits, skipped, tuple(proofs),
                max(map(len, active_orbits), default=0), H0.order, 0, False,
                "proof-carrying child coset could not be lifted exactly to the current subgroup",
            )
        H = lifted.subgroup
        r = compose(r, lifted.representative)

    return OrbitFactoredPartialStringIntersectionV2(
        "exact_orbit_factored_partial_string_intersection", RightCoset(H, r),
        active, initial_orbits, active_orbits, skipped, tuple(proofs),
        max(map(len, active_orbits), default=0), H0.order, H.order, True,
        "all active invariant-orbit constraints were solved by exact R1 child proof objects and lifted by paired Schreier preimages; inactive orbits were skipped",
    )
