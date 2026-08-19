from permutation_group_schreier import schreier_stabilizer_chain
from master_canonical_reduction_v3 import master_canonical_reduction_v3


def cycle_group(n):
    return schreier_stabilizer_chain([tuple((i + 1) % n for i in range(n))])


def test_large_composite_cycle_now_gets_strict_canonical_block_reduction():
    n = 25
    G = cycle_group(n)
    r = master_canonical_reduction_v3(
        G, [(i,) for i in range(n)], [0] * n,
        exact_terminal_size=24,
    )
    assert r.status == "unique_canonical_imprimitive_quotient"
    assert r.progress_verified
    assert r.progress_kind == "quotient_block_decomposition"
    assert r.reduced_domain_size == 5
    assert r.branch_count == 5


def test_large_prime_cycle_remains_explicit_primitive_child():
    n = 29
    G = cycle_group(n)
    r = master_canonical_reduction_v3(
        G, [(i,) for i in range(n)], [0] * n,
        exact_terminal_size=24,
    )
    assert r.status == "primitive_quotient_action"
    assert not r.progress_verified


def test_existing_small_terminal_branch_is_unchanged():
    n = 7
    G = cycle_group(n)
    r = master_canonical_reduction_v3(G, [(i,) for i in range(n)], [0] * n)
    assert r.status == "exact_homogeneous_pair_terminal"
    assert r.progress_verified
