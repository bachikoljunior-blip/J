from kernel_lifted_local_fullness_v3 import kernel_lifted_local_fullness_v3
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


def test_small_exact_fixture_cannot_be_promoted_to_theorem_scale_evidence():
    G, blocks = wreath_block_action(6, 2)
    r = kernel_lifted_local_fullness_v3(
        G, blocks, [0] * G.degree, (0, 1, 2, 3)
    )
    assert r.exact_result.full is True
    assert r.exact_result.recurrence_child_bound_verified
    assert not r.parameter_gate.certified
    assert not r.theorem_scale_recurrence_evidence
