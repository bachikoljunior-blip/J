from itertools import combinations
import random

from permutation_group_schreier import compose, inverse, schreier_stabilizer_chain
from master_canonical_reduction_v5 import master_canonical_reduction_v5


def cycle_group(n):
    cycle = tuple((i + 1) % n for i in range(n))
    return cycle, schreier_stabilizer_chain([cycle])


def conjugate_by_relabeling(g, q):
    return compose(compose(inverse(q), g), q)


def induced_symmetric_action_on_pairs(v):
    vertices = list(combinations(range(v), 2))
    index = {S: i for i, S in enumerate(vertices)}
    swap = list(range(v)); swap[0], swap[1] = swap[1], swap[0]
    cycle = tuple((i + 1) % v for i in range(v))
    gens = []
    for g in (tuple(swap), cycle):
        gens.append(tuple(index[tuple(sorted(g[x] for x in S))] for S in vertices))
    return schreier_stabilizer_chain(gens)


def test_c29_large_regular_primitive_action_is_now_an_exact_terminal():
    n = 29
    _, G = cycle_group(n)
    r = master_canonical_reduction_v5(
        G, [(i,) for i in range(n)], [0] * n,
        exact_terminal_size=24,
    )
    assert r.status == "primitive_regular_prime_exact_terminal"
    assert r.reduced_domain_size == 1
    assert r.regular_prime_coordinate_systems == n * (n - 1) == 812
    assert r.terminal_canonical_code is not None
    assert r.progress_verified


def test_c29_terminal_code_is_unchanged_by_arbitrary_domain_relabeling():
    n = 29
    cycle, G = cycle_group(n)
    base = master_canonical_reduction_v5(
        G, [(i,) for i in range(n)], [0] * n,
        exact_terminal_size=24,
    )
    q = list(range(n))
    random.Random(138).shuffle(q)
    q = tuple(q)
    Gq = schreier_stabilizer_chain([conjugate_by_relabeling(cycle, q)])
    relabeled = master_canonical_reduction_v5(
        Gq, [(i,) for i in range(n)], [0] * n,
        exact_terminal_size=24,
    )
    assert relabeled.status == base.status
    assert relabeled.terminal_canonical_code == base.terminal_canonical_code


def test_existing_large_johnson_reduction_is_preserved_before_regular_terminal():
    G = induced_symmetric_action_on_pairs(8)
    n = G.degree
    r = master_canonical_reduction_v5(
        G, [(i,) for i in range(n)], [0] * n,
        exact_terminal_size=24,
    )
    assert r.status == "primitive_orbital_exact_johnson_ground_reduction_available"
    assert r.reduced_domain_size == 8
    assert (r.johnson_ground_size, r.johnson_subset_size) == (8, 2)
    assert r.regular_prime_coordinate_systems == 0
    assert r.progress_verified


def test_regular_coordinate_limit_remains_fail_closed():
    n = 29
    _, G = cycle_group(n)
    r = master_canonical_reduction_v5(
        G, [(i,) for i in range(n)], [0] * n,
        exact_terminal_size=24,
        max_regular_coordinate_systems=100,
    )
    assert r.status == "primitive_orbital_relation_unresolved"
    assert not r.progress_verified
    assert r.terminal_canonical_code is None
