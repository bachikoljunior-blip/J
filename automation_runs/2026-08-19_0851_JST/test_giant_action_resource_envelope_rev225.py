from __future__ import annotations

import local_certificate_beard_v1 as _beard
import unaffected_stabilizer_reduction_v1 as _stable
from giant_action_resource_envelope_v1 import giant_action_resource_envelope
from local_certificate_beard_v1 import local_certificate_beard
from permutation_group_schreier import schreier_stabilizer_chain


def _symmetric_with_independent_pair(k):
    n = k + 2
    e = list(range(n))
    swap = e.copy()
    swap[0], swap[1] = 1, 0
    cycle = e.copy()
    for i in range(k):
        cycle[i] = (i + 1) % k
    extra = e.copy()
    extra[k], extra[k + 1] = k + 1, k
    return schreier_stabilizer_chain((tuple(swap), tuple(cycle), tuple(extra))), tuple((i,) for i in range(k))


def test_structural_cap_rejects_before_first_giant_audit(monkeypatch):
    group, blocks = _symmetric_with_independent_pair(9)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("giant audit must not start beyond cap")

    monkeypatch.setattr(_beard, "analyze_giant_block_action", forbidden)
    got = local_certificate_beard(
        group, blocks, (0,) * group.degree, tuple(range(9)),
        max_giant_action_schreier_work=1,
    )
    assert got.status == "undetermined_giant_action_schreier_work_cap"
    assert got.full is None and len(got.giant_action_resource_envelopes) == 1
    assert not got.giant_action_resource_envelopes[0].admitted


def test_admitted_audits_are_cumulative_and_final_reduction_reuses_certificate(monkeypatch):
    group, blocks = _symmetric_with_independent_pair(9)

    def duplicate_forbidden(*_args, **_kwargs):
        raise AssertionError("final reduction must reuse the already executed after-layer certificate")

    monkeypatch.setattr(_stable, "analyze_giant_block_action", duplicate_forbidden)
    monkeypatch.setattr(_stable, "pointwise_stabilizer_chain", duplicate_forbidden)
    got = local_certificate_beard(
        group, blocks, (0,) * group.degree, tuple(range(9)),
        max_giant_action_schreier_work=10**40,
    )
    assert got.status == "certified_full_by_stable_beard"
    assert got.full is True and len(got.giant_action_resource_envelopes) == 2
    assert all(x.admitted for x in got.giant_action_resource_envelopes)


def test_bound_saturates_at_remaining_cap_plus_one():
    group, _ = _symmetric_with_independent_pair(9)
    small = giant_action_resource_envelope(group, 9, 1000)
    large = giant_action_resource_envelope(group, 9, 10**40)
    assert small.work_upper_bound == 1001 and not small.admitted
    assert large.work_upper_bound > small.work_upper_bound and large.admitted


def test_exactly_exhausted_budget_fails_closed_before_next_audit():
    group, blocks = _symmetric_with_independent_pair(9)
    first = giant_action_resource_envelope(group, 9, 10**40)
    got = local_certificate_beard(
        group, blocks, (0,) * group.degree, tuple(range(9)),
        max_giant_action_schreier_work=first.work_upper_bound,
    )
    assert got.status == "undetermined_giant_action_schreier_work_cap"
    assert len(got.giant_action_resource_envelopes) == 2
    assert got.giant_action_resource_envelopes[0].admitted
    assert not got.giant_action_resource_envelopes[1].admitted
