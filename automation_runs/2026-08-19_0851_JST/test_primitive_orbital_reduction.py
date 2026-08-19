from itertools import combinations

from permutation_group_schreier import schreier_stabilizer_chain
from primitive_orbital_reduction import reduce_primitive_quotient_by_orbital_sizes


def induced_action_on_k_subsets(v, k):
    vertices = list(combinations(range(v), k))
    index = {S: i for i, S in enumerate(vertices)}
    swap = list(range(v)); swap[0], swap[1] = swap[1], swap[0]
    cycle = tuple((i + 1) % v for i in range(v))
    out = []
    for g in (tuple(swap), cycle):
        p = []
        for S in vertices:
            p.append(index[tuple(sorted(g[x] for x in S))])
        out.append(tuple(p))
    return schreier_stabilizer_chain(out)


def test_primitive_s5_two_subset_action_reduces_to_five_ground_points():
    G = induced_action_on_k_subsets(5, 2)
    n = G.degree
    r = reduce_primitive_quotient_by_orbital_sizes(
        G, [(i,) for i in range(n)], [0] * n
    )
    assert r.status == "primitive_orbital_exact_johnson_ground_reduction_available"
    assert r.orbital_signature_count == 2
    assert r.reduced_domain_size == 5
    assert (r.johnson_ground_size, r.johnson_subset_size) == (5, 2)
    assert r.progress_verified


def test_prime_regular_cycle_is_primitive_but_orbital_size_coarsening_stays_unresolved():
    n = 29
    rotate = tuple((i + 1) % n for i in range(n))
    G = schreier_stabilizer_chain([rotate])
    r = reduce_primitive_quotient_by_orbital_sizes(
        G, [(i,) for i in range(n)], [0] * n
    )
    assert r.status == "primitive_orbital_relation_unresolved"
    assert r.orbital_signature_count == 1
    assert not r.progress_verified
