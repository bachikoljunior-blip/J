from types import SimpleNamespace

import design_tuple_full_string_union_si_v1 as _union
from coset_stabilizer_primitives import RightCoset
from design_full_string_child_preflight_v1 import (
    design_full_string_child_preflight,
    record_design_full_string_child_execution,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _branch(degree=4):
    group = schreier_stabilizer_chain((identity(degree),))
    return SimpleNamespace(coset=RightCoset(group, identity(degree)))


def test_complete_small_order_cover_is_reserved_before_execution():
    branches = (_branch(), _branch())
    got = design_full_string_child_preflight(
        branches, original_root_degree=16, original_degree=4,
        group_order_poly_power=2, max_group_order=256, max_work=10**30,
    )
    assert got.admitted and got.branch_count == 2
    assert got.subgroup_orders == (1, 1)
    assert got.work_upper_bound == 2 * (4**12) * (2**24)


def test_structural_branch_is_rejected_as_a_separate_unsolved_problem():
    cycle = tuple((i + 1) % 9 for i in range(9))
    group = schreier_stabilizer_chain((cycle,))
    branch = SimpleNamespace(coset=RightCoset(group, identity(9)))
    got = design_full_string_child_preflight(
        (branch,), original_root_degree=9, original_degree=9,
        group_order_poly_power=1, max_group_order=8, max_work=10**30,
    )
    assert not got.admitted
    assert got.status == "design_full_string_structural_child_preflight_unavailable"


def test_budget_rejection_happens_before_candidate_solver(monkeypatch):
    branch = _branch()
    plan = SimpleNamespace(
        exact_empty=False,
        complete=True,
        status="certified_complete_design_tuple_transport_cover",
        branches=(branch,),
        surviving_branch_count=1,
        local_log2_cost_bound=1.0,
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("candidate solver started before full-cover preflight")

    monkeypatch.setattr(_union, "candidate_coset_string_isomorphism_u2", forbidden)
    ambient = branch.coset.subgroup
    got = _union.solve_design_tuple_transport_full_string(
        ambient, plan, (0, 0, 0, 0), (0, 0, 0, 0),
        root_n=16, max_design_full_string_child_work=1,
    )
    assert got.status == "design_full_string_child_work_cap_exceeded"
    assert got.branches_checked == 0
    assert got.child_preflight is not None and not got.child_preflight.admitted


def test_execution_record_cannot_exceed_reserved_scans():
    preflight = design_full_string_child_preflight(
        (_branch(),), original_root_degree=16, original_degree=4,
        group_order_poly_power=2, max_group_order=256, max_work=10**30,
    )
    child = SimpleNamespace(permutation_candidates_checked=2)
    done = record_design_full_string_child_execution(
        preflight, (child,), complete=True,
    )
    assert done.complete and done.executed_branch_count == 1
    assert done.permutation_candidates_checked == 2
