from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Hashable, Iterable

from coset_stabilizer_primitives import RightCoset
from paired_action_coset_preimage_v1 import paired_action_coset_preimage
from paired_bipartite_right_partition_provenance_v1 import _canonical_atom
from permutation_group_schreier import (
    compose,
    identity,
    schreier_stabilizer_chain,
    validate_perm,
)
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2

Subset = tuple[int, ...]
ColorToken = tuple[tuple[tuple, int], ...]


@dataclass(frozen=True)
class BipartiteNeighborhoodCosetIntersection:
    status: str
    right_degree: int
    left_size: int
    subset_state_count: int
    image_group_order: int
    candidate_status: str | None
    source_left_color_inventory: tuple[tuple[tuple, int], ...]
    target_left_color_inventory: tuple[tuple[tuple, int], ...]
    coset: RightCoset | None
    exact: bool
    exact_empty: bool
    full_left_color_symmetric_model: bool
    parent_left_action_verified: bool
    quasipolynomial_cost_certified: bool
    reason: str


def _normalize_edges(left_size: int, right_size: int, edges: Iterable[tuple[int, int]]) -> tuple[Subset, ...]:
    neighborhoods = [set() for _ in range(left_size)]
    for a, b in edges:
        a = int(a)
        b = int(b)
        if not 0 <= a < left_size or not 0 <= b < right_size:
            raise ValueError("edge endpoint outside declared bipartite parts")
        neighborhoods[a].add(b)
    return tuple(tuple(sorted(xs)) for xs in neighborhoods)


def _colors(left_size: int, colors: Iterable[Hashable] | None) -> tuple[tuple, ...]:
    raw = tuple(0 for _ in range(left_size)) if colors is None else tuple(colors)
    if len(raw) != left_size:
        raise ValueError("left color sequence length mismatch")
    return tuple(_canonical_atom(value) for value in raw)


def _inventory(colors: tuple[tuple, ...]) -> tuple[tuple[tuple, int], ...]:
    return tuple(sorted(Counter(colors).items()))


def _map_subset(subset: Subset, perm) -> Subset:
    return tuple(sorted(perm[x] for x in subset))


def _orbit_closed_subset_domain(
    seeds: Iterable[Subset],
    generators,
    *,
    max_subset_states: int,
) -> tuple[Subset, ...] | None:
    if max_subset_states < 1:
        raise ValueError("max_subset_states must be positive")
    seen = {tuple(sorted(S)) for S in seeds}
    if len(seen) > max_subset_states:
        return None
    queue = deque(sorted(seen, key=lambda S: (len(S), S)))
    while queue:
        S = queue.popleft()
        for g in generators:
            T = _map_subset(S, g)
            if T in seen:
                continue
            if len(seen) >= max_subset_states:
                return None
            seen.add(T)
            queue.append(T)
    return tuple(sorted(seen, key=lambda S: (len(S), S)))


def _induced_generators(coords: tuple[Subset, ...], generators) -> tuple[tuple[int, ...], ...]:
    index = {S: i for i, S in enumerate(coords)}
    images = []
    for g in generators:
        q = tuple(index[_map_subset(S, g)] for S in coords)
        images.append(validate_perm(q))
    return tuple(images)


def _family_string(
    coords: tuple[Subset, ...],
    neighborhoods: tuple[Subset, ...],
    colors: tuple[tuple, ...],
) -> tuple[ColorToken, ...]:
    buckets: dict[Subset, Counter] = {S: Counter() for S in coords}
    for S, color in zip(neighborhoods, colors):
        if S not in buckets:
            raise AssertionError("neighborhood escaped the orbit-closed subset domain")
        buckets[S][color] += 1
    return tuple(tuple(sorted(buckets[S].items())) for S in coords)


