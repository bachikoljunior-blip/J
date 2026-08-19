from coset_stabilizer_primitives import RightCoset
from orbit_factored_partial_string_coset_intersection_v2 import (
    orbit_factored_partial_string_coset_intersection_v2,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def test_two_small_active_orbits_return_exact_proof_children():
    # Two independent 2-cycles give two invariant active orbit children.
    g1 = (1, 0, 2, 3)
    g2 = (0, 1, 3, 2)
    G = schreier_stabilizer_chain([g1, g2])
    got = orbit_factored_partial_string_coset_intersection_v2(
        RightCoset(G, identity(4)),
        (0, 0, 1, 1),
        (0, 1, 2, 3),
        root_n=64,
        max_explicit_degree=8,
    )
    assert got.status == "exact_orbit_factored_partial_string_intersection"
    assert got.exact and got.coset is not None
    assert len(got.child_proofs) == 2
    assert all(p.exact and p.terminal_certified for p in got.child_proofs)
    assert got.coset.subgroup.order == 4


def test_large_transitive_active_child_is_exposed_and_fails_closed():
    n = 20
    cycle = tuple((i + 1) % n for i in range(n))
    G = schreier_stabilizer_chain([cycle])
    got = orbit_factored_partial_string_coset_intersection_v2(
        RightCoset(G, identity(n)),
        (0,) * n,
        tuple(range(n)),
        root_n=n,
        max_explicit_degree=20,
    )
    assert got.status == "undetermined_nonpolylog_child_requires_r1"
    assert not got.exact and got.coset is None
    assert len(got.child_proofs) == 1
    child = got.child_proofs[0]
    assert child.domain_size == n
    assert child.permutation_candidates_checked == 0
    assert not child.exact and not child.local_cost_certified
