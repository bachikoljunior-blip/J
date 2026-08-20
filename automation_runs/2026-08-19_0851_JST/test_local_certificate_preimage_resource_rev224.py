from __future__ import annotations

import local_certificate_beard_v1 as _beard
from local_certificate_beard_v1 import local_certificate_beard
from local_certificate_preimage_resource_v1 import preimage_schreier_resource_envelope
from local_fullness_certificates import _alternating_test_generators
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


def test_cap_rejects_before_any_preimage_execution(monkeypatch):
    group, blocks = _symmetric_with_independent_pair(9)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("preimage execution must not start beyond cap")

    monkeypatch.setattr(_beard, "_test_alternating_preimage", forbidden)
    got = local_certificate_beard(
        group, blocks, (0,) * group.degree, tuple(range(9)),
        max_preimage_schreier_work=1,
    )
    assert got.status == "undetermined_preimage_schreier_work_cap"
    assert got.full is None and not got.theorem_scale_recurrence_evidence
    assert got.preimage_resource_envelope is not None
    assert not got.preimage_resource_envelope.admitted


def test_admitted_bound_preserves_exact_bounded_result():
    group, blocks = _symmetric_with_independent_pair(9)
    envelope = preimage_schreier_resource_envelope(
        group, 9, len(_alternating_test_generators(9, tuple(range(9)))), 10**30
    )
    assert envelope.admitted
    got = local_certificate_beard(
        group, blocks, (0,) * group.degree, tuple(range(9)),
        max_preimage_schreier_work=10**30,
    )
    assert got.status == "certified_full_by_stable_beard"
    assert got.full is True and got.preimage_resource_envelope == envelope


def test_bound_is_monotone_in_cap_and_saturates_at_cap_plus_one():
    group, _ = _symmetric_with_independent_pair(9)
    small = preimage_schreier_resource_envelope(group, 9, 2, 1000)
    large = preimage_schreier_resource_envelope(group, 9, 2, 10**30)
    assert small.work_upper_bound == 1001 and not small.admitted
    assert large.work_upper_bound > small.work_upper_bound and large.admitted
