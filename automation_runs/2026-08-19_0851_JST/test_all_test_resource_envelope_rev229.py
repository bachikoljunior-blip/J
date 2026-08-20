from __future__ import annotations

from math import comb

import theorem_local_certificate_relation_v1 as _entry
from all_test_resource_envelope_v1 import (
    all_test_resource_envelope,
    record_all_test_execution,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain
from theorem_local_certificate_relation_v1 import (
    aggregate_beard_local_certificate_relation,
)


def test_all_test_bound_uses_exact_multiplicity_and_execution_suffix():
    envelope = all_test_resource_envelope(126, 4000, 504000)
    assert envelope.admitted and envelope.work_upper_bound == 126 * 4000
    partial = record_all_test_execution(
        envelope, 7, 12345, complete=False,
    )
    assert partial.executed_test_count == 7
    assert partial.unexecuted_test_count == 119
    assert partial.charged_work == 12345 and not partial.complete


def test_all_test_cap_rejects_before_first_theorem_certificate(monkeypatch):
    n = 90
    group = schreier_stabilizer_chain((identity(n),))
    blocks = tuple((i,) for i in range(n))
    total = comb(n, 9)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("all-test multiplicity must be admitted before T execution")

    monkeypatch.setattr(_entry, "local_certificate_beard", forbidden)
    got = aggregate_beard_local_certificate_relation(
        group,
        blocks,
        (0,) * n,
        test_size=9,
        max_test_sets=total,
        max_single_test_schreier_work=4000,
        max_all_test_schreier_work=total * 4000 - 1,
    )
    assert got.status == "undetermined_all_test_work_cap"
    assert got.certificates_checked == 0
    envelope = got.all_test_resource_envelope
    assert envelope is not None and not envelope.admitted
    assert envelope.test_count == total
    assert envelope.executed_test_count == 0
    assert envelope.unexecuted_test_count == total


def test_complete_execution_record_requires_every_reserved_test():
    envelope = all_test_resource_envelope(3, 100, 300)
    try:
        record_all_test_execution(envelope, 2, 150, complete=True)
    except ValueError as exc:
        assert "omitted" in str(exc)
    else:
        raise AssertionError("incomplete schedule was accepted as complete")
