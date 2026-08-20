from __future__ import annotations

import pytest

import quotient_factored_partial_string_intersection_v1 as _quotient
from giant_block_action_certificates import analyze_giant_block_action
from local_certificate_beard_v1 import local_certificate_beard
from local_certificate_preimage_resource_v1 import preimage_schreier_resource_envelope
from local_fullness_certificates import _alternating_test_generators
from permutation_group_schreier import schreier_stabilizer_chain
from quotient_factored_partial_string_intersection_v1 import (
    quotient_factored_partial_string_intersection,
)


def _symmetric_with_independent_pair(k):
    n = k + 2
    e = list(range(n))
    swap = e.copy(); swap[0], swap[1] = 1, 0
    cycle = e.copy()
    for i in range(k):
        cycle[i] = (i + 1) % k
    extra = e.copy(); extra[k], extra[k + 1] = k + 1, k
    return (
        schreier_stabilizer_chain((tuple(swap), tuple(cycle), tuple(extra))),
        tuple((i,) for i in range(k)),
    )


def test_one_budget_charges_every_executed_single_t_phase_once():
    group, blocks = _symmetric_with_independent_pair(5)
    got = local_certificate_beard(
        group,
        blocks,
        (0, 0, 1, 1, 2, 8, 9),
        tuple(range(5)),
        max_single_test_schreier_work=10**100,
    )
    assert got.status == "certified_nonfull_giant_obstruction"
    envelope = got.single_test_resource_envelope
    assert envelope is not None and envelope.admitted
    names = tuple(phase.name for phase in envelope.phases)
    assert names == (
        "prepared_preimage",
        "giant_action_audit",
        "affected_segment_quotient_kernel",
        "affected_segment_parent_reassembly",
        "giant_action_audit",
    )
    assert all(phase.admitted and phase.executed for phase in envelope.phases)
    assert envelope.charged_work == sum(
        phase.work_upper_bound for phase in envelope.phases
    )
    assert envelope.remaining_work == envelope.max_work - envelope.charged_work


def test_shared_budget_rejects_next_phase_before_execution():
    group, blocks = _symmetric_with_independent_pair(9)
    T = tuple(range(9))
    preimage = preimage_schreier_resource_envelope(
        group,
        9,
        len(_alternating_test_generators(9, T)),
        10**40,
    )
    assert preimage.admitted
    got = local_certificate_beard(
        group,
        blocks,
        (0,) * group.degree,
        T,
        max_single_test_schreier_work=preimage.work_upper_bound,
    )
    assert got.status == "undetermined_giant_action_schreier_work_cap"
    envelope = got.single_test_resource_envelope
    assert envelope is not None and not envelope.admitted
    assert envelope.charged_work == preimage.work_upper_bound
    assert envelope.remaining_work == 0
    assert envelope.phases[0].executed
    assert not envelope.phases[1].admitted and not envelope.phases[1].executed


def test_combined_segment_budget_reserves_reassembly_before_recursion(monkeypatch):
    group, blocks = _symmetric_with_independent_pair(5)
    giant = analyze_giant_block_action(group, blocks)
    quotient_only = quotient_factored_partial_string_intersection(
        group,
        blocks,
        (0, 0, 1, 1, 2, 8, 9),
        tuple(range(5)),
        max_quotient_leaves=1000,
        giant_certificate=giant,
        max_quotient_schreier_work=10**100,
    ).resource_envelope
    assert quotient_only is not None and quotient_only.admitted

    def forbidden(*_args, **_kwargs):
        raise AssertionError("combined cap must reject before quotient preparation")

    monkeypatch.setattr(_quotient, "prepare_block_action_preimage", forbidden)
    got = quotient_factored_partial_string_intersection(
        group,
        blocks,
        (0, 0, 1, 1, 2, 8, 9),
        tuple(range(5)),
        max_quotient_leaves=1000,
        giant_certificate=giant,
        max_combined_schreier_work=quotient_only.work_upper_bound,
    )
    assert got.status == "undetermined_reassembly_schreier_work_cap"
    assert got.resource_envelope is not None and got.resource_envelope.admitted
    assert got.reassembly_resource_envelope is not None
    assert not got.reassembly_resource_envelope.admitted
    assert got.quotient_nodes == got.quotient_leaves == 0


def test_single_budget_cannot_be_mixed_with_phase_budgets():
    group, blocks = _symmetric_with_independent_pair(5)
    with pytest.raises(ValueError, match="cannot be mixed"):
        local_certificate_beard(
            group,
            blocks,
            (0,) * group.degree,
            tuple(range(5)),
            max_single_test_schreier_work=10**20,
            max_preimage_schreier_work=10**20,
        )
