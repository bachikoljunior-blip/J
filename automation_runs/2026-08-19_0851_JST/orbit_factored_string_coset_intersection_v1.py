from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from orbit_action_preimage_coset_v1 import orbit_action, orbit_action_preimage_coset
from permutation_group_schreier import (
    StabilizerChain,
    compose,
    group_orbit,
    identity,
    inverse,
    schreier_stabilizer_chain,
)
from recursive_point_image_coset_intersection import right_coset_intersection_recursive


@dataclass(frozen=True)
class OrbitFactoredStringIntersection:
    status: str
    coset: Optional[RightCoset]
    initial_subgroup_order: int
    final_subgroup_order: int
    orbit_children: Tuple[Tuple[int, ...], ...]
    child_search_nodes: Tuple[int, ...]
    largest_child_domain: int
    reason: str


def _group_orbits(group: StabilizerChain):
    remaining = set(range(group.degree))
    out = []
    while remaining:
        x = min(remaining)
        O = tuple(sorted(group_orbit(group, x)))
        out.append(O)
        remaining -= set(O)
    return tuple(sorted(out, key=lambda O: (len(O), O)))


def _image_chain(group: StabilizerChain, orbit):
    m = len(orbit)
    gens = group.original_generators or (identity(group.degree),)
    images = [orbit_action(g, orbit) for g in gens]
    return schreier_stabilizer_chain(images or [identity(m)])


def orbit_factored_string_coset_intersection(
    candidate: RightCoset,
    values,
    *,
    max_child_nodes=200000,
) -> OrbitFactoredStringIntersection:
    """Intersect a coset with one string by exact invariant-orbit children.

    Let the current candidate set be H*r in the repository's RightCoset
    convention (apply representative r, then an element of H).  Every H-orbit is
    invariant, so the value constraint can be imposed orbit by orbit.  On one
    orbit O, source values are pulled through r^{-1}; the small action image H^O
    is intersected exactly with all local source->target value maps.  rev156 then
    lifts that exact child coset to its exact full-domain preimage in H.  Replacing
    H*r by the lifted subgroup and composed representative preserves all earlier
    orbit constraints.  After every initial H-orbit is processed, the result is
    exactly the original candidate coset intersected with the Young subgroup of
    `values`.

    The only exponential-style exact search in this executor is performed on the
    child orbit domains and its node counts are exposed.  Paired-Schreier lifting
    and global quasipolynomial accounting still require separate certified cost
    closure; this routine does not claim Q1/Q2 complete by itself.
    """
    vals = tuple(values)
    H0 = candidate.subgroup
    n = H0.degree
    if len(vals) != n or len(candidate.representative) != n:
        raise ValueError("string/coset degree mismatch")

    initial_orbits = _group_orbits(H0)
    H = H0
    r = candidate.representative
    node_counts = []

    for O in initial_orbits:
        # Every later H is a subgroup of H0, hence each initial H0 orbit remains
        # invariant even if it splits further.
        try:
            image = _image_chain(H, O)
        except ValueError as exc:
            raise AssertionError("constrained subgroup escaped initial invariant orbit") from exc

        rinv = inverse(r)
        local_source = tuple(vals[rinv[j]] for j in O)
        local_target = tuple(vals[j] for j in O)
        value_coset = _all_value_preserving_maps(local_source, local_target)
        if value_coset is None:
            return OrbitFactoredStringIntersection(
                "empty_intersection_local_value_multiplicity",
                None,
                H0.order,
                0,
                initial_orbits,
                tuple(node_counts),
                max(map(len, initial_orbits), default=0),
                "one invariant orbit has incompatible pulled-source/target value multiplicities",
            )

        child = right_coset_intersection_recursive(
            RightCoset(image, identity(len(O))),
            value_coset,
            max_nodes=max_child_nodes,
        )
        node_counts.append(child.search_nodes)
        if child.status == "undetermined_node_limit":
            return OrbitFactoredStringIntersection(
                "undetermined_child_intersection_limit",
                None,
                H0.order,
                0,
                initial_orbits,
                tuple(node_counts),
                max(map(len, initial_orbits), default=0),
                "exact child String-Isomorphism search exceeded max_child_nodes",
            )
        if child.status == "empty_intersection":
            return OrbitFactoredStringIntersection(
                "empty_intersection",
                None,
                H0.order,
                0,
                initial_orbits,
                tuple(node_counts),
                max(map(len, initial_orbits), default=0),
                "one invariant-orbit child has no compatible action image",
            )
        if child.status != "exact_intersection_coset" or child.coset is None:
            return OrbitFactoredStringIntersection(
                "undetermined_child_status",
                None,
                H0.order,
                0,
                initial_orbits,
                tuple(node_counts),
                max(map(len, initial_orbits), default=0),
                "unexpected child exact-intersection status; fail closed",
            )

        lifted = orbit_action_preimage_coset(H, O, child.coset)
        if lifted.status != "exact_orbit_action_coset_preimage" or lifted.coset is None:
            return OrbitFactoredStringIntersection(
                "undetermined_child_preimage",
                None,
                H0.order,
                0,
                initial_orbits,
                tuple(node_counts),
                max(map(len, initial_orbits), default=0),
                "child coset could not be lifted exactly to the current full-domain subgroup",
            )

        # child preimage D = L*s is a subset of current H.  Original candidates
        # are H*r; imposing D changes them to L*(r then s).
        H = lifted.subgroup
        r = compose(r, lifted.representative)

    result = RightCoset(H, r)
    return OrbitFactoredStringIntersection(
        "exact_orbit_factored_string_intersection",
        result,
        H0.order,
        H.order,
        initial_orbits,
        tuple(node_counts),
        max(map(len, initial_orbits), default=0),
        "all invariant-orbit child SI cosets were solved exactly, lifted by paired Schreier preimages, and composed without a full-domain point-image intersection search",
    )
