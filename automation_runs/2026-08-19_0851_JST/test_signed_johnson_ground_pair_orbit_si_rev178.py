from itertools import combinations

from permutation_group_schreier import inverse, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from signed_johnson_ground_pair_orbit_si_v1 import (
    signed_johnson_ground_pair_relation_orbit_si,
)


def cycle(v):
    return tuple((i + 1) % v for i in range(v))


def swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def induced_ground_group(v, k):
    subsets = tuple(combinations(range(v), k))
    index = {subset: i for i, subset in enumerate(subsets)}

    def induce(sigma):
        return tuple(
            index[tuple(sorted(sigma[x] for x in subset))]
            for subset in subsets
        )

    ground_gens = (swap01(v), cycle(v))
    domain_gens = tuple(induce(g) for g in ground_gens)
    return schreier_stabilizer_chain(domain_gens), domain_gens


def relabel_target(source, p):
    pinv = inverse(tuple(p))
    return tuple(source[pinv[j]] for j in range(len(source)))


def cycle_edge_colors(v):
    edges = {tuple(sorted((i, (i + 1) % v))) for i in range(v)}
    return tuple(int(pair in edges) for pair in combinations(range(v), 2))


def test_c9_exact_si_closes_by_relation_orbit_below_group_order():
    v, k = 9, 2
    G, gens = induced_ground_group(v, k)
    assert G.order == 362880
    source = cycle_edge_colors(v)
    witness = gens[1]
    target = relabel_target(source, witness)

    got = signed_johnson_ground_pair_relation_orbit_si(
        G,
        source,
        target,
        root_n=64,
        max_relation_states=30000,
    )
    assert got.status == "exact_signed_ground_pair_relation_orbit_coset", got
    assert got.exact and got.terminal_certified and got.local_cost_certified
    assert got.pair_relation_determines_string
    assert not got.complement_in_image
    assert got.pair_relation_orbit_states == 20160
    assert got.pair_relation_orbit_states < G.order
    assert got.coset is not None and got.coset.contains(witness)
    assert got.coset.subgroup.order == 18
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_relation_orbit_cap_fails_closed_without_exact_claim():
    v, k = 9, 2
    G, gens = induced_ground_group(v, k)
    source = cycle_edge_colors(v)
    target = relabel_target(source, gens[1])

    got = signed_johnson_ground_pair_relation_orbit_si(
        G,
        source,
        target,
        root_n=64,
        max_relation_states=100,
    )
    assert got.status == "undetermined_signed_ground_pair_relation_orbit_limit", got
    assert not got.exact and not got.terminal_certified
    assert not got.local_cost_certified
    assert got.pair_relation_orbit_states == 100
