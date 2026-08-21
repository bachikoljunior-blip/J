from types import SimpleNamespace

import colored_subset_exact_twl_branch_plan_v1 as _plan
from design_branch_materialization_resource_v1 import (
    design_branch_materialization_resource_envelope,
    record_design_branch_materialization,
)


def test_arbitrary_precision_cartesian_and_copy_work_are_reserved():
    got = design_branch_materialization_resource_envelope(32, 11, 2, 7, 9, 10**12)
    assert got.admitted and got.branch_count == 63
    assert got.witness_snapshot_work_upper_bound == 16 * 3
    assert got.work_per_branch_upper_bound == 5
    assert got.work_upper_bound == 48 + 63 * 5


def test_runtime_branch_cap_is_not_theorem_budget():
    exact = design_branch_materialization_resource_envelope(32, 11, 2, 7, 9, 10**12)
    rejected = design_branch_materialization_resource_envelope(
        32, 11, 2, 7, 9, exact.work_upper_bound - 1,
    )
    assert not rejected.admitted
    assert rejected.status == "design_branch_materialization_work_cap_exceeded"


def test_complete_record_requires_every_reserved_pair():
    envelope = design_branch_materialization_resource_envelope(32, 11, 2, 2, 3, 10**6)
    done = record_design_branch_materialization(
        envelope, materialized_branch_count=6, complete=True,
    )
    assert done.complete and done.charged_work_upper_bound == done.work_upper_bound
    try:
        record_design_branch_materialization(
            envelope, materialized_branch_count=5, complete=True,
        )
    except ValueError as exc:
        assert "entire Cartesian cover" in str(exc)
    else:
        raise AssertionError("a partial Cartesian cover was marked complete")


def test_rejection_occurs_before_any_witness_tuple_is_read(monkeypatch):
    class ForbiddenOutcome:
        @property
        def individualized(self):
            raise AssertionError("branch tuple was touched before materialization admission")

    family = SimpleNamespace(
        local_log2_cost_bound=1.0,
        minimal_individualization_length=2,
        witness_outcomes=(ForbiddenOutcome(), ForbiddenOutcome()),
    )
    paired = SimpleNamespace(
        source=family,
        target=family,
        exact_empty=False,
        complete=True,
        status="certified_paired_exact_twl_design_family",
        reason="fixture",
    )
    monkeypatch.setattr(
        _plan, "paired_exact_twl_design_witness_families", lambda *_a, **_k: paired,
    )
    got = _plan.build_exact_twl_design_branch_plan(
        11, 2, (), (), original_root_degree=32, max_materialization_work=1,
    )
    assert got.status == "undetermined_exact_twl_design_branch_materialization_preflight"
    assert got.branches == () and got.branch_count == 4
    assert got.materialization_resource_envelope is not None
    assert not got.materialization_resource_envelope.admitted
