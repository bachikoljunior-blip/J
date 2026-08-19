from affected_kernel_recurrence_plan_v1 import affected_kernel_recurrence_plan
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


def test_wreath_giant_exposes_exact_small_kernel_orbit_children():
    G, blocks = wreath_block_action(6, 2)
    plan = affected_kernel_recurrence_plan(G, blocks)
    assert plan.status == "certified_affected_kernel_child_partition"
    assert plan.giant_degree == 6
    assert plan.strict_primary_shrink
    assert plan.largest_child_domain == 2
    assert plan.certified_child_bound == 2
    assert sorted(len(o) for o in plan.kernel_orbits) == [2] * 6
    assert sorted(x for orbit in plan.kernel_orbits for x in orbit) == list(range(G.degree))
    assert plan.execution_cost_certified is False


def test_nongiant_action_fails_closed():
    n = 10
    e = tuple(range(n))
    G = schreier_stabilizer_chain([e])
    blocks = [tuple([i]) for i in range(5)]
    plan = affected_kernel_recurrence_plan(G, blocks)
    assert plan.status == "giant_action_required"
    assert not plan.strict_primary_shrink
    assert not plan.execution_cost_certified
