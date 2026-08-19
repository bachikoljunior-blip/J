from giant_block_action_certificates import _block_action
from permutation_group_schreier import compose, schreier_stabilizer_chain
from local_certificate_partition_coset_v1 import local_certificate_partition_coset


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
    return schreier_stabilizer_chain([tuple(swap_blocks), tuple(cycle_blocks), tuple(within)]), blocks


def broken_block_values(blocks, which):
    values = [0] * sum(map(len, blocks))
    for u in blocks[which]:
        values[u] = 1
    return values


def act_cells(cells, q):
    return tuple(tuple(sorted(q[x] for x in cell)) for cell in cells)


def test_two_strings_expose_exact_partition_respecting_coset():
    G, blocks = wreath_block_action(10, 2)
    result = local_certificate_partition_coset(
        G, blocks, broken_block_values(blocks, 0), broken_block_values(blocks, 4)
    )
    assert result.status == "canonical_local_partition_coset"
    assert result.source_relation.significant_split
    assert result.target_relation.significant_split
    assert result.transporter is not None
    assert result.source_stabilizer is not None
    assert result.candidate_count == result.source_stabilizer.order > 0

    point_to_block = {u: i for i, block in enumerate(blocks) for u in block}
    q = _block_action(result.transporter, blocks, point_to_block)
    assert act_cells(result.source_relation.color_classes, q) == result.target_relation.color_classes

    for h in result.source_stabilizer.original_generators:
        qh = _block_action(h, blocks, point_to_block)
        assert act_cells(result.source_relation.color_classes, qh) == result.source_relation.color_classes
        candidate = compose(h, result.transporter)
        qc = _block_action(candidate, blocks, point_to_block)
        assert act_cells(result.source_relation.color_classes, qc) == result.target_relation.color_classes


def test_incompatible_significant_structure_fails_closed():
    G, blocks = wreath_block_action(10, 2)
    result = local_certificate_partition_coset(
        G, blocks, broken_block_values(blocks, 0), [0] * G.degree
    )
    assert result.status == "canonical_local_partition_incompatible"
    assert result.transporter is None
    assert result.candidate_count == 0


def test_local_certificate_resource_limit_fails_closed():
    G, blocks = wreath_block_action(10, 2)
    result = local_certificate_partition_coset(
        G,
        blocks,
        broken_block_values(blocks, 0),
        broken_block_values(blocks, 1),
        max_test_sets=10,
    )
    assert result.status == "undetermined_testset_limit"
    assert result.transporter is None
    assert result.candidate_count == 0


def test_partition_orbit_limit_fails_closed():
    G, blocks = wreath_block_action(10, 2)
    result = local_certificate_partition_coset(
        G,
        blocks,
        broken_block_values(blocks, 0),
        broken_block_values(blocks, 4),
        max_partition_states=1,
    )
    assert result.status == "undetermined_partition_orbit_limit"
    assert result.transporter is None
    assert result.candidate_count == 0
