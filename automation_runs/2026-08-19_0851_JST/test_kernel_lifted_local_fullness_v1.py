from giant_block_action_certificates import _block_action
from kernel_lifted_local_fullness_v1 import kernel_lifted_local_fullness
from local_fullness_certificates import (
    _alternating_test_generators,
    local_fullness_certificate,
)
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


def test_kernel_lift_fullness_matches_old_exact_global_certificate():
    G, blocks = wreath_block_action(6, 2)
    values = [0] * G.degree
    T = (0, 1, 2, 3)

    new = kernel_lifted_local_fullness(G, blocks, values, T)
    old = local_fullness_certificate(G, blocks, values, T)
    assert new.status == "certified_full_kernel_lift"
    assert new.full is True
    assert old.full is True
    assert new.affected_orbit_bound_verified

    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    for witness, q in zip(new.lift_witnesses, _alternating_test_generators(6, T)):
        assert G.contains(witness)
        assert all(values[i] == values[witness[i]] for i in range(G.degree))
        assert _block_action(witness, blocks, point_to_block) == q


def test_kernel_lift_nonfullness_matches_old_exact_global_certificate():
    G, blocks = wreath_block_action(6, 2)
    values = [0] * G.degree
    for u in blocks[0]:
        values[u] = 1
    T = (0, 1, 2)

    new = kernel_lifted_local_fullness(G, blocks, values, T)
    old = local_fullness_certificate(G, blocks, values, T)
    assert new.status == "certified_nonfull_kernel_lift"
    assert new.full is False
    assert old.full is False
    assert new.missing_generator is not None
    assert new.largest_affected_kernel_orbit <= G.degree / len(blocks) + 1e-12


def test_kernel_intersection_budget_fails_closed():
    G, blocks = wreath_block_action(6, 2)
    values = [0] * G.degree
    r = kernel_lifted_local_fullness(
        G, blocks, values, (0, 1, 2), max_intersection_nodes=1
    )
    assert r.status == "undetermined_kernel_intersection_limit"
    assert r.full is None


def test_nonlogarithmic_test_set_is_rejected_before_expensive_work():
    G, blocks = wreath_block_action(6, 2)
    values = [0] * G.degree
    r = kernel_lifted_local_fullness(
        G, blocks, values, (0, 1, 2, 3), max_test_size_factor=0.25
    )
    assert r.status == "test_set_not_logarithmic"
    assert r.logarithmic_test_bound == 3
