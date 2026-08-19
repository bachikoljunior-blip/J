from canonical_partition_guided_string_iso_v1 import canonical_partition_guided_string_iso
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import compose, inverse, schreier_stabilizer_chain


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
    )


def colored_block_values(blocks, special):
    values = [0] * sum(len(b) for b in blocks)
    for u in blocks[special]:
        values[u] = 1
    return tuple(values)


def conjugate_by_relabeling(g, q):
    return compose(compose(inverse(q), g), q)


def relabel_values(values, q):
    out = [None] * len(values)
    for i, v in enumerate(values):
        out[q[i]] = v
    return tuple(out)


def relabel_blocks(blocks, q):
    return tuple(tuple(sorted(q[u] for u in block)) for block in blocks)


def same_coset(a, b):
    assert a.subgroup.order == b.subgroup.order
    assert all(b.subgroup.contains(g) for g in a.subgroup.original_generators)
    assert all(a.subgroup.contains(g) for g in b.subgroup.original_generators)
    assert a.contains(b.representative)
    assert b.contains(a.representative)


def test_returned_coset_generators_and_representative_are_semantically_valid():
    G, blocks = wreath_block_action(6, 2)
    x = colored_block_values(blocks, 0)
    y = colored_block_values(blocks, 1)
    r = canonical_partition_guided_string_iso(G, blocks, x, y, test_size=3)
    assert r.status == "exact_partition_guided_isomorphism_coset"
    C = r.isomorphism_coset

    # The representative is genuinely in G and maps every source value to the
    # corresponding target value.  The subgroup is genuinely contained in G and
    # fixes the target string, so no coset element is invented by bookkeeping.
    assert G.contains(C.representative)
    assert all(x[i] == y[C.representative[i]] for i in range(G.degree))
    for h in C.subgroup.original_generators:
        assert G.contains(h)
        assert all(y[i] == y[h[i]] for i in range(G.degree))


def test_full_coset_is_equivariant_under_arbitrary_physical_relabeling():
    G, blocks = wreath_block_action(6, 2)
    x = colored_block_values(blocks, 0)
    y = colored_block_values(blocks, 1)
    base = canonical_partition_guided_string_iso(G, blocks, x, y, test_size=3)
    assert base.status == "exact_partition_guided_isomorphism_coset"

    # A fixed nontrivial physical relabeling that cuts across quotient blocks.
    q = (7, 0, 10, 3, 1, 8, 5, 11, 2, 9, 4, 6)
    Gq = schreier_stabilizer_chain(
        [conjugate_by_relabeling(g, q) for g in G.original_generators]
    )
    blocksq = relabel_blocks(blocks, q)
    xq = relabel_values(x, q)
    yq = relabel_values(y, q)
    again = canonical_partition_guided_string_iso(Gq, blocksq, xq, yq, test_size=3)
    assert again.status == base.status
    assert again.child_measure == base.child_measure

    conjugated_group = schreier_stabilizer_chain(
        [conjugate_by_relabeling(g, q) for g in base.isomorphism_coset.subgroup.original_generators]
        or [tuple(range(G.degree))]
    )
    conjugated_coset = RightCoset(
        conjugated_group,
        conjugate_by_relabeling(base.isomorphism_coset.representative, q),
    )
    same_coset(conjugated_coset, again.isomorphism_coset)
