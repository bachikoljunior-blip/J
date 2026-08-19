from permutation_group_schreier import compose, inverse, schreier_stabilizer_chain
from canonical_partition_transporter_v1 import canonical_partition_transporter


def symmetric_group_4():
    swap = (1, 0, 2, 3)
    cycle = (1, 2, 3, 0)
    return schreier_stabilizer_chain([swap, cycle])


def test_exact_source_partition_stabilizer_and_transporter():
    G = symmetric_group_4()
    blocks = [(0,), (1,), (2,), (3,)]
    source = ((0, 1), (2, 3))
    target = ((0, 2), (1, 3))

    r = canonical_partition_transporter(G, blocks, source, target)
    assert r.status == "partition_transporter_coset"
    assert r.transporter is not None
    assert r.source_stabilizer is not None
    assert r.source_stabilizer.order == 4
    assert r.orbit_states == 6

    p = r.transporter
    assert tuple(sorted(p[x] for x in source[0])) == target[0]
    assert tuple(sorted(p[x] for x in source[1])) == target[1]


def test_stabilizer_only_mode_preserves_each_colored_cell():
    G = symmetric_group_4()
    blocks = [(0,), (1,), (2,), (3,)]
    source = ((0, 1), (2, 3))
    r = canonical_partition_transporter(G, blocks, source)
    assert r.status == "partition_transporter_coset"
    assert r.source_stabilizer.order == 4
    for g in r.source_stabilizer.original_generators:
        assert tuple(sorted(g[x] for x in source[0])) == source[0]
        assert tuple(sorted(g[x] for x in source[1])) == source[1]


def test_reordered_physical_blocks_preserve_transport_structure():
    G = symmetric_group_4()
    blocks = [(0,), (1,), (2,), (3,)]
    source = ((0, 1), (2, 3))
    target = ((0, 2), (1, 3))
    base = canonical_partition_transporter(G, blocks, source, target)

    # Change only the quotient block numbering. Translate the colored cells into
    # the new quotient coordinates and require the same orbit/stabilizer data.
    order = [2, 0, 3, 1]
    reordered = [blocks[i] for i in order]
    old_to_new = {old: new for new, old in enumerate(order)}
    source2 = tuple(tuple(sorted(old_to_new[x] for x in cell)) for cell in source)
    target2 = tuple(tuple(sorted(old_to_new[x] for x in cell)) for cell in target)
    again = canonical_partition_transporter(G, reordered, source2, target2)

    assert again.status == base.status
    assert again.orbit_states == base.orbit_states
    assert again.source_stabilizer.order == base.source_stabilizer.order


def test_partition_orbit_budget_fails_closed():
    G = symmetric_group_4()
    r = canonical_partition_transporter(
        G, [(0,), (1,), (2,), (3,)], ((0, 1), (2, 3)), max_states=1
    )
    assert r.status == "undetermined_partition_orbit_limit"
    assert r.transporter is None
    assert r.source_stabilizer is None


def test_ordered_color_shape_mismatch_is_not_bridged():
    G = symmetric_group_4()
    r = canonical_partition_transporter(
        G,
        [(0,), (1,), (2,), (3,)],
        ((0, 1), (2, 3)),
        ((0,), (1, 2, 3)),
    )
    assert r.status == "partition_shape_mismatch"
    assert r.transporter is None
