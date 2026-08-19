from itertools import combinations

from paired_uniform_neighborhood_design_branches_v1 import (
    pair_uniform_neighborhood_design_branches,
)


def _fano_relation(relabel=None):
    lines = {
        (0, 1, 2),
        (0, 3, 4),
        (0, 5, 6),
        (1, 3, 5),
        (1, 4, 6),
        (2, 3, 6),
        (2, 4, 5),
    }
    if relabel is not None:
        lines = {
            tuple(sorted(relabel[x] for x in line))
            for line in lines
        }
    coords = tuple(combinations(range(7), 3))
    colors = tuple(int(T in lines) for T in coords)
    return coords, colors


def _pair(source_colors, target_colors, *, max_branch_pairs=200000):
    coords = tuple(combinations(range(7), 3))
    return pair_uniform_neighborhood_design_branches(
        7,
        3,
        coords,
        source_colors,
        coords,
        target_colors,
        root_n=7,
        max_tuple_states=1000,
        max_family_work_units=2000000,
        max_branch_work_units=500000,
        max_branch_pairs=max_branch_pairs,
    )


def test_relabelled_fano_relations_get_complete_invariant_filtered_tuple_pair_cover():
    _, source = _fano_relation()
    _, target = _fano_relation((3, 0, 6, 2, 5, 1, 4))
    got = _pair(source, target)
    assert got.status == "certified_paired_uniform_neighborhood_design_branch_cover"
    assert got.exact
    assert got.complete
    assert not got.exact_empty
    assert got.paired_twl_status == "certified_paired_exact_twl_design_family"
    assert got.minimal_individualization_length == 1
    assert got.source_witness_count == 7
    assert got.target_witness_count == 7
    assert got.branch_count == 49
    assert got.branch_bound == 49
    assert len(got.branches) == 49
    assert got.source_frontier_ready
    assert got.target_frontier_ready
    assert {branch.outcome_status for branch in got.branches} == {"certified_twl_alpha_coloring"}


def test_color_multiplicity_mismatch_is_exact_empty():
    _, source = _fano_relation()
    target = list(source)
    zero = target.index(0)
    target[zero] = 1
    got = _pair(source, tuple(target))
    assert got.status == "exact_empty_uniform_neighborhood_color_multiplicity"
    assert got.exact_empty
    assert got.complete
    assert got.exact
    assert not got.branches


def test_complete_cover_is_not_partially_materialized_past_branch_cap():
    _, source = _fano_relation()
    _, target = _fano_relation((3, 0, 6, 2, 5, 1, 4))
    got = _pair(source, target, max_branch_pairs=10)
    assert got.status == "undetermined_paired_uniform_neighborhood_branch_cap"
    assert got.branch_count == 49
    assert got.branch_bound == 49
    assert not got.complete
    assert not got.exact
    assert not got.branches
