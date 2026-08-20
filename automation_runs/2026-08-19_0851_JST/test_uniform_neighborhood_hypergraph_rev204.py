from itertools import combinations

from uniform_neighborhood_hypergraph_v1 import build_uniform_neighborhood_hypergraph


def _edges_from_neighborhoods(neighborhoods):
    return {(a, b) for a, S in enumerate(neighborhoods) for b in S}


def test_complete_two_subset_neighborhoods_give_explicit_johnson_embedding():
    subsets = tuple(combinations(range(4), 2))
    got = build_uniform_neighborhood_hypergraph(
        len(subsets), 4, _edges_from_neighborhoods(subsets), range(len(subsets))
    )
    assert got.status == "certified_complete_uniform_neighborhood_johnson_embedding"
    assert got.complete_uniform_hypergraph
    assert got.normalized_degree == 2
    assert not got.complemented
    assert tuple(S for _, S in got.johnson_embedding) == subsets


def test_dense_uniform_neighborhoods_are_complemented_before_johnson_recognition():
    neighborhoods = tuple(tuple(x for x in range(4) if x != missing) for missing in range(4))
    got = build_uniform_neighborhood_hypergraph(
        4, 4, _edges_from_neighborhoods(neighborhoods), range(4)
    )
    assert got.status == "certified_complete_uniform_neighborhood_johnson_embedding"
    assert got.complemented
    assert got.original_degree == 3
    assert got.normalized_degree == 1
    assert set(got.hyperedges) == set(combinations(range(4), 1))


def test_noncomplete_uniform_hypergraph_produces_exact_nonconstant_test_relation():
    neighborhoods = ((0, 1), (0, 2), (3, 4))
    got = build_uniform_neighborhood_hypergraph(
        3, 5, _edges_from_neighborhoods(neighborhoods), range(3)
    )
    assert got.status == "certified_nonconstant_uniform_neighborhood_test_relation"
    assert not got.complete_uniform_hypergraph
    assert got.test_relation_nonconstant
    assert got.test_arity == 2
    assert set(got.test_colors) == {0, 1}


def test_duplicate_full_neighborhoods_fail_closed_as_left_twins():
    neighborhoods = ((0, 1), (0, 1), (2, 3))
    got = build_uniform_neighborhood_hypergraph(
        3, 4, _edges_from_neighborhoods(neighborhoods), range(3)
    )
    assert got.status == "uniform_neighborhood_left_twins_present"
    assert not got.complete_uniform_hypergraph
    assert not got.test_relation_nonconstant
