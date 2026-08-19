from coset_stabilizer_primitives import RightCoset
from orbit_factored_partial_string_coset_intersection_v2 import (
    orbit_factored_partial_string_coset_intersection_v2,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def two_independent_s4_orbits():
    n = 8
    e = list(range(n))
    gens = []
    for offset in (0, 4):
        swap = e.copy(); swap[offset], swap[offset + 1] = offset + 1, offset
        cycle = e.copy()
        for i in range(4):
            cycle[offset + i] = offset + ((i + 1) % 4)
        gens.extend((tuple(swap), tuple(cycle)))
    return schreier_stabilizer_chain(gens)


def symmetric_group(n):
    e = list(range(n))
    swap = e.copy(); swap[0], swap[1] = 1, 0
    cycle = tuple((i + 1) % n for i in range(n))
    return schreier_stabilizer_chain([tuple(swap), cycle])


def test_small_active_orbit_executes_only_proof_carrying_terminal():
    G = two_independent_s4_orbits()
    values = (0, 0, 1, 1, 9, 8, 7, 6)
    got = orbit_factored_partial_string_coset_intersection_v2(
        RightCoset(G, identity(8)), values, (0, 1, 2, 3),
        primary_domain_size=64, polylog_power=1,
    )
    assert got.status == "exact_proof_carrying_partial_string_intersection"
    assert got.coset is not None
    assert got.all_children_proof_carrying
    assert len(got.child_proofs) == 1
    assert got.child_proofs[0].status == "exact_coset_small_terminal"
    assert got.child_proofs[0].accounting_node is not None
    # active S4 string stabilizer S2xS2, inactive S4 remains free
    assert got.coset.subgroup.order == 4 * 24


def test_large_primitive_active_orbit_refuses_opaque_exact_fallback():
    G = symmetric_group(7)
    got = orbit_factored_partial_string_coset_intersection_v2(
        RightCoset(G, identity(7)), [0] * 7, tuple(range(7)),
        primary_domain_size=7, polylog_power=1,
    )
    assert got.status == "requires_recursive_child_dispatch"
    assert got.coset is None
    assert not got.all_children_proof_carrying
    assert len(got.child_proofs) == 1
    assert got.child_proofs[0].status == "requires_primitive_recursive_dispatch"
    assert not got.child_proofs[0].exact
    assert got.child_proofs[0].accounting_node is None
