from canonical_partition_guided_string_iso_v1 import (
    _all_value_preserving_maps,
    canonical_partition_guided_string_iso,
)
from coset_stabilizer_primitives import RightCoset
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
    return (
        schreier_stabilizer_chain([tuple(swap_blocks), tuple(cycle_blocks), tuple(within)]),
        blocks,
        tuple(cycle_blocks),
    )


def colored_block_values(blocks, special):
    values = [0] * sum(len(b) for b in blocks)
    for u in blocks[special]:
        values[u] = 1
    return values


def _same_coset(a, b):
    assert a.subgroup.order == b.subgroup.order
    assert all(b.subgroup.contains(g) for g in a.subgroup.original_generators)
    assert all(a.subgroup.contains(g) for g in b.subgroup.original_generators)
    assert a.contains(b.representative)
    assert b.contains(a.representative)


def test_partition_guided_result_matches_direct_exact_g_intersection():
    G, blocks, shift = wreath_block_action(6, 2)
    x = colored_block_values(blocks, 0)
    y = colored_block_values(blocks, 1)

    guided = canonical_partition_guided_string_iso(G, blocks, x, y, test_size=3)
    assert guided.status == "exact_partition_guided_isomorphism_coset"
    assert guided.progress_verified
    assert guided.child_measure == 5
    assert guided.isomorphism_coset.contains(shift)

    value_coset = _all_value_preserving_maps(x, y)
    baseline = right_coset_intersection_recursive(
        RightCoset(G, identity(G.degree)), value_coset, max_nodes=500000
    )
    assert baseline.status == "exact_intersection_coset"
    _same_coset(guided.isomorphism_coset, baseline.coset)


def test_known_nonisomorphism_is_rejected_without_fabricating_coset():
    G, blocks, _ = wreath_block_action(6, 2)
    x = colored_block_values(blocks, 0)
    y = [0] * G.degree
    y[blocks[0][0]] = 1
    y[blocks[1][0]] = 1
    r = canonical_partition_guided_string_iso(G, blocks, x, y, test_size=3)
    assert r.status.startswith("non_isomorphic")
    assert r.isomorphism_coset is None


def test_uniform_pair_remains_no_progress_not_false_success():
    G, blocks, _ = wreath_block_action(6, 2)
    values = [0] * G.degree
    r = canonical_partition_guided_string_iso(G, blocks, values, values, test_size=3)
    assert r.status == "canonical_partition_no_progress"
    assert not r.progress_verified
    assert r.isomorphism_coset is None


def test_exact_intersection_budget_fails_closed():
    G, blocks, _ = wreath_block_action(6, 2)
    x = colored_block_values(blocks, 0)
    y = colored_block_values(blocks, 1)
    r = canonical_partition_guided_string_iso(
        G, blocks, x, y, test_size=3, max_intersection_nodes=1
    )
    assert r.status == "undetermined_intersection_limit"
    assert not r.progress_verified
    assert r.isomorphism_coset is None
