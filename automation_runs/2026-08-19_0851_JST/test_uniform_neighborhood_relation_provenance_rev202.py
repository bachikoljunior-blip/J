from __future__ import annotations

from itertools import combinations, permutations

from uniform_neighborhood_relation_provenance_v1 import (
    certify_paired_uniform_neighborhood_provenance,
    derive_uniform_neighborhood_relation,
)


def _edges_from_hyperedges(hyperedges):
    return {(a, b) for a, edge in enumerate(hyperedges) for b in edge}


def _relabel_hypergraph(hyperedges, right_perm, left_perm=None):
    mapped = [tuple(sorted(right_perm[b] for b in edge)) for edge in hyperedges]
    if left_perm is None:
        return mapped
    out = [None] * len(mapped)
    for old, new in enumerate(left_perm):
        out[new] = mapped[old]
    return out


def test_complete_uniform_family_emits_explicit_johnson_embedding():
    hyperedges = list(combinations(range(4), 2))
    got = derive_uniform_neighborhood_relation(6, 4, _edges_from_hyperedges(hyperedges))
    assert got.status == "explicit_johnson_embedding"
    assert got.normalized_degree == 2
    assert len(got.johnson_embedding) == 6
    assert {subset for _, subset in got.johnson_embedding} == set(hyperedges)


def test_cycle_neighborhoods_emit_nonconstant_pair_containment_relation():
    hyperedges = [(0, 1), (1, 2), (2, 3), (0, 3)]
    got = derive_uniform_neighborhood_relation(4, 4, _edges_from_hyperedges(hyperedges))
    assert got.status == "nonconstant_containment_relation"
    assert got.relation_arity == 2
    assert got.relation_inventory == ((0, 2), (1, 4))


def test_dense_complement_normalization_preserves_structural_relation():
    sparse = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)]
    dense = [tuple(sorted(set(range(5)) - set(edge))) for edge in sparse]
    a = derive_uniform_neighborhood_relation(5, 5, _edges_from_hyperedges(sparse))
    b = derive_uniform_neighborhood_relation(5, 5, _edges_from_hyperedges(dense))
    assert not a.complemented
    assert b.complemented
    assert a.neighborhoods == b.neighborhoods
    assert a.relation_inventory == b.relation_inventory


def test_all_left_and_right_relabelings_preserve_paired_relation_inventory():
    hyperedges = [(0, 1), (1, 2), (2, 3), (0, 3)]
    source_edges = _edges_from_hyperedges(hyperedges)
    for lp in permutations(range(4)):
        for rp in permutations(range(4)):
            target_hyperedges = _relabel_hypergraph(hyperedges, rp, lp)
            got = certify_paired_uniform_neighborhood_provenance(
                4, 4, source_edges, _edges_from_hyperedges(target_hyperedges)
            )
            assert got.status == "paired_nonconstant_containment_relation_provenance"
            assert got.provenance_verified
            assert got.relation_inventory == ((0, 2), (1, 4))


def test_duplicate_neighborhoods_fail_closed_as_left_twins():
    hyperedges = [(0, 1), (0, 1), (2, 3)]
    got = derive_uniform_neighborhood_relation(3, 4, _edges_from_hyperedges(hyperedges))
    assert got.status == "uniform_neighborhood_requires_twin_free_left"


def test_subset_resource_limit_fails_closed():
    # Four distinct 4-subsets on an 8-point ground; theorem arity is 4, so C(8,4)=70.
    hyperedges = [
        (0, 1, 2, 3),
        (0, 1, 4, 5),
        (2, 3, 6, 7),
        (4, 5, 6, 7),
    ]
    got = derive_uniform_neighborhood_relation(
        4, 8, _edges_from_hyperedges(hyperedges), max_subsets=10
    )
    assert got.status == "undetermined_containment_relation_subset_limit"
