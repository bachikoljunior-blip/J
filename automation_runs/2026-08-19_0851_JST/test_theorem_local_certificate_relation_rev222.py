from __future__ import annotations

import theorem_local_certificate_relation_v1 as _entry
import aggregate_local_certificate_relation as _global_entry
from permutation_group_schreier import schreier_stabilizer_chain
from theorem_local_certificate_relation_v1 import (
    aggregate_beard_local_certificate_relation,
)


def _symmetric_with_independent_pair(k):
    n = k + 2
    identity = list(range(n))
    swap01 = identity.copy()
    swap01[0], swap01[1] = 1, 0
    cycle = identity.copy()
    for i in range(k):
        cycle[i] = (i + 1) % k
    extra = identity.copy()
    extra[k], extra[k + 1] = k + 1, k
    return (
        schreier_stabilizer_chain((tuple(swap01), tuple(cycle), tuple(extra))),
        tuple((i,) for i in range(k)),
    )


def test_strict_theorem_window_fails_before_local_execution(monkeypatch):
    group, blocks = _symmetric_with_independent_pair(9)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("local certificate must not run outside theorem window")

    monkeypatch.setattr(_entry, "local_certificate_beard", forbidden)
    got = aggregate_beard_local_certificate_relation(
        group, blocks, (0,) * group.degree, test_size=9
    )
    assert got.status == "undetermined_theorem_parameter_window"
    assert got.certificates_checked == 0
    assert not got.parameter_gate.certified
    assert not got.exact and got.aggregate is None


def test_testset_cap_fails_before_local_execution(monkeypatch):
    group, blocks = _symmetric_with_independent_pair(9)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("local certificate must not run beyond relation cap")

    monkeypatch.setattr(_entry, "local_certificate_beard", forbidden)
    got = aggregate_beard_local_certificate_relation(
        group,
        blocks,
        (0,) * group.degree,
        test_size=5,
        max_test_sets=100,
        require_theorem_scale=False,
    )
    assert got.status == "undetermined_testset_limit"
    assert got.test_count == 126 and got.certificates_checked == 0
    assert not got.exact and got.aggregate is None


def test_bounded_s9_fullness_uses_actual_beard_not_global_stabilizer():
    group, blocks = _symmetric_with_independent_pair(9)
    got = aggregate_beard_local_certificate_relation(
        group,
        blocks,
        (0,) * group.degree,
        test_size=9,
        require_theorem_scale=False,
    )
    assert got.status == "bounded_exact_beard_relation_without_theorem_scale"
    assert got.exact and got.local_certificates_complete
    assert not got.theorem_scale_complete
    assert got.certificates_checked == got.test_count == got.full_count == 1
    assert got.nonfull_count == got.undetermined_count == 0
    assert got.certificates[0].status == "certified_full_by_stable_beard"
    assert got.aggregate is not None
    assert got.aggregate.relation == ((tuple(range(9)), True),)


def test_bounded_s5_nonfullness_is_an_exact_false_relation_entry():
    group, blocks = _symmetric_with_independent_pair(5)
    values = (0, 0, 1, 1, 2, 8, 9)
    got = aggregate_beard_local_certificate_relation(
        group,
        blocks,
        values,
        test_size=5,
        require_theorem_scale=False,
    )
    assert got.exact and got.local_certificates_complete
    assert got.full_count == 0 and got.nonfull_count == 1
    assert got.certificates[0].status == "certified_nonfull_giant_obstruction"
    assert got.aggregate is not None
    assert got.aggregate.relation == ((tuple(range(5)), False),)


def test_bounded_beard_relation_never_calls_global_string_stabilizer(monkeypatch):
    group, blocks = _symmetric_with_independent_pair(5)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("global string stabilizer is forbidden on beard path")

    monkeypatch.setattr(_global_entry, "exact_string_stabilizer", forbidden)
    got = aggregate_beard_local_certificate_relation(
        group,
        blocks,
        (0, 0, 1, 1, 2, 8, 9),
        test_size=5,
        require_theorem_scale=False,
    )
    assert got.exact and got.aggregate is not None


def test_unknown_local_certificate_withholds_complete_relation():
    group, blocks = _symmetric_with_independent_pair(5)
    got = aggregate_beard_local_certificate_relation(
        group,
        blocks,
        (0,) * group.degree,
        test_size=5,
        require_theorem_scale=False,
    )
    assert got.status == "undetermined_local_certificate"
    assert got.certificates_checked == 1
    assert got.certificates[0].full is None
    assert not got.exact and not got.local_certificates_complete
    assert got.aggregate is None
