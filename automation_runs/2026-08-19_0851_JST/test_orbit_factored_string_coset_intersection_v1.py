from block_action_preimage_coset_v1 import block_action_preimage_coset
from coset_stabilizer_primitives import RightCoset
from local_fullness_certificates import _alternating_test_generators, _young_group
from orbit_factored_string_coset_intersection_v1 import (
    orbit_factored_string_coset_intersection,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain
from recursive_point_image_coset_intersection import right_coset_intersection_recursive


def wreath_block_action(k, s):
    n = k * s
    e = list(range(n))
    blocks = [tuple(range(i * s, (i + 1) * s)) for i in range(k)]
    swap_blocks = e.copy()
    for c in range(s):
        swap_blocks[c], swap_blocks[s + c] = swap_blocks[s + c], swap_blocks[c]
    cycle_blocks = e.copy()
    for i in range(k):
        for c in range(s):
            cycle_blocks[i * s + c] = ((i + 1) % k) * s + c
    within = e.copy()
    within[0], within[1] = within[1], within[0]
    return schreier_stabilizer_chain(
        [tuple(swap_blocks), tuple(cycle_blocks), tuple(within)]
    ), blocks


def same_coset(a, b):
    assert a.subgroup.order == b.subgroup.order
    assert all(b.subgroup.contains(g) for g in a.subgroup.original_generators)
    assert all(a.subgroup.contains(g) for g in b.subgroup.original_generators)
    assert a.contains(b.representative)
    assert b.contains(a.representative)


def candidate_for_block_3cycle(G, blocks):
    q = _alternating_test_generators(len(blocks), (0, 1, 2))[0]
    lift = block_action_preimage_coset(G, blocks, q)
    assert lift.status == "exact_block_action_preimage_coset"
    return lift.coset


def full_domain_oracle(candidate, values):
    young = RightCoset(_young_group(tuple(values)), identity(len(values)))
    return right_coset_intersection_recursive(candidate, young, max_nodes=500000)


def test_uniform_string_matches_full_domain_exact_oracle_and_exposes_small_children():
    G, blocks = wreath_block_action(6, 2)
    candidate = candidate_for_block_3cycle(G, blocks)
    values = [0] * G.degree

    new = orbit_factored_string_coset_intersection(candidate, values)
    old = full_domain_oracle(candidate, values)

    assert new.status == "exact_orbit_factored_string_intersection"
    assert old.status == "exact_intersection_coset"
    same_coset(new.coset, old.coset)
    assert new.largest_child_domain == 2
    assert sorted(len(O) for O in new.orbit_children) == [2] * 6
    assert len(new.child_search_nodes) == 6


def test_moved_distinguished_block_matches_global_empty_intersection():
    G, blocks = wreath_block_action(6, 2)
    candidate = candidate_for_block_3cycle(G, blocks)
    values = [0] * G.degree
    for u in blocks[0]:
        values[u] = 1

    new = orbit_factored_string_coset_intersection(candidate, values)
    old = full_domain_oracle(candidate, values)

    assert old.status == "empty_intersection"
    assert new.status in {
        "empty_intersection_local_value_multiplicity",
        "empty_intersection",
    }
    assert new.coset is None
    assert new.largest_child_domain == 2


def test_child_search_limit_fails_closed_without_falling_back_to_global_search():
    G, blocks = wreath_block_action(6, 2)
    candidate = candidate_for_block_3cycle(G, blocks)
    values = [0] * G.degree

    new = orbit_factored_string_coset_intersection(
        candidate, values, max_child_nodes=0
    )
    assert new.status == "undetermined_child_intersection_limit"
    assert new.coset is None
    assert new.child_search_nodes and new.child_search_nodes[0] == 1
