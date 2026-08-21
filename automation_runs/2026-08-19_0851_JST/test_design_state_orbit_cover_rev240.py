from itertools import permutations
from types import SimpleNamespace

import design_tuple_full_string_union_si_v1 as _union
from bounded_group_transport import act_string
from coset_stabilizer_primitives import RightCoset
from design_full_string_child_preflight_v1 import design_full_string_child_preflight
from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_state_orbit_candidate_v1 import state_orbit_candidate_envelope


def _symmetric_group(n):
    return schreier_stabilizer_chain(tuple(permutations(range(n))))


def _plan(*branches):
    return SimpleNamespace(
        exact_empty=False,
        complete=True,
        status="certified_complete_design_tuple_transport_cover",
        branches=tuple(branches),
        surviving_branch_count=len(branches),
        local_log2_cost_bound=1.0,
    )


def test_complete_cover_enables_large_state_orbit_terminal():
    group = _symmetric_group(6)
    branch = SimpleNamespace(coset=RightCoset(group, identity(6)))
    values = (0, 0, 0, 0, 0, 1)
    got = _union.solve_design_tuple_transport_full_string(
        group, _plan(branch), values, values,
        root_n=6, max_group_order=2,
        max_design_full_string_child_work=10**20,
        quasipoly_constant=10**6,
    )
    assert got.exact and got.complete and got.coset is not None
    assert got.branch_results[0].status == "exact_state_orbit_candidate_coset"
    assert got.child_preflight is not None
    assert got.child_preflight.terminal_kinds == ("state_orbit",)
    assert got.child_preflight.state_orbit_image_upper_bounds == (6,)
    assert got.child_preflight.permutation_candidates_checked == 6


def test_all_branch_sum_rejects_before_first_candidate(monkeypatch):
    group = _symmetric_group(6)
    branch = SimpleNamespace(coset=RightCoset(group, identity(6)))
    values = (0, 0, 0, 0, 0, 1)
    one = state_orbit_candidate_envelope(branch.coset, values, max_work=10**20)
    cap = one.work_upper_bound + 1

    def forbidden(*_args, **_kwargs):
        raise AssertionError("candidate solver started before complete-cover admission")

    monkeypatch.setattr(_union, "candidate_coset_string_isomorphism_u2", forbidden)
    got = _union.solve_design_tuple_transport_full_string(
        group, _plan(branch, branch), values, values,
        root_n=6, max_group_order=2,
        max_design_full_string_child_work=cap,
    )
    assert got.status == "design_full_string_state_orbit_cover_work_cap_exceeded"
    assert got.branches_checked == 0
    assert got.child_preflight is not None
    assert got.child_preflight.work_upper_bound == cap + 1
    assert not got.child_preflight.admitted


def test_complete_cover_preserves_nonidentity_candidate_coordinates():
    group = _symmetric_group(5)
    shift = (1, 2, 3, 4, 0)
    branch = SimpleNamespace(coset=RightCoset(group, shift))
    source = (0, 0, 0, 1, 1)
    target = act_string(source, (2, 0, 1, 4, 3))
    got = _union.solve_design_tuple_transport_full_string(
        group, _plan(branch), source, target,
        root_n=5, max_group_order=2,
        max_design_full_string_child_work=10**20,
        quasipoly_constant=10**6,
    )
    assert got.exact and got.coset is not None
    assert act_string(source, got.coset.representative) == target
    assert got.branch_results[0].status == "exact_state_orbit_candidate_coset"


def test_complete_cover_can_prove_every_branch_empty():
    cycle = schreier_stabilizer_chain(((1, 2, 3, 4, 0),))
    branch = SimpleNamespace(coset=RightCoset(cycle, identity(5)))
    got = _union.solve_design_tuple_transport_full_string(
        cycle, _plan(branch),
        (1, 1, 0, 0, 0), (1, 0, 1, 0, 0),
        root_n=5, max_group_order=2,
        max_design_full_string_child_work=10**20,
        quasipoly_constant=10**6,
    )
    assert got.status == "exact_empty_design_tuple_full_string_union"
    assert got.exact and got.coset is None
    assert got.branch_results[0].status == "exact_empty_state_orbit_candidate"


def test_preflight_exposes_exact_per_branch_state_reservations():
    group = _symmetric_group(6)
    branch = SimpleNamespace(coset=RightCoset(group, identity(6)))
    values = (0, 0, 0, 0, 0, 1)
    envelope = state_orbit_candidate_envelope(branch.coset, values, max_work=10**20)
    got = design_full_string_child_preflight(
        (branch, branch), original_root_degree=6, original_degree=6,
        group_order_poly_power=2, max_group_order=2,
        max_work=2 * envelope.work_upper_bound,
        target_values=values,
    )
    assert got.admitted
    assert got.state_orbit_work_upper_bounds == (
        envelope.work_upper_bound, envelope.work_upper_bound,
    )
    assert got.work_upper_bound == 2 * envelope.work_upper_bound
    assert got.permutation_scan_upper_bounds == (6, 6)
