from giant_block_action_certificates import _block_action
from permutation_group_schreier import schreier_stabilizer_chain
from canonical_local_partition_iso_coset_v1 import canonical_local_partition_iso_coset


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


def test_isomorphic_broken_blocks_yield_candidate_coset_containing_known_map():
    G, blocks, shift = wreath_block_action(10, 2)
    x = colored_block_values(blocks, 0)
    y = colored_block_values(blocks, 1)
    r = canonical_local_partition_iso_coset(G, blocks, x, y, test_size=3)
    assert r.status == "canonical_partition_candidate_coset"
    assert r.candidate_coset is not None
    assert r.candidate_coset.contains(shift)

    # The subgroup carried by RightCoset is the target partition stabilizer.
    target_cells = r.target_relation.color_classes
    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    for g in r.candidate_coset.subgroup.original_generators:
        q = _block_action(g, blocks, point_to_block)
        for cell in target_cells:
            assert tuple(sorted(q[i] for i in cell)) == cell


def test_partition_invariant_mismatch_rejects_broken_vs_uniform():
    G, blocks, _ = wreath_block_action(10, 2)
    x = colored_block_values(blocks, 0)
    y = [0] * G.degree
    r = canonical_local_partition_iso_coset(G, blocks, x, y, test_size=3)
    assert r.status == "canonical_partition_invariant_mismatch"
    assert r.candidate_coset is None


def test_uniform_pair_is_valid_but_provides_no_recurrence_progress():
    G, blocks, _ = wreath_block_action(10, 2)
    values = [0] * G.degree
    r = canonical_local_partition_iso_coset(G, blocks, values, values, test_size=3)
    assert r.status == "canonical_partition_no_progress"
    assert r.candidate_coset is None


def test_partition_transport_budget_fails_closed():
    G, blocks, _ = wreath_block_action(10, 2)
    x = colored_block_values(blocks, 0)
    y = colored_block_values(blocks, 1)
    r = canonical_local_partition_iso_coset(
        G, blocks, x, y, test_size=3, max_partition_states=1
    )
    assert r.status == "undetermined_partition_orbit_limit"
    assert r.candidate_coset is None
