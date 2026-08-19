from coset_stabilizer_primitives import RightCoset
from local_fullness_certificates import exact_string_stabilizer
from orbit_factored_partial_string_coset_intersection_v1 import (
    orbit_factored_partial_string_coset_intersection,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def two_independent_s4_orbits():
    n = 8
    e = list(range(n))
    gens = []
    for offset in (0, 4):
        swap = e.copy()
        swap[offset], swap[offset + 1] = swap[offset + 1], swap[offset]
        cycle = e.copy()
        for i in range(4):
            cycle[offset + i] = offset + ((i + 1) % 4)
        gens.extend((tuple(swap), tuple(cycle)))
    return schreier_stabilizer_chain(gens)


def test_partial_intersection_matches_exact_masked_segment_stabilizer():
    G = two_independent_s4_orbits()
    values = (0, 0, 1, 1, 9, 8, 7, 6)
    active = (0, 1, 2, 3)
    got = orbit_factored_partial_string_coset_intersection(
        RightCoset(G, identity(G.degree)), values, active
    )
    assert got.status == "exact_orbit_factored_partial_string_intersection"
    assert got.coset is not None
    assert got.active_orbit_children == ((0, 1, 2, 3),)
    assert got.skipped_orbits == ((4, 5, 6, 7),)

    masked = tuple(("active", values[i]) if i in active else ("inactive", None)
                   for i in range(G.degree))
    exact = exact_string_stabilizer(G, masked)
    assert exact.status == "exact_intersection_coset"
    assert exact.coset is not None
    assert got.coset.subgroup.order == exact.coset.subgroup.order
    assert all(exact.coset.subgroup.contains(g) for g in got.coset.subgroup.original_generators)
    assert all(got.coset.subgroup.contains(g) for g in exact.coset.subgroup.original_generators)
    # S2 x S2 on the active orbit, unrestricted S4 on the inactive orbit.
    assert got.coset.subgroup.order == 4 * 24


def test_partial_intersection_fails_closed_when_active_set_cuts_an_orbit():
    G = two_independent_s4_orbits()
    got = orbit_factored_partial_string_coset_intersection(
        RightCoset(G, identity(G.degree)), [0] * G.degree, (0, 1)
    )
    assert got.status == "active_domain_not_subgroup_invariant"
    assert got.coset is None