def intersect_bipartite_neighborhoods_with_right_coset(
    candidate: RightCoset,
    source_left_size: int,
    target_left_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    source_left_colors: Iterable[Hashable] | None = None,
    target_left_colors: Iterable[Hashable] | None = None,
    max_subset_states: int = 200000,
    max_image_group_order: int = 256,
    parent_left_action_verified: bool = False,
) -> BipartiteNeighborhoodCosetIntersection:
    """Exact colored-bipartite incidence intersection inside one right-side coset.

    This solves the precise model in which the left action is the full product of
    symmetric groups on equal-color left vertices. In that model a right
    permutation is a bipartite isomorphism iff, for every left color, it maps the
    multiset of source neighborhoods to the corresponding target multiset.

    For a candidate right coset ``H*r``, source neighborhoods are first moved by
    ``r``. The union of their H-orbits and the target-neighborhood H-orbits is a
    finite H-invariant subset domain. Neighborhood multiplicity-by-left-color is
    an exact string on that domain. Existing candidate-coset SI solves the image
    string inside the induced H action; the generic paired Schreier preimage then
    lifts the exact image coset back to H, and the fixed representative r is
    restored. No ambient-right group element is enumerated by this wrapper.

    ``parent_left_action_verified`` is deliberately metadata, not a theorem gate:
    callers may use this exact result as the full parent bipartite intersection
    only after separately proving that the parent really permits the full
    color-symmetric left action. Otherwise this routine is an exact local model
    but must not be promoted to the full parent SI result.
    """
    n1s = int(source_left_size)
    n1t = int(target_left_size)
    n2 = candidate.subgroup.degree
    r = validate_perm(candidate.representative)
    if len(r) != n2:
        raise ValueError("candidate representative/right subgroup degree mismatch")
    if n1s < 1 or n1t < 1 or n2 < 1:
        raise ValueError("bipartite parts must be nonempty")

    source_colors = _colors(n1s, source_left_colors)
    target_colors = _colors(n1t, target_left_colors)
    source_inventory = _inventory(source_colors)
    target_inventory = _inventory(target_colors)
    if source_inventory != target_inventory:
        return BipartiteNeighborhoodCosetIntersection(
            "exact_empty_left_color_inventory",
            n2,
            n1s,
            0,
            0,
            None,
            source_inventory,
            target_inventory,
            None,
            True,
            True,
            True,
            bool(parent_left_action_verified),
            True,
            "left color multiplicities differ, so no color-preserving bipartite isomorphism exists in this candidate fiber",
        )

    source_neighborhoods = _normalize_edges(n1s, n2, source_edges)
    target_neighborhoods = _normalize_edges(n1t, n2, target_edges)
    shifted_source = tuple(_map_subset(S, r) for S in source_neighborhoods)

    domain_generators = tuple(candidate.subgroup.original_generators)
    if not domain_generators:
        domain_generators = (identity(n2),)
    coords = _orbit_closed_subset_domain(
        tuple(shifted_source) + tuple(target_neighborhoods),
        domain_generators,
        max_subset_states=max_subset_states,
    )
    if coords is None:
        return BipartiteNeighborhoodCosetIntersection(
            "undetermined_subset_orbit_resource_limit",
            n2,
            n1s,
            max_subset_states,
            0,
            None,
            source_inventory,
            target_inventory,
            None,
            False,
            False,
            True,
            bool(parent_left_action_verified),
            False,
            "the exact H-invariant neighborhood-subset domain exceeded the explicit subset-state cap",
        )

    image_generators = _induced_generators(coords, domain_generators)
    image_group = schreier_stabilizer_chain(image_generators or (identity(len(coords)),))
    source_string = _family_string(coords, shifted_source, source_colors)
    target_string = _family_string(coords, target_neighborhoods, target_colors)

    image_identity_candidate = RightCoset(image_group, identity(len(coords)))
    image_si = candidate_coset_string_isomorphism_u2(
        image_identity_candidate,
        source_string,
        target_string,
        root_n=max(n2, len(coords)),
        max_group_order=max_image_group_order,
    )
    if not image_si.exact:
        return BipartiteNeighborhoodCosetIntersection(
            "undetermined_image_string_intersection_" + image_si.status,
            n2,
            n1s,
            len(coords),
            image_group.order,
            image_si.status,
            source_inventory,
            target_inventory,
            None,
            False,
            False,
            True,
            bool(parent_left_action_verified),
            False,
            "the induced neighborhood-family string reached an unresolved candidate-coset SI branch",
        )
    if image_si.coset is None:
        return BipartiteNeighborhoodCosetIntersection(
            "exact_empty_bipartite_neighborhood_coset",
            n2,
            n1s,
            len(coords),
            image_group.order,
            image_si.status,
            source_inventory,
            target_inventory,
            None,
            True,
            True,
            True,
            bool(parent_left_action_verified),
            False,
            "the exact induced neighborhood-family string intersection is empty",
        )

    lifted = paired_action_coset_preimage(
        candidate.subgroup,
        image_generators,
        image_si.coset,
    )
    if lifted.status != "exact_paired_action_coset_preimage" or lifted.coset is None:
        return BipartiteNeighborhoodCosetIntersection(
            "undetermined_neighborhood_image_preimage_" + lifted.status,
            n2,
            n1s,
            len(coords),
            image_group.order,
            image_si.status,
            source_inventory,
            target_inventory,
            None,
            False,
            False,
            True,
            bool(parent_left_action_verified),
            False,
            "the exact induced string result could not be certified back through the paired right-ground subset action",
        )

    result = RightCoset(
        lifted.coset.subgroup,
        compose(r, lifted.coset.representative),
    )
    return BipartiteNeighborhoodCosetIntersection(
        "exact_bipartite_neighborhood_coset_intersection",
        n2,
        n1s,
        len(coords),
        image_group.order,
        image_si.status,
        source_inventory,
        target_inventory,
        result,
        True,
        False,
        True,
        bool(parent_left_action_verified),
        False,
        "exact color-stratified left-neighborhood multiset SI was solved in the induced H subset action, lifted to the right-ground candidate coset, and translated back through its fixed representative; global recurrence cost and actual parent-left-action provenance remain separate obligations",
    )
