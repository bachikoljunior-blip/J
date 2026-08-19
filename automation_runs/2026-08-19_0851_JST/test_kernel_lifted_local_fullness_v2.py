from giant_block_action_certificates import _block_action
from kernel_lifted_local_fullness_v1 import kernel_lifted_local_fullness
from kernel_lifted_local_fullness_v2 import kernel_lifted_local_fullness_v2
from local_fullness_certificates import _alternating_test_generators
from permutation_group_schreier import schreier_stabilizer_chain


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


def test_fullness_matches_rev153_but_executes_on_small_kernel_orbit_children():
    G, blocks = wreath_block_action(6, 2)
    values = [0] * G.degree
    T = (0, 1, 2, 3)

    old = kernel_lifted_local_fullness(G, blocks, values, T)
    new = kernel_lifted_local_fullness_v2(G, blocks, values, T)

    assert old.full is True
    assert new.status == "certified_full_orbit_factored"
    assert new.full is True
    assert new.largest_recursive_child_domain == 2
    assert new.certified_affected_child_bound == 2
    assert new.all_recursive_children_affected
    assert new.recurrence_child_bound_verified

    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    for witness, q in zip(new.lift_witnesses, _alternating_test_generators(6, T)):
        assert G.contains(witness)
        assert all(values[i] == values[witness[i]] for i in range(G.degree))
        assert _block_action(witness, blocks, point_to_block) == q


def test_nonfullness_matches_rev153_and_preserves_exact_missing_generator():
    G, blocks = wreath_block_action(6, 2)
    values = [0] * G.degree
    for u in blocks[0]:
        values[u] = 1
    T = (0, 1, 2)

    old = kernel_lifted_local_fullness(G, blocks, values, T)
    new = kernel_lifted_local_fullness_v2(G, blocks, values, T)

    assert old.full is False
    assert new.status == "certified_nonfull_orbit_factored"
    assert new.full is False
    assert new.missing_generator == old.missing_generator
    assert new.largest_recursive_child_domain == 2
    assert new.recurrence_child_bound_verified


def test_child_budget_fails_closed_without_global_intersection_fallback():
    G, blocks = wreath_block_action(6, 2)
    new = kernel_lifted_local_fullness_v2(
        G, blocks, [0] * G.degree, (0, 1, 2), max_child_nodes=0
    )
    assert new.status == "undetermined_orbit_child_limit"
    assert new.full is None
    assert not new.recurrence_child_bound_verified


def test_nonlogarithmic_test_set_still_fails_before_child_execution():
    G, blocks = wreath_block_action(6, 2)
    new = kernel_lifted_local_fullness_v2(
        G, blocks, [0] * G.degree, (0, 1, 2, 3), max_test_size_factor=0.25
    )
    assert new.status == "test_set_not_logarithmic"
    assert new.full is None
    assert not new.child_intersection_nodes
