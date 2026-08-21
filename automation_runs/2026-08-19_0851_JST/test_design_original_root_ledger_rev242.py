from types import SimpleNamespace

import colored_subset_design_branch_plan_v1 as _plan
import design_branch_tuple_transport_v1 as _transport
from design_original_root_ledger_v1 import design_original_root_ledger


def _ledger(**overrides):
    kwargs = dict(
        max_states=3,
        max_wl_vertices=64,
        max_wl_rounds=2,
        max_branch_pairs=5,
        max_partition_states=7,
        max_design_full_string_child_work=11,
        max_design_union_reconstruction_work=13,
        max_work=10**9,
    )
    kwargs.update(overrides)
    return design_original_root_ledger(8, 4, 2, **kwargs)


def test_original_root_ledger_reserves_every_design_phase():
    got = _ledger()
    assert got.admitted
    assert got.status == "certified_design_original_root_ledger"
    assert got.wl_work_upper_bound > 0
    assert got.materialization_work_upper_bound > 0
    assert got.tuple_transport_work_upper_bound > 0
    assert got.child_si_work_upper_bound == 11
    assert got.union_work_upper_bound == 13
    assert got.partition_state_cap == 7
    assert got.work_upper_bound <= got.max_work


def test_rejected_ledger_stops_before_first_witness_wl(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("witness/WL executed before original-root ledger admission")

    monkeypatch.setattr(_plan, "find_colored_subset_design_witness_family", forbidden)
    colors = (0,) * 6
    got = _plan.build_colored_subset_design_branch_plan(
        4,
        2,
        colors,
        colors,
        original_root_degree=8,
        max_states=3,
        max_wl_vertices=64,
        max_wl_rounds=2,
        max_branch_pairs=5,
        max_partition_states=7,
        max_design_full_string_child_work=11,
        max_design_union_reconstruction_work=13,
        max_original_root_design_work=1,
    )
    assert got.status == "design_original_root_ledger_work_cap_exceeded"
    assert not got.complete
    assert got.source_family is None and got.target_family is None
    assert got.original_root_ledger is not None
    assert got.original_root_ledger.work_upper_bound == 2


def test_tuple_transport_cannot_expand_pre_wl_reservation(monkeypatch):
    ledger = _ledger()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("tuple transporter started after ledger mismatch")

    monkeypatch.setattr(_transport, "_signed_partition_transporter", forbidden)
    branch_plan = SimpleNamespace(
        vertex_count=4,
        individualization_length=1,
        branch_count=1,
        exact_empty=False,
        complete=True,
        status="certified_complete_design_branch_plan",
        branches=(((0,), (0,)),),
        local_log2_cost_bound=1.0,
        original_root_ledger=ledger,
    )
    group = SimpleNamespace(degree=8)
    got = _transport.transport_complete_design_tuple_branches(
        group, (), branch_plan, max_partition_states=8,
    )
    assert got.status == "design_tuple_transport_exceeds_original_root_ledger"
    assert not got.complete
    assert got.original_root_ledger is ledger


def test_original_root_ledger_uses_caller_cap_plus_one_saturation():
    got = _ledger(max_work=7)
    assert not got.admitted
    assert got.work_upper_bound == 8
