from permutation_group_schreier import schreier_stabilizer_chain
from aggregate_local_certificate_relation import aggregate_fullness_relation


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
    within = e.copy(); within[0], within[1] = within[1], within[0]
    return schreier_stabilizer_chain([tuple(swap_blocks), tuple(cycle_blocks), tuple(within)]), blocks


def test_constant_relation_remains_unsplit_and_broken_block_splits_canonically():
    for k in (8, 10):
        G, blocks = wreath_block_action(k, 2)
        constant = [0] * G.degree
        uniform = aggregate_fullness_relation(G, blocks, constant, test_size=3, max_class_fraction=0.9)
        assert uniform.status == "canonical_relation_no_significant_split"
        assert uniform.full_count == uniform.test_count
        assert uniform.color_classes == (tuple(range(k)),)

        broken = [0] * G.degree
        for u in blocks[0]: broken[u] = 1
        split = aggregate_fullness_relation(G, blocks, broken, test_size=3, max_class_fraction=0.9)
        assert len(split.color_classes) == 2
        assert (0,) in split.color_classes
        if k == 10:
            assert split.status == "certified_significant_split"
            assert split.largest_class == 9

        # Renumber the quotient block family. The singleton structural class must
        # follow the distinguished physical block rather than its old numeric label.
        permutation = list(range(1, k)) + [0]
        reordered = [blocks[i] for i in permutation]
        again = aggregate_fullness_relation(G, reordered, broken, test_size=3, max_class_fraction=0.9)
        assert sorted(map(len, again.color_classes)) == sorted(map(len, split.color_classes))
        special_new = permutation.index(0)
        assert (special_new,) in again.color_classes
