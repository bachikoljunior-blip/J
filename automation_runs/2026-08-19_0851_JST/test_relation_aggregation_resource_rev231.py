from math import comb
from types import SimpleNamespace

import theorem_local_certificate_relation_v1 as _entry
from babai_local_certificate_parameter_gate_v1 import BabaiLocalCertificateParameterGate
from permutation_group_schreier import identity, schreier_stabilizer_chain
from relation_aggregation_resource_envelope_v1 import (
    record_relation_aggregation_execution,
    relation_aggregation_resource_envelope,
)


def test_complete_multiplicity_and_round_charge_are_exact():
    count = comb(8, 5)
    envelope = relation_aggregation_resource_envelope(8, 5, count, 10**9)
    assert envelope.admitted and envelope.test_count == count
    done = record_relation_aggregation_execution(envelope, 3)
    assert done.complete and done.executed_rounds == 3
    assert done.charged_work_upper_bound == 3 * done.per_round_work_upper_bound


def test_bad_multiplicity_is_rejected():
    try:
        relation_aggregation_resource_envelope(8, 5, comb(8, 5) - 1, 10**9)
    except ValueError as exc:
        assert "multiplicity" in str(exc)
    else:
        raise AssertionError("incomplete relation multiplicity was accepted")


def test_theorem_aggregation_cap_rejects_before_refinement(monkeypatch):
    group = schreier_stabilizer_chain((identity(6),))
    blocks = tuple((i,) for i in range(6))

    gate = BabaiLocalCertificateParameterGate(
        "certified_local_certificate_parameter_window", 6, 6, 5,
        0.0, 5.0, True, "upstream fixture",
    )
    monkeypatch.setattr(_entry, "babai_local_certificate_parameter_gate", lambda *_: gate)
    monkeypatch.setattr(
        _entry,
        "local_certificate_beard",
        lambda _group, _blocks, _values, T, **_kwargs: SimpleNamespace(
            test_set=tuple(T), full=False,
            theorem_scale_recurrence_evidence=True,
            single_test_resource_envelope=None,
        ),
    )

    got = _entry.aggregate_beard_local_certificate_relation(
        group, blocks, (0,) * 6, test_size=5, max_test_sets=6,
        max_single_test_schreier_work=100,
        max_all_test_schreier_work=600,
        max_relation_aggregation_work=1,
    )
    assert got.status == "undetermined_relation_aggregation_work_cap"
    assert got.certificates_checked == 6 and got.local_certificates_complete
    assert got.all_test_resource_envelope.complete
    envelope = got.relation_aggregation_resource_envelope
    assert envelope is not None and not envelope.admitted
    assert envelope.executed_rounds == 0 and not envelope.complete
