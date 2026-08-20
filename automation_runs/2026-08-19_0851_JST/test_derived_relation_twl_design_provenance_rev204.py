from __future__ import annotations

from itertools import combinations

from derived_relation_twl_design_provenance_v1 import (
    certify_paired_parent_derived_twl_design,
)


def _edges_from_hyperedges(hyperedges):
    return {(a, b) for a, edge in enumerate(hyperedges) for b in edge}


def _relabel_hypergraph(hyperedges, right_perm):
    return [tuple(sorted(right_perm[b] for b in edge)) for edge in hyperedges]


def test_cycle5_parent_relation_reaches_exact_upcc_family():
    hyperedges = [(i, (i + 1) % 5) for i in range(5)]
    edges = _edges_from_hyperedges(hyperedges)
    got = certify_paired_parent_derived_twl_design(
        5,
        5,
        edges,
        edges,
        max_tuple_states=100,
        max_rounds=16,
        max_work_units=2_000_000,
    )
    assert got.status == "certified_paired_parent_derived_twl_design_family"
    assert got.parent_relation_provenance_verified
    assert got.structural_family_complete
    outcomes = got.paired_design_family.source.witness_outcomes
    assert len(outcomes) == 1
    assert outcomes[0].status == "certified_twl_upcc"


def test_two_disjoint_triangles_parent_relation_reaches_imprimitive_split():
    hyperedges = list(combinations((0, 1, 2), 2)) + list(combinations((3, 4, 5), 2))
    edges = _edges_from_hyperedges(hyperedges)
    got = certify_paired_parent_derived_twl_design(
        6,
        6,
        edges,
        edges,
        max_tuple_states=100,
        max_rounds=16,
        max_work_units=4_000_000,
    )
    assert got.status == "certified_paired_parent_derived_twl_design_family"
    outcome = got.paired_design_family.source.witness_outcomes[0]
    assert outcome.status == "certified_twl_imprimitive_alpha_partition"
    assert sorted(map(len, outcome.output_partition)) == [3, 3]


def test_parent_relabeling_preserves_complete_design_family_invariants():
    hyperedges = [(i, (i + 1) % 5) for i in range(5)]
    image = (2, 4, 1, 3, 0)
    source = _edges_from_hyperedges(hyperedges)
    target = _edges_from_hyperedges(_relabel_hypergraph(hyperedges, image))
    got = certify_paired_parent_derived_twl_design(
        5,
        5,
        source,
        target,
        max_tuple_states=100,
        max_rounds=16,
        max_work_units=4_000_000,
    )
    assert got.status == "certified_paired_parent_derived_twl_design_family"
    assert got.paired_design_family.invariant_compatible


def test_arity_one_no_large_twin_relation_is_direct_alpha_partition():
    hyperedges = [(0,), (1,), (2,)]
    edges = _edges_from_hyperedges(hyperedges)
    got = certify_paired_parent_derived_twl_design(3, 6, edges, edges)
    assert got.status == "certified_paired_parent_derived_point_partition"
    assert sorted(map(len, got.source_direct_partition)) == [3, 3]
    assert got.structural_family_complete


def test_unique_large_relation_twin_case_is_not_reprocessed_by_design():
    hyperedges = [(0,), (1,), (2,)]
    edges = _edges_from_hyperedges(hyperedges)
    got = certify_paired_parent_derived_twl_design(3, 7, edges, edges)
    assert got.status == "parent_derived_twl_design_not_applicable"
    assert not got.structural_family_complete


def test_parent_relation_resource_failure_remains_undetermined():
    hyperedges = [
        (0, 1, 2, 3),
        (0, 1, 4, 5),
        (2, 3, 6, 7),
        (4, 5, 6,7),
    ]
    edges = _edges_from_hyperedges(hyperedges)
    got = certify_paired_parent_derived_twl_design(
        4, 8, edges, edges, max_subsets=10
    )
    assert got.status == "parent_derived_twl_design_not_applicable"
    assert not got.structural_family_complete


def test_arity_one_equal_size_cells_are_paired_by_relation_color_not_labels():
    hyperedges = [(0,), (1,), (2,)]
    source = _edges_from_hyperedges(hyperedges)
    image = (3, 4, 5, 0, 1, 2)
    target = _edges_from_hyperedges(_relabel_hypergraph(hyperedges, image))
    got = certify_paired_parent_derived_twl_design(3, 6, source, target)
    assert got.status == "certified_paired_parent_derived_point_partition"
    # relation color 0 (not contained) precedes relation color 1 (contained).
    assert got.source_direct_partition == ((3, 4, 5), (0, 1, 2))
    assert got.target_direct_partition == ((0, 1, 2), (3, 4, 5))
    for src_cell, dst_cell in zip(got.source_direct_partition, got.target_direct_partition):
        assert tuple(sorted(image[x] for x in src_cell)) == dst_cell
