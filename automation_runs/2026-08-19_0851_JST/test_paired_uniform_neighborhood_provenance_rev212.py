from itertools import combinations

from paired_uniform_neighborhood_provenance_v1 import (
    certify_paired_uniform_neighborhood_provenance,
)


def _fano_edges(right_perm=None, left_perm=None):
    lines = [
        (0, 1, 2),
        (0, 3, 4),
        (0, 5, 6),
        (1, 3, 5),
        (1, 4, 6),
        (2, 3, 6),
        (2, 4, 5),
    ]
    right_perm = tuple(range(7)) if right_perm is None else tuple(right_perm)
    left_perm = tuple(range(7)) if left_perm is None else tuple(left_perm)
    return tuple(
        (left_perm[a], right_perm[b])
        for a, line in enumerate(lines)
        for b in line
    )


def test_relabelled_fano_bipartite_states_certify_same_nonconstant_v2_relation_provenance():
    source = _fano_edges()
    target = _fano_edges(
        right_perm=(3, 0, 6, 2, 5, 1, 4),
        left_perm=(6, 2, 4, 0, 5, 1, 3),
    )
    got = certify_paired_uniform_neighborhood_provenance(7, 7, source, target)
    assert got.status == "certified_paired_uniform_neighborhood_test_relation_provenance"
    assert got.exact
    assert not got.exact_empty
    assert got.derived_relation_certified
    assert not got.paired_johnson_certified
    assert got.normalized_degree == 3
    assert not got.complemented
    assert got.selected_left_count == 7
    assert got.test_arity == 3
    assert got.source_coordinates == tuple(combinations(range(7), 3))
    assert got.target_coordinates == got.source_coordinates
    assert sorted(got.source_colors) == sorted(got.target_colors)
    assert sum(got.source_colors) == 7
    assert sum(got.target_colors) == 7


def test_complete_uniform_neighborhoods_certify_paired_johnson_provenance():
    neighborhoods = tuple(combinations(range(4), 2))
    source = tuple((a, b) for a, pair in enumerate(neighborhoods) for b in pair)
    right_perm = (2, 0, 3, 1)
    left_perm = (5, 2, 0, 4, 1, 3)
    target = tuple(
        (left_perm[a], right_perm[b])
        for a, pair in enumerate(neighborhoods)
        for b in pair
    )
    got = certify_paired_uniform_neighborhood_provenance(6, 4, source, target)
    assert got.status == "certified_paired_uniform_neighborhood_johnson_provenance"
    assert got.exact
    assert got.paired_johnson_certified
    assert not got.derived_relation_certified
    assert got.normalized_degree == 2
    assert got.selected_left_count == 6


def test_degree_inventory_mismatch_is_exact_empty_before_hypergraph_stage():
    source = _fano_edges()
    target = list(source)
    target.remove((0, 0))
    got = certify_paired_uniform_neighborhood_provenance(7, 7, source, tuple(target))
    assert got.status == "exact_empty_bipartite_degree_inventory"
    assert got.exact
    assert got.exact_empty
    assert got.source_hypergraph is None
    assert got.target_hypergraph is None
