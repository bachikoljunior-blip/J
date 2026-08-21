from dataclasses import replace
from itertools import combinations
from types import SimpleNamespace

import design_lemma_exact_twl_candidate_si_v1 as _candidate
from design_pipeline_admission_ledger_v1 import (
    design_pipeline_admission_ledger,
    record_design_pipeline_execution,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _ledger(cap=10**30):
    return design_pipeline_admission_ledger(
        original_root_degree=16,
        original_degree=8,
        vertex_count=8,
        arity=2,
        ambient_group_order=16,
        ambient_generator_count=3,
        target_values=(0, 0, 0, 0, 1, 1, 1, 1),
        max_group_order=8,
        max_work=cap,
    )


def _lifted(group):
    return tuple((g, False) for g in group.original_generators)


def test_ledger_reserves_every_phase_before_execution():
    got = _ledger()
    assert got.admitted
    assert got.witness_count_per_side_upper_bound == 8
    assert got.branch_count_upper_bound == 64
    assert got.branch_subgroup_generator_count_upper_bound >= 48
    assert got.child_generator_count_upper_bound >= got.ambient_group_order
    assert got.twl_work_upper_bound > 0
    assert got.materialization_work_upper_bound > 0
    assert got.tuple_transport_work_upper_bound > 0
    assert got.child_si_work_upper_bound == (
        got.branch_count_upper_bound * got.child_si_work_per_branch_upper_bound
    )
    assert got.union_generator_inputs_upper_bound > got.branch_count_upper_bound
    assert got.work_upper_bound == sum((
        got.twl_work_upper_bound,
        got.materialization_work_upper_bound,
        got.tuple_transport_work_upper_bound,
        got.child_si_work_upper_bound,
        got.union_work_upper_bound,
    ))


def test_shared_cap_rejects_before_first_twl_run(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("t-WL branch builder started before shared pipeline admission")

    monkeypatch.setattr(_candidate, "build_exact_twl_design_branch_plan", forbidden)
    group = schreier_stabilizer_chain((identity(8),))
    relation = tuple(0 for _ in combinations(range(8), 2))
    got = _candidate.exact_twl_design_candidate_string_isomorphism(
        group,
        ((identity(8), False),),
        8,
        2,
        relation,
        relation,
        (0,) * 8,
        (0,) * 8,
        root_n=16,
        max_design_pipeline_work=1,
    )
    assert got.status == "undetermined_exact_twl_design_pipeline_preflight"
    assert got.branch_plan is None
    assert got.pipeline_admission_ledger is not None
    assert got.pipeline_admission_ledger.work_upper_bound == 2


def test_shared_ledger_uses_only_caller_cap_plus_one_saturation():
    got = design_pipeline_admission_ledger(
        original_root_degree=4,
        original_degree=4,
        vertex_count=4,
        arity=2,
        ambient_group_order=1,
        ambient_generator_count=1,
        target_values=(0,) * 4,
        max_group_order=16,
        max_work=7,
    )
    assert not got.admitted
    assert got.work_upper_bound == 8


def test_recording_cannot_overrun_any_reserved_phase():
    ledger = _ledger()
    recorded = record_design_pipeline_execution(
        ledger,
        twl_work=ledger.twl_work_upper_bound,
        materialization_work=ledger.materialization_work_upper_bound,
        tuple_transport_work=ledger.tuple_transport_work_upper_bound,
        child_si_work=ledger.child_si_work_upper_bound,
        union_work=ledger.union_work_upper_bound,
        complete=True,
    )
    assert recorded.complete
    assert recorded.charged_work == ledger.work_upper_bound

    try:
        record_design_pipeline_execution(
            ledger,
            twl_work=ledger.twl_work_upper_bound + 1,
            materialization_work=0,
            tuple_transport_work=0,
            child_si_work=0,
            union_work=0,
            complete=False,
        )
    except ValueError as exc:
        assert "phase exceeds" in str(exc)
    else:
        raise AssertionError("a phase overrun was accepted")


def test_root_lift_gate_remains_fail_closed():
    got = design_pipeline_admission_ledger(
        original_root_degree=8,
        original_degree=9,
        vertex_count=8,
        arity=2,
        ambient_group_order=2,
        ambient_generator_count=1,
        target_values=(0,) * 9,
        max_work=10**30,
    )
    assert not got.root_lift_certified
    assert not got.admitted
    assert got.status == "design_pipeline_original_root_lift_unavailable"


def test_production_phase_caps_are_clipped_to_shared_slices(monkeypatch):
    pipeline = replace(
        _ledger(10**40),
        twl_work_upper_bound=101,
        materialization_work_upper_bound=102,
        tuple_transport_work_upper_bound=103,
        child_si_work_upper_bound=104,
        union_work_upper_bound=105,
        work_upper_bound=515,
        max_work=515,
        admitted=True,
    )
    captured = {}
    monkeypatch.setattr(
        _candidate,
        "design_pipeline_admission_ledger",
        lambda **_kwargs: pipeline,
    )

    twl_resource = SimpleNamespace(
        admitted=True,
        reason="ok",
        charged_paired_work=1,
        executed_source_runs=1,
        executed_target_runs=1,
        executed_source_work=1,
        executed_target_work=1,
    )

    def fake_twl_resource(_root, _v, _k, max_work):
        captured["twl_preflight"] = max_work
        return twl_resource

    monkeypatch.setattr(
        _candidate, "paired_correlated_twl_resource_envelope", fake_twl_resource,
    )
    monkeypatch.setattr(
        _candidate,
        "record_paired_correlated_twl_execution",
        lambda envelope, **_kwargs: envelope,
    )

    family = SimpleNamespace(
        states_checked=1,
        work_units=1,
        exact=True,
        theorem_parameter_gate=True,
        symmetry_defect_gate=True,
        status="certified_exact_twl_design_witness_family",
    )
    materialization = SimpleNamespace(
        complete=True,
        materialized_branch_count=1,
        charged_work_upper_bound=1,
    )
    plan = SimpleNamespace(
        source_family=family,
        target_family=family,
        exact_empty=False,
        complete=True,
        status="certified_complete_design_branch_plan",
        individualization_length=0,
        branch_count=1,
        reason="ok",
        materialization_resource_envelope=materialization,
    )

    def fake_plan(*_args, **kwargs):
        captured["twl_engine"] = kwargs["max_work_units"]
        captured["materialization"] = kwargs["max_materialization_work"]
        return plan

    monkeypatch.setattr(_candidate, "build_exact_twl_design_branch_plan", fake_plan)
    monkeypatch.setattr(
        _candidate,
        "certify_design_branch_quasipoly_cost",
        lambda *_args, **_kwargs: SimpleNamespace(certified=True, reason="ok"),
    )

    transport_resource = SimpleNamespace(admitted=True, reason="ok")

    def fake_transport_resource(*args):
        captured["transport"] = args[-1]
        return transport_resource

    monkeypatch.setattr(
        _candidate, "design_tuple_transport_resource_envelope", fake_transport_resource,
    )
    executed_transport_resource = SimpleNamespace(
        admitted=True,
        reason="ok",
        complete=True,
        executed_branches=1,
        executed_orbit_states=1,
        executed_action_steps=1,
        charged_work_upper_bound=1,
    )
    monkeypatch.setattr(
        _candidate,
        "record_design_tuple_transport_execution",
        lambda _envelope, **_kwargs: executed_transport_resource,
    )
    transport = SimpleNamespace(
        complete=True,
        status="certified_complete_design_tuple_transport_cover",
        exact_empty=False,
        reason="ok",
        executed_branch_count=1,
        total_orbit_states=1,
        total_action_steps=1,
    )
    monkeypatch.setattr(
        _candidate,
        "transport_complete_design_tuple_branches",
        lambda *_args, **_kwargs: transport,
    )

    full = SimpleNamespace(
        exact=False,
        reason="sentinel after cap capture",
        child_preflight=None,
        union_resource_envelope=None,
    )

    def fake_full(*_args, **kwargs):
        captured["children"] = kwargs["max_design_full_string_child_work"]
        captured["union"] = kwargs["max_design_union_reconstruction_work"]
        return full

    monkeypatch.setattr(
        _candidate, "solve_design_tuple_transport_full_string", fake_full,
    )
    monkeypatch.setattr(
        _candidate,
        "record_design_pipeline_execution",
        lambda _ledger, **_kwargs: pipeline,
    )

    group = schreier_stabilizer_chain((identity(8),))
    relation = tuple(0 for _ in combinations(range(8), 2))
    got = _candidate.exact_twl_design_candidate_string_isomorphism(
        group,
        _lifted(group),
        8,
        2,
        relation,
        relation,
        (0,) * 8,
        (0,) * 8,
        root_n=16,
        max_twl_work_units=10**9,
        max_paired_twl_work_units=10**9,
        max_design_branch_materialization_work=10**9,
        max_design_transport_work=10**9,
        max_design_full_string_child_work=10**9,
        max_design_union_reconstruction_work=10**9,
        max_design_pipeline_work=10**9,
    )
    assert got.status == "undetermined_exact_twl_design_full_string"
    assert captured == {
        "twl_preflight": 101,
        "twl_engine": 101,
        "materialization": 102,
        "transport": 103,
        "children": 104,
        "union": 105,
    }


def test_cycle11_records_all_five_pipeline_phases_exactly_once():
    v, k = 11, 2
    edges = {tuple(sorted((i, (i + 1) % v))) for i in range(v)}
    relation = tuple(int(S in edges) for S in combinations(range(v), k))
    cycle = tuple((i + 1) % v for i in range(v))
    group = schreier_stabilizer_chain((cycle,))
    values = tuple(0 for _ in range(v))

    got = _candidate.exact_twl_design_candidate_string_isomorphism(
        group,
        _lifted(group),
        v,
        k,
        relation,
        relation,
        values,
        values,
        root_n=64,
        max_states=100,
        max_tuple_states=1000,
        max_twl_rounds=32,
        max_twl_work_units=60_000_000,
        max_partition_states=64,
        max_group_order=16,
        max_design_pipeline_work=10**40,
    )
    assert got.exact and got.complete
    ledger = got.pipeline_admission_ledger
    assert ledger is not None and ledger.admitted and ledger.complete
    assert ledger.phases_recorded == (
        "twl", "materialization", "transport", "child", "union",
    )
    assert ledger.branch_count_upper_bound == 121
    assert ledger.materialized_branch_count == 1
    assert ledger.transported_branch_count == 1
    assert ledger.executed_child_count == 1
    assert ledger.union_generator_count > 0
    assert ledger.charged_work <= ledger.work_upper_bound
