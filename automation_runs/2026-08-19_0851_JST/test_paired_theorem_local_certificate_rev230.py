from dataclasses import replace
from itertools import combinations
from types import SimpleNamespace

from aggregate_local_certificate_relation import _aggregate_boolean_relation
from all_test_resource_envelope_v1 import (
    all_test_resource_envelope,
    record_all_test_execution,
)
from babai_local_certificate_parameter_gate_v1 import BabaiLocalCertificateParameterGate
from paired_theorem_local_certificate_relation_v1 import (
    pair_theorem_local_certificate_relations,
)
from theorem_local_certificate_relation_v1 import TheoremLocalCertificateRelation


def _artifact(bits):
    m, t = 6, 5
    coordinates = tuple(combinations(range(m), t))
    relation = tuple(zip(coordinates, tuple(bits)))
    aggregate = _aggregate_boolean_relation(
        m, t, relation, max_class_fraction=0.9, reason="rev230 fixture",
    )
    gate = BabaiLocalCertificateParameterGate(
        "certified_local_certificate_parameter_window", 1, m, t,
        0.0, float(t), True, "fixture of an upstream-certified immutable gate",
    )
    reserved = all_test_resource_envelope(len(coordinates), 100, 600)
    complete = record_all_test_execution(
        reserved, len(coordinates), 300, complete=True,
    )
    certificates = tuple(SimpleNamespace(test_set=T) for T in coordinates)
    return TheoremLocalCertificateRelation(
        "certified_theorem_local_certificate_relation", m, t,
        len(coordinates), len(coordinates), sum(bits), len(bits) - sum(bits),
        0, gate, certificates, aggregate, True, True, True,
        "complete fixture", complete,
    )


def test_complete_pair_is_released_only_as_relation_si_input():
    source = _artifact((True, False, False, True, False, True))
    target = _artifact((False, True, True, False, True, False))
    got = pair_theorem_local_certificate_relations(source, target)
    assert got.status == "certified_paired_relation_si_input"
    assert got.canonical_test_order_certified
    assert got.necessary_palette_invariants_match
    assert got.ready_for_relation_si and not got.exact_empty


def test_palette_mismatch_is_exact_necessary_invariant_failure():
    source = _artifact((True, False, False, True, False, True))
    target = _artifact((False, False, False, False, True, False))
    got = pair_theorem_local_certificate_relations(source, target)
    assert got.status == "paired_relation_palette_mismatch_exact_empty"
    assert got.exact_empty and not got.ready_for_relation_si


def test_incomplete_or_reordered_evidence_stays_fail_closed():
    source = _artifact((True, False, False, True, False, True))
    target = _artifact((False, True, True, False, True, False))
    target = replace(target, certificates=tuple(reversed(target.certificates)))
    got = pair_theorem_local_certificate_relations(source, target)
    assert got.status == "undetermined_incomplete_paired_evidence"
    assert not got.canonical_test_order_certified
    assert not got.exact_empty and not got.ready_for_relation_si
