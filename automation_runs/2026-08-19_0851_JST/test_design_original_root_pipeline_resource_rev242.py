from dataclasses import replace
from itertools import combinations

import pytest
import design_lemma_exact_twl_candidate_si_v1 as _candidate

from design_original_root_pipeline_resource_v1 import (
    design_original_root_pipeline_resource_envelope,
    record_design_original_root_pipeline_phase,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _group():
    return schreier_stabilizer_chain(((1, 0, 2),))


def test_pipeline_preflight_rejects_before_any_phase_and_preserves_full_suffix():
    got = design_original_root_pipeline_resource_envelope(
        _group(), original_root_degree=8, vertex_count=3, arity=2,
        target_values=(0, 1, 0), group_order_poly_power=2,
        max_group_order=256, max_work=1,
    )
    assert got.status == "design_original_root_pipeline_work_cap_exceeded"
    assert not got.admitted
    assert got.completed_phases == ()
    assert got.unexecuted_suffix == ("twl", "materialization", "transport", "children", "union")


def test_pipeline_uses_complete_input_independent_branch_cover():
    got = design_original_root_pipeline_resource_envelope(
        _group(), original_root_degree=8, vertex_count=3, arity=2,
        target_values=(0, 1, 0), group_order_poly_power=2,
        max_group_order=256, max_work=10**80,
    )
    assert got.admitted
    assert got.branch_count_upper_bound == 16  # (1 + 3)^2
    assert len(got.phase_work_upper_bounds) == 5
    assert got.work_upper_bound == sum(got.phase_work_upper_bounds)


def test_ledger_is_ordered_single_charge_and_retains_suffix():
    got = design_original_root_pipeline_resource_envelope(
        _group(), original_root_degree=8, vertex_count=3, arity=2,
        target_values=(0, 1, 0), group_order_poly_power=2,
        max_group_order=256, max_work=10**80,
    )
    got = record_design_original_root_pipeline_phase(got, "twl", charged_work=7)
    assert got.completed_phases == ("twl",)
    assert got.unexecuted_suffix[0] == "materialization"
    with pytest.raises(ValueError):
        record_design_original_root_pipeline_phase(got, "transport", charged_work=0)
    with pytest.raises(ValueError):
        record_design_original_root_pipeline_phase(
            got, "materialization", charged_work=got.phase_work_upper_bounds[1] + 1,
        )


def test_ledger_can_complete_all_five_phases():
    got = design_original_root_pipeline_resource_envelope(
        _group(), original_root_degree=8, vertex_count=3, arity=2,
        target_values=(0, 1, 0), group_order_poly_power=2,
        max_group_order=256, max_work=10**80,
    )
    for phase in ("twl", "materialization", "transport", "children", "union"):
        got = record_design_original_root_pipeline_phase(got, phase, charged_work=0)
    assert got.complete
    assert got.unexecuted_suffix == ()


def test_phase_bound_tampering_cannot_be_charged():
    got = design_original_root_pipeline_resource_envelope(
        _group(), original_root_degree=8, vertex_count=3, arity=2,
        target_values=(0, 1, 0), group_order_poly_power=2,
        max_group_order=256, max_work=10**80,
    )
    forged = replace(got, admitted=False)
    with pytest.raises(ValueError):
        record_design_original_root_pipeline_phase(forged, "twl", charged_work=0)


def test_candidate_rejects_global_cap_before_first_twl_run(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("t-WL started before the complete pipeline reservation")

    monkeypatch.setattr(_candidate, "build_exact_twl_design_branch_plan", forbidden)
    group = _group()
    got = _candidate.exact_twl_design_candidate_string_isomorphism(
        group, tuple((g, False) for g in group.original_generators),
        3, 2, (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
        root_n=8, max_design_pipeline_work=1,
    )
    assert got.status == "undetermined_design_original_root_pipeline_preflight"
    assert got.pipeline_resource_envelope.unexecuted_suffix[0] == "twl"


def test_exact_candidate_records_one_shared_five_phase_ledger():
    v, k = 11, 2
    edges = {tuple(sorted((i, (i + 1) % v))) for i in range(v)}
    relation = tuple(int(S in edges) for S in combinations(range(v), k))
    cycle = tuple((i + 1) % v for i in range(v))
    group = schreier_stabilizer_chain((cycle,))
    source = tuple(range(v))
    got = _candidate.exact_twl_design_candidate_string_isomorphism(
        group, tuple((g, False) for g in group.original_generators),
        v, k, relation, relation, source, source,
        root_n=64, max_states=100, max_tuple_states=1000,
        max_twl_rounds=32, max_twl_work_units=60_000_000,
        max_partition_states=64, max_group_order=16,
    )
    assert got.exact and got.complete and got.full_string_result.coset.contains(identity(v))
    ledger = got.pipeline_resource_envelope
    assert ledger.admitted and ledger.complete
    assert ledger.completed_phases == ("twl", "materialization", "transport", "children", "union")
    assert ledger.unexecuted_suffix == ()
    assert ledger.charged_work <= ledger.work_upper_bound <= ledger.max_work
