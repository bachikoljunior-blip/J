import pytest

from design_tuple_transport_resource_envelope_v1 import (
    design_tuple_transport_resource_envelope,
    record_design_tuple_transport_execution,
)


def _bound(cap=10**12, **overrides):
    args = dict(
        original_root_degree=16,
        original_degree=8,
        ground_size=8,
        individualization_length=2,
        branch_count=9,
        group_order=16,
        generator_count=3,
        max_work=cap,
    )
    args.update(overrides)
    return design_tuple_transport_resource_envelope(**args)


def test_reserves_all_cartesian_branches_and_generator_edges():
    got = _bound()
    assert got.admitted
    assert got.orbit_states_per_branch_upper_bound == 16
    assert got.generator_edges_per_branch_upper_bound == 48
    assert got.work_upper_bound == 9 + 9 * got.work_per_branch_upper_bound


def test_runtime_caps_are_not_theorem_inputs_and_small_budget_fails_closed():
    exact = _bound()
    rejected = _bound(cap=exact.work_upper_bound - 1)
    assert not rejected.admitted
    assert rejected.status == "design_tuple_transport_work_cap_exceeded"


def test_original_root_lift_and_log_arity_are_required():
    assert not _bound(original_degree=17).root_lift_certified
    assert not _bound(ground_size=17).root_lift_certified
    assert not _bound(individualization_length=5).root_lift_certified


def test_execution_is_charged_once_and_cannot_exceed_reservation():
    envelope = _bound()
    done = record_design_tuple_transport_execution(
        envelope,
        executed_branches=9,
        executed_orbit_states=100,
        executed_action_steps=300,
        complete=True,
    )
    assert done.complete
    assert done.charged_work_upper_bound == done.work_upper_bound
    with pytest.raises(ValueError):
        record_design_tuple_transport_execution(
            envelope,
            executed_branches=10,
            executed_orbit_states=0,
            executed_action_steps=0,
            complete=False,
        )
