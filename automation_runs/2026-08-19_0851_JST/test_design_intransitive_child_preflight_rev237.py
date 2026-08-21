from types import SimpleNamespace

import design_tuple_full_string_union_si_v1 as _union
from coset_stabilizer_primitives import RightCoset
from design_full_string_child_preflight_v1 import design_full_string_child_preflight
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _intransitive_branch():
    left = (1, 2, 0, 3, 4, 5)
    right = (0, 1, 2, 4, 5, 3)
    group = schreier_stabilizer_chain((left, right))
    return SimpleNamespace(coset=RightCoset(group, identity(6)))


def _plan(branch):
    return SimpleNamespace(
        exact_empty=False,
        complete=True,
        status="certified_complete_design_tuple_transport_cover",
        branches=(branch,),
        surviving_branch_count=1,
        local_log2_cost_bound=1.0,
    )


def test_intransitive_parent_is_admitted_when_every_initial_orbit_image_is_small():
    got = design_full_string_child_preflight(
        (_intransitive_branch(),), original_root_degree=6, original_degree=6,
        group_order_poly_power=2, max_group_order=3, max_work=10**100,
    )
    assert got.admitted
    assert got.subgroup_orders == (9,)
    assert got.terminal_kinds == ("intransitive_small_order_orbit_images",)
    assert got.orbit_image_orders == ((3, 3),)
    assert got.permutation_scan_upper_bounds == (12,)


def test_intransitive_complete_cover_is_rejected_before_first_child_when_budget_short(monkeypatch):
    branch = _intransitive_branch()
    exact = design_full_string_child_preflight(
        (branch,), original_root_degree=6, original_degree=6,
        group_order_poly_power=2, max_group_order=3, max_work=10**100,
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("candidate solver started before intransitive cover reservation")

    monkeypatch.setattr(_union, "candidate_coset_string_isomorphism_u2", forbidden)
    got = _union.solve_design_tuple_transport_full_string(
        branch.coset.subgroup, _plan(branch),
        (0, 1, 2, 0, 1, 2), (0, 1, 2, 0, 1, 2),
        root_n=6, max_explicit_degree=1, max_group_order=3,
        max_design_full_string_child_work=exact.work_upper_bound - 1,
    )
    assert got.status == "design_full_string_child_work_cap_exceeded"
    assert got.branches_checked == 0


def test_intransitive_parent_executes_all_small_image_children_and_records_scans():
    branch = _intransitive_branch()
    got = _union.solve_design_tuple_transport_full_string(
        branch.coset.subgroup, _plan(branch),
        (0, 1, 2, 0, 1, 2), (0, 1, 2, 0, 1, 2),
        root_n=6, max_explicit_degree=1, max_group_order=3,
        max_design_full_string_child_work=10**100,
    )
    assert got.exact and got.complete and got.branches_checked == 1
    assert got.child_preflight is not None and got.child_preflight.complete
    assert got.child_preflight.permutation_candidates_checked == 12
