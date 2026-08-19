from itertools import combinations

from permutation_group_schreier import schreier_stabilizer_chain
from signed_johnson_local_certificate_relation_v1 import (
    signed_johnson_local_certificate_relation,
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
        return tuple(
            index[tuple(sorted(sigma[x] for x in S))]
            for S in subsets
        )

    return schreier_stabilizer_chain((induce(swap01(v)), induce(cycle(v))))


def test_j52_distinct_string_builds_complete_exact_nonfull_certificate_relation():
    G = induced_johnson(5, 2)
    values = tuple(range(G.degree))
    got = signed_johnson_local_certificate_relation(
        G, values, values, 5, max_test_sets=10, max_quotient_leaves=100
    )
    assert got.status == "exact_signed_johnson_local_certificate_relations", got
    assert (got.ground_size, got.subset_size, got.test_size, got.test_count) == (5, 2, 5, 1)
    assert got.exact
    assert got.beard_calls == 1  # source==target reuses the exact certificate
    assert len(got.source_relation) == len(got.target_relation) == 1
    assert got.source_relation == got.target_relation
    token = got.source_relation[0][1]
    assert token[0] == "nonfull"
    assert got.source_aggregate is not None
    assert got.source_aggregate.status == "uniform_certificate_relation_no_progress"
    assert not got.theorem_scale_recurrence_evidence


def test_complete_family_limit_is_checked_before_any_beard_call():
    G = induced_johnson(10, 2)
    values = tuple(range(G.degree))
    got = signed_johnson_local_certificate_relation(
        G, values, values, 5, max_test_sets=100
    )
    assert got.status == "undetermined_certificate_family_limit", got
    assert got.test_count == 252
    assert got.beard_calls == 0
    assert not got.exact
    assert not got.theorem_scale_recurrence_evidence
