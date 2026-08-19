from permutation_group_schreier import schreier_stabilizer_chain
from canonical_no_split_obstruction import classify_no_split_obstruction


def make_block_group(k, s):
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


def test_uniform_and_split_cases():
    G, blocks = make_block_group(10, 2)
    uniform = classify_no_split_obstruction(G, blocks, [0] * G.degree)
    assert uniform.status == "certified_global_alternating_obstruction"
    assert uniform.giant_type == "S_m"
    assert uniform.compact_alt_generators_verified

    values = [0] * G.degree
    for u in blocks[0]:
        values[u] = 1
    split = classify_no_split_obstruction(G, blocks, values)
    assert split.status == "certified_significant_split"
    assert (0,) in split.split_classes


def test_regular_nonfull_case_remains_unresolved():
    n = 7
    rotate = tuple((i + 1) % n for i in range(n))
    G = schreier_stabilizer_chain([rotate])
    blocks = [(i,) for i in range(n)]
    cert = classify_no_split_obstruction(G, blocks, [0] * n)
    assert cert.status == "canonical_nonfull_no_split"
    assert cert.quotient_image_order == 7
    assert cert.full_test_count == 0
    assert cert.nonfull_test_count == 35
