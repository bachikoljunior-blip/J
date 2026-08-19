from itertools import combinations

from permutation_group_schreier import schreier_stabilizer_chain
from signed_johnson_local_certificate_split_filter_v1 import (
    signed_johnson_local_certificate_split_filter,
)


def cycle(v):
    return tuple((i + 1) % v for i in range(v))


def swap01(v):
    p = list(range(v))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def induced_johnson(v, k):
    subsets = tuple(combinations(range(v), k))
    index = {S: i for i, S in enumerate(subsets)}

    def induce(sigma):
        return tuple(index[tuple(sorted(sigma[x] for x in S))] for S in subsets)

    return schreier_stabilizer_chain((induce(swap01(v)), induce(cycle(v))))


def test_exact_uniform_certificate_relation_is_not_overpromoted_to_a_split_filter():
    G = induced_johnson(5, 2)
    values = tuple(range(G.degree))
    got = signed_johnson_local_certificate_split_filter(
        G, values, values, 5, max_test_sets=10, max_quotient_leaves=100
    )
    assert got.status == "local_certificate_relation_without_significant_split", got
    assert got.relation.exact
    assert got.coset is None
    assert not got.exact_empty
    assert got.canonical_filter
    assert not got.theorem_scale_recurrence_evidence


def test_family_resource_limit_propagates_without_claiming_a_filter():
    G = induced_johnson(10, 2)
    values = tuple(range(G.degree))
    got = signed_johnson_local_certificate_split_filter(
        G, values, values, 5, max_test_sets=100
    )
    assert got.status == "undetermined_certificate_family_limit", got
    assert got.coset is None
    assert not got.relation.exact
    assert not got.canonical_filter
    assert not got.exact_empty
