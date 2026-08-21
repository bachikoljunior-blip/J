from itertools import combinations

import design_lemma_exact_twl_candidate_si_v1 as _candidate
from correlated_twl_resource_envelope_v1 import (
    paired_correlated_twl_resource_envelope,
    record_paired_correlated_twl_execution,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def test_complete_paired_upper_bound_counts_every_primitive():
    got = paired_correlated_twl_resource_envelope(8, 8, 2, 2_000_000)
    assert got.root_lift_certified and got.admitted
    assert got.tuple_states_per_run == 64
    assert got.individualization_runs_per_side_upper_bound == 9
    assert got.stabilization_rounds_per_run_upper_bound == 64
    assert got.initial_work_per_run_upper_bound == 64
    assert got.replacement_work_per_round_upper_bound == 64 * 8 * 2
    assert got.work_per_run_upper_bound == 64 + 64 * 64 * 8 * 2
    assert got.work_per_side_upper_bound == 9 * got.work_per_run_upper_bound
    assert got.paired_work_upper_bound == 2 * got.work_per_side_upper_bound


def test_original_root_arity_and_finite_budget_reject_before_execution(monkeypatch):
    arity = paired_correlated_twl_resource_envelope(8, 8, 4, 10**30)
    assert not arity.root_lift_certified and not arity.admitted

    def forbidden(*_args, **_kwargs):
        raise AssertionError("t-WL execution started before paired preflight admission")

    monkeypatch.setattr(_candidate, "build_exact_twl_design_branch_plan", forbidden)
    group = schreier_stabilizer_chain((identity(11),))
    relation = tuple(0 for _ in combinations(range(11), 2))
    got = _candidate.exact_twl_design_candidate_string_isomorphism(
        group, ((identity(11), False),), 11, 2, relation, relation,
        (0,) * 11, (0,) * 11, root_n=32,
        max_paired_twl_work_units=1,
    )
    assert got.status == "undetermined_exact_twl_resource_preflight"
    assert got.branch_plan is None
    assert got.twl_resource_envelope is not None
    assert not got.twl_resource_envelope.admitted
    assert got.twl_resource_envelope.executed_source_runs == 0


def test_actual_source_target_execution_is_charged_once():
    v, k = 11, 2
    edges = {tuple(sorted((i, (i + 1) % v))) for i in range(v)}
    relation = tuple(int(S in edges) for S in combinations(range(v), k))
    cycle = tuple((i + 1) % v for i in range(v))
    group = schreier_stabilizer_chain((cycle,))
    got = _candidate.exact_twl_design_candidate_string_isomorphism(
        group, ((cycle, False),), v, k, relation, relation,
        (0,) * v, (0,) * v, root_n=32,
        max_states=100, max_tuple_states=200, max_twl_rounds=16,
        max_twl_work_units=2_000_000,
        max_paired_twl_work_units=10_000_000,
        max_partition_states=32, max_group_order=16,
    )
    assert got.exact and got.complete
    envelope = got.twl_resource_envelope
    assert envelope is not None and envelope.admitted and envelope.complete
    assert got.branch_plan is not None
    source = got.branch_plan.source_family
    target = got.branch_plan.target_family
    assert envelope.executed_source_runs == source.states_checked
    assert envelope.executed_target_runs == target.states_checked
    assert envelope.charged_paired_work == source.work_units + target.work_units
    assert envelope.charged_paired_work <= envelope.paired_work_upper_bound


def test_execution_record_cannot_exceed_reserved_multiplicity():
    envelope = paired_correlated_twl_resource_envelope(8, 8, 2, 2_000_000)
    try:
        record_paired_correlated_twl_execution(
            envelope,
            executed_source_runs=10,
            executed_target_runs=0,
            executed_source_work=0,
            executed_target_work=0,
            complete=False,
        )
    except ValueError as exc:
        assert "run count" in str(exc)
    else:
        raise AssertionError("an execution above the reserved multiplicity was accepted")
