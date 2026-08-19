from permutation_group_schreier import identity, schreier_stabilizer_chain
from local_fullness_certificates import _alternating_test_generators
from giant_parity_reduction import reduce_global_giant_to_parity_classes


def make_symmetric_block_group(k, s):
    n = k * s
    e = list(range(n))
    blocks = [tuple(range(i * s, (i + 1) * s)) for i in range(k)]
    swap = e.copy()
    for c in range(s):
        swap[c], swap[s + c] = swap[s + c], swap[c]
    rotate = e.copy()
    for i in range(k):
        for c in range(s):
            rotate[i * s + c] = ((i + 1) % k) * s + c
    within = e.copy()
    within[0], within[1] = within[1], within[0]
    return schreier_stabilizer_chain([tuple(swap), tuple(rotate), tuple(within)]), blocks


def test_symmetric_image_collapses_to_one_quotient_orbit():
    G, blocks = make_symmetric_block_group(8, 2)
    r = reduce_global_giant_to_parity_classes(G, blocks, [0] * G.degree)
    assert r.status == "symmetric_single_quotient_orbit"
    assert r.giant_type == "S_m"
    assert r.parity_branch_count == 1
    assert len(r.parity_cosets) == 1


def test_alternating_image_has_exactly_two_parity_classes():
    m = 8
    A = schreier_stabilizer_chain(_alternating_test_generators(m, tuple(range(m))))
    blocks = [(i,) for i in range(m)]
    r = reduce_global_giant_to_parity_classes(A, blocks, [0] * m)
    assert r.status == "alternating_two_parity_classes"
    assert r.giant_type == "A_m"
    assert r.parity_branch_count == 2
    even, odd = r.parity_cosets
    assert even.contains(identity(m))
    transposition = list(range(m)); transposition[0], transposition[1] = transposition[1], transposition[0]
    assert odd.contains(tuple(transposition))
    assert not even.contains(tuple(transposition))


def test_small_transitive_nongiant_group_is_not_overclaimed():
    m = 7
    rotate = tuple((i + 1) % m for i in range(m))
    G = schreier_stabilizer_chain([rotate])
    blocks = [(i,) for i in range(m)]
    r = reduce_global_giant_to_parity_classes(G, blocks, [0] * m)
    assert r.status == "not_global_giant"
    assert r.parity_branch_count == 0
