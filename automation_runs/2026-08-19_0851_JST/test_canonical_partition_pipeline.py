from permutation_group_schreier import schreier_stabilizer_chain
from canonical_partition_pipeline import canonical_partition_pipeline


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


def test_pipeline_returns_giant_for_uniform_full_case():
    G, blocks = make_block_group(8, 2)
    r = canonical_partition_pipeline(G, blocks, [0] * G.degree)
    assert r.status == "certified_global_alternating_obstruction"
    assert r.giant_type == "S_m"
    assert r.decisive_relation_level == "global_alternating_image"


def test_pipeline_returns_canonical_split_for_distinguished_block():
    G, blocks = make_block_group(10, 2)
    values = [0] * G.degree
    for u in blocks[0]:
        values[u] = 1
    r = canonical_partition_pipeline(G, blocks, values)
    assert r.status == "certified_significant_split"
    assert (0,) in r.split_classes
    assert r.decisive_relation_level == "local_certificate_incidence"


def test_pipeline_keeps_regular_nongiant_case_unresolved_without_overclaim():
    n = 7
    rotate = tuple((i + 1) % n for i in range(n))
    G = schreier_stabilizer_chain([rotate])
    blocks = [(i,) for i in range(n)]
    r = canonical_partition_pipeline(G, blocks, [0] * n)
    assert r.status == "homogeneous_pair_obstruction"
    assert r.giant_type is None
    assert r.johnson_ground_size is None
