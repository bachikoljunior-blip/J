from itertools import combinations

from uniform_neighborhood_twl_design_family_v1 import (
    close_uniform_neighborhood_relation_with_twl_family,
)


def _fano_colors():
    lines = {
        (0, 1, 2),
        (0, 3, 4),
        (0, 5, 6),
        (1, 3, 5),
        (1, 4, 6),
        (2, 3, 6),
        (2, 4, 5),
    }
    coords = tuple(combinations(range(7), 3))
    colors = tuple(int(T in lines) for T in coords)
    return coords, colors


def test_fano_codegree_homogeneous_relation_gets_canonical_twl_branch_progress():
    coords, colors = _fano_colors()
    got = close_uniform_neighborhood_relation_with_twl_family(
        7,
        3,
        coords,
        colors,
        max_tuple_states=1000,
        max_family_work_units=2000000,
        max_branch_work_units=500000,
    )
    assert got.base_descent_status == "right_higher_arity_design_unresolved"
    assert got.twl_family_status == "certified_exact_twl_design_witness_family"
    assert got.status == "certified_canonical_twl_design_branch_decomposition"
    assert got.canonical_branch_family
    assert got.exact
    assert got.minimal_individualization_length == 1
    assert got.branch_count == 7
    assert got.branch_bound == 7
    assert got.progress_branch_count == 7
    assert got.residual_branch_count == 0
    assert got.all_witness_branches_progress
    assert set(got.branch_statuses) == {"certified_design_auxiliary_split_progress"}
    assert got.max_child_aux_size == 6


def test_reversed_complete_coordinate_order_is_canonicalized_before_twl():
    coords, colors = _fano_colors()
    got = close_uniform_neighborhood_relation_with_twl_family(
        7,
        3,
        tuple(reversed(coords)),
        tuple(reversed(colors)),
        max_tuple_states=1000,
        max_family_work_units=2000000,
        max_branch_work_units=500000,
    )
    assert got.status == "certified_canonical_twl_design_branch_decomposition"
    assert got.branch_count == 7
    assert got.max_child_aux_size == 6


def test_exact_twl_resource_gate_fails_closed_after_rev205_stalls():
    coords, colors = _fano_colors()
    got = close_uniform_neighborhood_relation_with_twl_family(
        7,
        3,
        coords,
        colors,
        max_tuple_states=100,
    )
    assert got.base_descent_status == "right_higher_arity_design_unresolved"
    assert got.status == "undetermined_exact_twl_design_family"
    assert got.twl_family_status == "undetermined_twl_design_tuple_state_cap"
    assert not got.exact
    assert not got.all_witness_branches_progress


def test_rev205_significant_split_preempts_expensive_twl_family():
    v, t = 6, 3
    coords = tuple(combinations(range(v), t))
    colors = tuple(int(0 in T) for T in coords)
    got = close_uniform_neighborhood_relation_with_twl_family(v, t, coords, colors)
    assert got.status == "rev205_descent_preempts_twl_family"
    assert got.base_descent_status == "certified_right_design_codegree_split"
    assert got.twl_family_status is None
    assert got.all_witness_branches_progress
    assert got.exact
