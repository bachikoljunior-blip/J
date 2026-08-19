from itertools import combinations

from uniform_neighborhood_twl_branch_cost_v1 import (
    certify_uniform_neighborhood_twl_branch_cost,
)
from uniform_neighborhood_twl_design_family_v1 import (
    close_uniform_neighborhood_relation_with_twl_family,
)


def _fano_progress():
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
    return close_uniform_neighborhood_relation_with_twl_family(
        7,
        3,
        coords,
        colors,
        root_n=7,
        max_tuple_states=1000,
        max_family_work_units=2000000,
        max_branch_work_units=500000,
    )


def test_fano_family_has_certified_paired_quasipoly_branch_charge():
    progress = _fano_progress()
    got = certify_uniform_neighborhood_twl_branch_cost(
        progress,
        root_n=7,
        neighborhood_count=7,
    )
    assert got.status == "certified_uniform_neighborhood_twl_quasipoly_branch_cost"
    assert got.certified
    assert got.individualization_length == 1
    assert got.materialized_single_side_branches == 7
    assert got.single_side_branch_bound == 7
    assert got.paired_branch_bound == 49
    assert got.provenance_arity_cap == 6


def test_rev204_arity_provenance_gate_fails_closed():
    progress = _fano_progress()
    # m=1 gives rev204 provenance cap 1, which cannot have produced t=3.
    got = certify_uniform_neighborhood_twl_branch_cost(
        progress,
        root_n=7,
        neighborhood_count=1,
    )
    assert got.status == "undetermined_twl_branch_rev204_arity_gate"
    assert not got.certified


def test_rev205_preemption_adds_zero_twl_branch_charge():
    v, t = 6, 3
    coords = tuple(combinations(range(v), t))
    colors = tuple(int(0 in T) for T in coords)
    progress = close_uniform_neighborhood_relation_with_twl_family(v, t, coords, colors)
    got = certify_uniform_neighborhood_twl_branch_cost(
        progress,
        root_n=v,
        neighborhood_count=v,
    )
    assert got.status == "certified_zero_twl_branch_charge"
    assert got.certified
    assert got.materialized_single_side_branches == 0
    assert got.theorem_log2_branch_bound == 0.0
