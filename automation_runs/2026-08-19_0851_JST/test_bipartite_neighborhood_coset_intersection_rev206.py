from __future__ import annotations

from collections import Counter
from itertools import permutations

from bipartite_neighborhood_coset_intersection_v1 import (
    intersect_bipartite_neighborhoods_with_right_coset,
)
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _chain(gens):
    return schreier_stabilizer_chain(gens)


def _trivial(n):
    return _chain([identity(n)])


def _cyclic(n):
    return _chain([tuple((i + 1) % n for i in range(n))])


def _symmetric4():
    cycle = (1, 2, 3, 0)
    swap01 = (1, 0, 2, 3)
    return _chain([cycle, swap01])


def _edges(neighborhoods):
    return {(a, b) for a, S in enumerate(neighborhoods) for b in S}


def _mapped_inventory(neighborhoods, colors, p):
    return Counter((colors[a], tuple(sorted(p[b] for b in S))) for a, S in enumerate(neighborhoods))


def test_fixed_representative_is_restored_after_trivial_subgroup_intersection():
    r = (1, 2, 3, 0)
    source = [(0,), (1, 2), (0, 2, 3)]
    target = [tuple(sorted(r[b] for b in S)) for S in source]
    candidate = RightCoset(_trivial(4), r)
    got = intersect_bipartite_neighborhoods_with_right_coset(
        candidate,
        3,
        3,
        _edges(source),
        _edges(target),
        parent_left_action_verified=True,
    )
    assert got.status == "exact_bipartite_neighborhood_coset_intersection"
    assert got.coset is not None and got.coset.contains(r)
    assert got.coset.subgroup.order == 1
    assert got.parent_left_action_verified
    assert got.exact and not got.exact_empty


def test_trivial_candidate_is_exact_empty_when_neighborhood_family_differs():
    source = [(0,), (1, 2)]
    target = [(0,), (1, 3)]
    got = intersect_bipartite_neighborhoods_with_right_coset(
        RightCoset(_trivial(4), identity(4)),
        2,
        2,
        _edges(source),
        _edges(target),
    )
    assert got.status == "exact_empty_bipartite_neighborhood_coset"
    assert got.coset is None
    assert got.exact and got.exact_empty


def test_left_color_inventory_mismatch_is_exact_empty_before_subset_action():
    source = [(0,), (1,)]
    target = [(0,), (1,)]
    got = intersect_bipartite_neighborhoods_with_right_coset(
        RightCoset(_cyclic(3), identity(3)),
        2,
        2,
        _edges(source),
        _edges(target),
        source_left_colors=("a", "b"),
        target_left_colors=("a", "a"),
    )
    assert got.status == "exact_empty_left_color_inventory"
    assert got.exact_empty and got.exact
    assert got.subset_state_count == 0


def test_duplicate_neighborhood_multiplicities_and_left_colors_are_preserved_exactly():
    source = [(0, 1), (0, 1), (2, 3), (2, 3)]
    target = [(1, 2), (1, 2), (0, 3), (0, 3)]
    colors = ("red", "blue", "red", "blue")
    candidate = RightCoset(_symmetric4(), identity(4))
    got = intersect_bipartite_neighborhoods_with_right_coset(
        candidate,
        4,
        4,
        _edges(source),
        _edges(target),
        source_left_colors=colors,
        target_left_colors=colors,
        max_image_group_order=256,
    )
    assert got.status == "exact_bipartite_neighborhood_coset_intersection"
    assert got.coset is not None
    assert got.exact

    all_perms = tuple(permutations(range(4)))
    expected = {
        p
        for p in all_perms
        if _mapped_inventory(source, colors, p) == _mapped_inventory(target, colors, identity(4))
    }
    actual = {p for p in all_perms if got.coset.contains(p)}
    assert actual == expected
    assert actual


def test_exhaustive_s4_coset_matches_direct_colored_bipartite_condition():
    source = [(0,), (0, 1), (2, 3)]
    target = [(2,), (2, 3), (0, 1)]
    source_colors = (0, 1, 1)
    target_colors = (0, 1, 1)
    candidate = RightCoset(_symmetric4(), identity(4))
    got = intersect_bipartite_neighborhoods_with_right_coset(
        candidate,
        3,
        3,
        _edges(source),
        _edges(target),
        source_left_colors=source_colors,
        target_left_colors=target_colors,
    )
    assert got.exact
    all_perms = tuple(permutations(range(4)))
    expected = {
        p
        for p in all_perms
        if _mapped_inventory(source, source_colors, p)
        == _mapped_inventory(target, target_colors, identity(4))
    }
    actual = set() if got.coset is None else {p for p in all_perms if got.coset.contains(p)}
    assert actual == expected


def test_subset_orbit_resource_limit_fails_closed_not_empty():
    source = [(0, 1), (0, 2)]
    target = list(source)
    got = intersect_bipartite_neighborhoods_with_right_coset(
        RightCoset(_symmetric4(), identity(4)),
        2,
        2,
        _edges(source),
        _edges(target),
        max_subset_states=3,
    )
    assert got.status == "undetermined_subset_orbit_resource_limit"
    assert not got.exact
    assert not got.exact_empty
    assert got.coset is None


def test_cyclic_cycle_family_returns_full_cyclic_stabilizer():
    neighborhoods = [(i, (i + 1) % 5) for i in range(5)]
    candidate = RightCoset(_cyclic(5), identity(5))
    got = intersect_bipartite_neighborhoods_with_right_coset(
        candidate,
        5,
        5,
        _edges(neighborhoods),
        _edges(neighborhoods),
    )
    assert got.status == "exact_bipartite_neighborhood_coset_intersection"
    assert got.coset is not None
    assert got.coset.subgroup.order == 5
    assert got.exact
