from permutation_group_schreier import schreier_stabilizer_chain
from master_canonical_reduction_v2 import master_canonical_reduction_v2


def test_small_regular_nongiant_obstruction_finishes_in_exact_terminal():
    m = 7
    rotate = tuple((i + 1) % m for i in range(m))
    G = schreier_stabilizer_chain([rotate])
    blocks = [(i,) for i in range(m)]
    r = master_canonical_reduction_v2(G, blocks, [0] * m)
    assert r.status == "exact_homogeneous_pair_terminal"
    assert r.progress_verified
    assert r.progress_kind == "exact_terminal"
    assert r.terminal_canonical_code is not None


def test_terminal_size_gate_preserves_large_case_as_unresolved():
    m = 25
    rotate = tuple((i + 1) % m for i in range(m))
    G = schreier_stabilizer_chain([rotate])
    blocks = [(i,) for i in range(m)]
    r = master_canonical_reduction_v2(
        G, blocks, [0] * m,
        exact_terminal_size=24,
        max_test_sets=100000,
    )
    assert r.status == "unresolved_large_homogeneous_design_or_coherent_obstruction"
    assert not r.progress_verified
    assert r.terminal_canonical_code is None
