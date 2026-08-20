from __future__ import annotations

from bipartite_design_parent_union_v1 import (
    solve_design_witness_cover_in_parent_bipartite_action,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _cycle5_edges():
    neighborhoods = [(i, (i + 1) % 5) for i in range(5)]
    return {(a, b) for a, S in enumerate(neighborhoods) for b in S}


def _diagonal_cycle5_parent():
    parent_cycle = tuple((i + 1) % 5 for i in range(5)) + tuple(5 + ((i + 1) % 5) for i in range(5))
    group = schreier_stabilizer_chain([parent_cycle])
    right_index = {5 + i: i for i in range(5)}
    right_images = tuple(
        tuple(right_index[g[5 + i]] for i in range(5))
        for g in group.original_generators
    )
    return group, right_images, parent_cycle


def test_cycle5_complete_design_cover_reconstructs_full_parent_cyclic_coset():
    parent, right_images, parent_cycle = _diagonal_cycle5_parent()
    edges = _cycle5_edges()
    got = solve_design_witness_cover_in_parent_bipartite_action(
        parent,
        right_images,
        tuple(range(5)),
        tuple(range(5, 10)),
        edges,
        edges,
        alpha=0.75,
        max_tuple_states=100,
        max_twl_work_units=2_000_000,
        max_branch_pairs=100,
        max_auxiliary_degree=40,
        max_image_group_order=16,
    )
    assert got.status == "exact_design_parent_full_string_union_coset"
    assert got.exact and got.complete and got.set_reconstruction_complete
    assert not got.exact_empty
    assert got.coset is not None
    assert got.coset.subgroup.order == parent.order == 5
    assert got.coset.contains(identity(10))
    assert got.coset.contains(parent_cycle)
    assert got.structural_branches == got.branches_checked == 1
    assert not got.quasipolynomial_cost_certified


def test_full_parent_colors_filter_structural_cycle_cover_to_identity():
    parent, right_images, parent_cycle = _diagonal_cycle5_parent()
    edges = _cycle5_edges()
    distinct = tuple(range(5))
    got = solve_design_witness_cover_in_parent_bipartite_action(
        parent,
        right_images,
        tuple(range(5)),
        tuple(range(5, 10)),
        edges,
        edges,
        source_left_colors=distinct,
        target_left_colors=distinct,
        alpha=0.75,
        max_tuple_states=100,
        max_twl_work_units=2_000_000,
        max_branch_pairs=100,
        max_auxiliary_degree=40,
        max_image_group_order=16,
    )
    assert got.status == "exact_design_parent_full_string_union_coset"
    assert got.coset is not None
    assert got.coset.subgroup.order == 1
    assert got.coset.contains(identity(10))
    assert not got.coset.contains(parent_cycle)


def test_full_parent_color_inventory_mismatch_makes_complete_union_exact_empty():
    parent, right_images, _parent_cycle = _diagonal_cycle5_parent()
    edges = _cycle5_edges()
    got = solve_design_witness_cover_in_parent_bipartite_action(
        parent,
        right_images,
        tuple(range(5)),
        tuple(range(5, 10)),
        edges,
        edges,
        source_left_colors=(0, 1, 2, 3, 4),
        target_left_colors=(0, 1, 2, 3, 3),
        alpha=0.75,
        max_tuple_states=100,
        max_twl_work_units=2_000_000,
        max_branch_pairs=100,
        max_auxiliary_degree=40,
        max_image_group_order=16,
    )
    assert got.status == "exact_empty_design_parent_full_string_union"
    assert got.exact and got.complete and got.exact_empty
    assert got.set_reconstruction_complete
    assert got.coset is None


def test_child_auxiliary_cap_withholds_complete_union_fail_closed():
    parent, right_images, _parent_cycle = _diagonal_cycle5_parent()
    edges = _cycle5_edges()
    got = solve_design_witness_cover_in_parent_bipartite_action(
        parent,
        right_images,
        tuple(range(5)),
        tuple(range(5, 10)),
        edges,
        edges,
        alpha=0.75,
        max_tuple_states=100,
        max_twl_work_units=2_000_000,
        max_branch_pairs=100,
        max_auxiliary_degree=34,
        max_image_group_order=16,
    )
    assert got.status == "undetermined_design_parent_full_string_branch"
    assert not got.exact and not got.complete and not got.exact_empty
    assert got.coset is None
