from dataclasses import replace
from itertools import combinations

from uniform_neighborhood_twl_branch_cost_v1 import (
    certify_uniform_neighborhood_twl_branch_cost,
)
from uniform_neighborhood_twl_design_family_v1 import (
    close_uniform_neighborhood_relation_with_twl_family,
)
from uniform_neighborhood_twl_recurrence_frontier_v1 import (
    certify_uniform_neighborhood_twl_recurrence_frontier,
)


def _fano_progress_and_cost():
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
    progress = close_uniform_neighborhood_relation_with_twl_family(
        7,
        3,
        coords,
        colors,
        root_n=7,
        max_tuple_states=1000,
        max_family_work_units=2000000,
        max_branch_work_units=500000,
    )
    cost = certify_uniform_neighborhood_twl_branch_cost(
        progress,
        root_n=7,
        neighborhood_count=7,
    )
    return progress, cost


def test_fano_all_seven_design_branches_form_certified_aux_shrink_frontier():
    progress, cost = _fano_progress_and_cost()
    assert progress.branch_child_aux_sizes == ((1, 6),) * 7
    got = certify_uniform_neighborhood_twl_recurrence_frontier(progress, cost)
    assert got.status == "certified_twl_design_aux_shrink_frontier"
    assert got.exact
    assert got.canonical
    assert got.branch_cost_certified
    assert got.all_branch_edges_shrink
    assert got.branch_count == 7
    assert got.total_child_occurrences == 14
    assert got.max_child_aux_size == 6


def test_frontier_rejects_a_nonshrinking_materialized_child():
    progress, cost = _fano_progress_and_cost()
    bad = replace(
        progress,
        branch_child_aux_sizes=((1, 7),) + progress.branch_child_aux_sizes[1:],
    )
    got = certify_uniform_neighborhood_twl_recurrence_frontier(bad, cost)
    assert got.status == "undetermined_twl_frontier_insufficient_aux_shrink"
    assert not got.exact
    assert not got.all_branch_edges_shrink


def test_frontier_requires_independent_branch_cost_certificate():
    progress, cost = _fano_progress_and_cost()
    bad_cost = replace(cost, certified=False)
    got = certify_uniform_neighborhood_twl_recurrence_frontier(progress, bad_cost)
    assert got.status == "undetermined_twl_frontier_branch_cost"
    assert not got.exact
