from itertools import combinations

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
