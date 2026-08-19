from itertools import combinations

from permutation_group_schreier import schreier_stabilizer_chain
from local_fullness_certificates import _alternating_test_generators
from master_canonical_reduction import master_canonical_reduction, reduce_canonical_pair_structure


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
    within = e.copy(); within[0], within[1] = within[1], within[0]
    return schreier_stabilizer_chain([tuple(swap), tuple(rotate), tuple(within)]), blocks


def johnson_pair_weights(v, k):
    vertices = list(combinations(range(v), k))
    return tuple(
        ((i, j), int(len(set(vertices[i]) & set(vertices[j])) == k - 1))
        for i, j in combinations(range(len(vertices)), 2)
    )


def test_master_split_and_symmetric_giant_branches_have_verified_progress():
    G, blocks = make_symmetric_block_group(10, 2)
    values = [0] * G.degree
    for u in blocks[0]: values[u] = 1
    split = master_canonical_reduction(G, blocks, values)
    assert split.status == "certified_local_certificate_split"
    assert split.progress_verified and split.reduced_domain_size == 9

    giant = master_canonical_reduction(G, blocks, [0] * G.degree)
    assert giant.status == "exact_giant_parity_reduction"
    assert giant.giant_type == "S_m"
    assert giant.branch_count == 1 and giant.progress_verified


def test_master_alternating_giant_has_only_two_parity_branches():
    m = 8
    A = schreier_stabilizer_chain(_alternating_test_generators(m, tuple(range(m))))
    blocks = [(i,) for i in range(m)]
    r = master_canonical_reduction(A, blocks, [0] * m)
    assert r.status == "exact_giant_parity_reduction"
    assert r.giant_type == "A_m"
    assert r.branch_count == 2 and r.progress_verified


def test_pair_stage_verifies_square_root_scale_johnson_reductions():
    for v, k in ((5, 2), (6, 2), (6, 3)):
        n = len(list(combinations(range(v), k)))
        r = reduce_canonical_pair_structure(n, johnson_pair_weights(v, k))
        assert r.status == "exact_johnson_ground_reduction_available"
        assert r.reduced_domain_size == v
        assert r.progress_kind == "johnson_ground_domain"
        assert r.progress_verified


def test_nongiant_homogeneous_case_remains_explicitly_unresolved():
    m = 7
    rotate = tuple((i + 1) % m for i in range(m))
    G = schreier_stabilizer_chain([rotate])
    blocks = [(i,) for i in range(m)]
    r = master_canonical_reduction(G, blocks, [0] * m)
    assert r.status == "unresolved_homogeneous_design_or_coherent_obstruction"
    assert not r.progress_verified
