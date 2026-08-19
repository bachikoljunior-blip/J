from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from orbit_action_preimage_coset_v1 import orbit_action_preimage_coset
from orbit_factored_string_coset_intersection_v1 import _group_orbits, _image_chain
from permutation_group_schreier import compose, inverse
from recursive_point_image_coset_intersection import right_coset_intersection_recursive


@dataclass(frozen=True)
class OrbitFactoredPartialStringIntersection:
    status: str
    coset: Optional[RightCoset]
    active_points: Tuple[int, ...]
    orbit_children: Tuple[Tuple[int, ...], ...]
    active_orbit_children: Tuple[Tuple[int, ...], ...]
    skipped_orbits: Tuple[Tuple[int, ...], ...]
    child_search_nodes: Tuple[int, ...]
    largest_active_child_domain: int
    initial_subgroup_order: int
    final_subgroup_order: int
    reason: str


def orbit_factored_partial_string_coset_intersection(
    candidate: RightCoset,
    values,
    active_points,
    *,
    max_child_nodes=200000,
) -> OrbitFactoredPartialStringIntersection:
    """Intersect a coset with a string segment over an invariant active domain.

    The active set must be invariant under the whole candidate coset.  Initial
    subgroup orbits wholly outside the active set carry no string constraint and
    are therefore skipped rather than sent to a potentially large opaque SI
    terminal.  Orbits inside the active set are solved exactly by the same
    orbit-image / paired-Schreier preimage composition as rev157.

    This is the execution primitive needed by Babai's growing-beard local
    certificates step: the beard is a union of affected orbits, while unaffected
    points are intentionally ignored until they either become affected or are
    fixed pointwise by the Unaffected Stabilizer theorem at the stable stage.
    """
    vals = tuple(values)
    H0 = candidate.subgroup
    n = H0.degree
    if len(vals) != n or len(candidate.representative) != n:
        raise ValueError("string/coset degree mismatch")

    active = tuple(sorted(set(int(x) for x in active_points)))
    if any(x < 0 or x >= n for x in active):
        raise ValueError("active point outside domain")
    A = set(active)
    r0 = candidate.representative
    if {r0[x] for x in A} != A:
        return OrbitFactoredPartialStringIntersection(
            "active_domain_not_coset_invariant", None, active, (), (), (), (),
            0, H0.order, 0,
            "candidate representative does not preserve the active string segment setwise",
        )

    initial_orbits = _group_orbits(H0)
    for O in initial_orbits:
        overlap = set(O) & A
        if overlap and overlap != set(O):
            return OrbitFactoredPartialStringIntersection(
                "active_domain_not_subgroup_invariant", None, active,
                initial_orbits, (), (), (), 0, H0.order, 0,
                "active set cuts an initial subgroup orbit; exact orbit factoring would not be valid",
            )

    active_orbits = tuple(O for O in initial_orbits if set(O) <= A)
    skipped = tuple(O for O in initial_orbits if set(O).isdisjoint(A))
    H = H0
    r = r0
    node_counts = []

    for O in active_orbits:
        image = _image_chain(H, O)
        rinv = inverse(r)
        local_source = tuple(vals[rinv[j]] for j in O)
        local_target = tuple(vals[j] for j in O)
        value_coset = _all_value_preserving_maps(local_source, local_target)
        if value_coset is None:
            return OrbitFactoredPartialStringIntersection(
                "empty_intersection_local_value_multiplicity", None, active,
                initial_orbits, active_orbits, skipped, tuple(node_counts),
                max(map(len, active_orbits), default=0), H0.order, 0,
                "one active invariant orbit has incompatible source/target value multiplicities",
            )

        child = right_coset_intersection_recursive(
            RightCoset(image, tuple(range(len(O)))),
            value_coset,
            max_nodes=max_child_nodes,
        )
        node_counts.append(child.search_nodes)
        if child.status == "undetermined_node_limit":
            return OrbitFactoredPartialStringIntersection(
                "undetermined_child_intersection_limit", None, active,
                initial_orbits, active_orbits, skipped, tuple(node_counts),
                max(map(len, active_orbits), default=0), H0.order, 0,
                "active invariant-orbit child SI exceeded max_child_nodes",
            )
        if child.status == "empty_intersection":
            return OrbitFactoredPartialStringIntersection(
                "empty_intersection", None, active, initial_orbits,
                active_orbits, skipped, tuple(node_counts),
                max(map(len, active_orbits), default=0), H0.order, 0,
                "one active invariant-orbit child has no compatible action image",
            )
        if child.status != "exact_intersection_coset" or child.coset is None:
            return OrbitFactoredPartialStringIntersection(
                "undetermined_child_status", None, active, initial_orbits,
                active_orbits, skipped, tuple(node_counts),
                max(map(len, active_orbits), default=0), H0.order, 0,
                "unexpected active child intersection status; fail closed",
            )

        lifted = orbit_action_preimage_coset(H, O, child.coset)
        if lifted.status != "exact_orbit_action_coset_preimage" or lifted.coset is None:
            return OrbitFactoredPartialStringIntersection(
                "undetermined_child_preimage", None, active, initial_orbits,
                active_orbits, skipped, tuple(node_counts),
                max(map(len, active_orbits), default=0), H0.order, 0,
                "active child coset could not be lifted exactly to the current subgroup",
            )
        H = lifted.subgroup
        r = compose(r, lifted.representative)

    return OrbitFactoredPartialStringIntersection(
        "exact_orbit_factored_partial_string_intersection",
        RightCoset(H, r), active, initial_orbits, active_orbits, skipped,
        tuple(node_counts), max(map(len, active_orbits), default=0),
        H0.order, H.order,
        "all and only active invariant-orbit string constraints were solved exactly; inactive orbits were preserved without opaque SI calls",
    )
