from itertools import combinations

from paired_uniform_neighborhood_design_branches_v1 import (
    pair_uniform_neighborhood_design_branches,
)
from paired_uniform_neighborhood_tuple_transport_v1 import (
    transport_paired_uniform_neighborhood_design_branches,
)
from permutation_group_schreier import schreier_stabilizer_chain


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
    return coords, tuple(int(T in lines) for T in coords)


def _fano_plan(target_colors=None):
    coords, source = _fano_colors()
    target = source if target_colors is None else tuple(target_colors)
    return pair_uniform_neighborhood_design_branches(
        7,
        3,
        coords,
        source,
        coords,
        target,
        root_n=7,
        max_tuple_states=1000,
        max_family_work_units=2000000,
        max_branch_work_units=500000,
    )


def test_two_point_ambient_group_filters_49_fano_pairs_to_exact_9_cosets():
    plan = _fano_plan()
    assert plan.branch_count == 49
    swap = (1, 0, 2, 3, 4, 5, 6)
    group = schreier_stabilizer_chain([swap])
    got = transport_paired_uniform_neighborhood_design_branches(
        group,
        ((swap, False),),
        plan,
        max_partition_states=10,
    )
    assert got.status == "certified_complete_paired_uniform_neighborhood_tuple_transport"
    assert got.exact
    assert got.complete
    assert not got.exact_empty
    assert got.input_branch_count == 49
    assert got.surviving_branch_count == 9
    survivor_pairs = {
        (branch.source_individualized, branch.target_individualized)
        for branch in got.branches
    }
    expected = {
        ((0,), (0,)), ((0,), (1,)), ((1,), (0,)), ((1,), (1,)),
        ((2,), (2,)), ((3,), (3,)), ((4,), (4,)), ((5,), (5,)), ((6,), (6,)),
    }
    assert survivor_pairs == expected


def test_partition_orbit_cap_withholds_entire_transport_cover():
    plan = _fano_plan()
    swap = (1, 0, 2, 3, 4, 5, 6)
    group = schreier_stabilizer_chain([swap])
    got = transport_paired_uniform_neighborhood_design_branches(
        group,
        ((swap, False),),
        plan,
        max_partition_states=1,
    )
    assert got.status == "undetermined_signed_ground_partition_orbit_limit"
    assert not got.exact
    assert not got.complete
    assert not got.branches


def test_upstream_exact_empty_remains_exact_empty_without_partial_transport():
    coords, source = _fano_colors()
    target = list(source)
    target[target.index(0)] = 1
    plan = _fano_plan(target)
    assert plan.exact_empty
    swap = (1, 0, 2, 3, 4, 5, 6)
    group = schreier_stabilizer_chain([swap])
    got = transport_paired_uniform_neighborhood_design_branches(
        group,
        ((swap, False),),
        plan,
    )
    assert got.status == "exact_empty_paired_uniform_neighborhood_plan"
    assert got.exact_empty
    assert got.complete
    assert got.exact
    assert got.surviving_branch_count == 0
