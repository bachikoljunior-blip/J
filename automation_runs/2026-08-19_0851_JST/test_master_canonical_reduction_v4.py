from itertools import combinations

from permutation_group_schreier import schreier_stabilizer_chain
from master_canonical_reduction_v4 import master_canonical_reduction_v4


def induced_symmetric_action_on_pairs(v):
    vertices = list(combinations(range(v), 2))
    index = {S: i for i, S in enumerate(vertices)}
    swap = list(range(v)); swap[0], swap[1] = swap[1], swap[0]
    cycle = tuple((i + 1) % v for i in range(v))
    gens = []
    for g in (tuple(swap), cycle):
        gens.append(tuple(index[tuple(sorted(g[x] for x in S))] for S in vertices))
    return schreier_stabilizer_chain(gens)


def test_large_primitive_johnson_action_reduces_after_terminal_gate():
    G = induced_symmetric_action_on_pairs(8)
    n = G.degree
    assert n == 28
    r = master_canonical_reduction_v4(
        G, [(i,) for i in range(n)], [0] * n,
        exact_terminal_size=24,
    )
    assert r.status == "primitive_orbital_exact_johnson_ground_reduction_available"
    assert r.reduced_domain_size == 8
    assert (r.johnson_ground_size, r.johnson_subset_size) == (8, 2)
    assert r.progress_verified


def test_prime_regular_large_primitive_action_remains_next_leaf():
    n = 29
    G = schreier_stabilizer_chain([tuple((i + 1) % n for i in range(n))])
    r = master_canonical_reduction_v4(
        G, [(i,) for i in range(n)], [0] * n,
        exact_terminal_size=24,
    )
    assert r.status == "primitive_orbital_relation_unresolved"
    assert not r.progress_verified
