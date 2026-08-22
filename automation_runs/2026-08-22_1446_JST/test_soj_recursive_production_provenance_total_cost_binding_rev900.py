from dataclasses import replace
from types import SimpleNamespace

from soj_recursive_production_provenance_total_cost_binding_v1 import (
    REV700_STATUS,
    REV800_STATUS,
    certify_recursive_production_provenance_total_cost_binding,
    replay_recursive_production_provenance_total_cost_binding,
    _prefixed_digest,
)

BARE1 = "1" * 64
BARE2 = "2" * 64
BARE3 = "3" * 64
P4 = "sha256:" + "4" * 64
P5 = "sha256:" + "5" * 64
P6 = "sha256:" + "6" * 64
P7 = "sha256:" + "7" * 64
P8 = "sha256:" + "8" * 64
P9 = "sha256:" + "9" * 64
GIT = "a" * 40


def rev700_cert(
    *,
    result_status="exact_nonempty",
    accounting=P5,
    reduction=P6,
    production_identity=None,
):
    payload = {
        "schema_version": 1,
        "status": REV700_STATUS,
        "main_commit_sha": GIT,
        "caller_binding_identity": BARE1,
        "envelope_identity": BARE2,
        "main_provenance_identity": BARE3,
        "recursive_provenance_identity": P4,
        "result_status": result_status,
        "result_lift_digest": P7,
        "accounting_binding_digest": accounting,
        "reduction_identity": reduction,
        "child_result_identity": P8,
    }
    identity = production_identity or _prefixed_digest(payload)
    return SimpleNamespace(
        **payload,
        certified=True,
        exact_contract_join=True,
        production_provenance_identity=identity,
    )


def rev800_cert(
    *,
    outcome="nonempty",
    accounting=P5,
    reduction=P6,
    bound=256.0,
    charge=8.0,
    parent=70,
    child=8,
    coherence_identity=None,
):
    payload = {
        "schema_version": 1,
        "status": REV800_STATUS,
        "outcome_kind": outcome,
        "parent_action_degree": parent,
        "child_ground_size": child,
        "reduction_identity": reduction,
        "accounting_binding_digest": accounting,
        "construction_cost_binding_identity": P9,
        "construction_multiplicative_cost_bound": bound,
        "charged_log2_reduction_cost": charge,
    }
    identity = coherence_identity or _prefixed_digest(payload)
    return SimpleNamespace(
        **payload,
        certified=True,
        exact=True,
        complete=True,
        coherence_identity=identity,
    )


def certify(p=None, c=None, pr=True, cr=True):
    return certify_recursive_production_provenance_total_cost_binding(
        p or rev700_cert(),
        c or rev800_cert(),
        production_provenance_replay_verified=pr,
        total_cost_coherence_replay_verified=cr,
    )


def test_accepts_matching_provenance_and_exact_once_cost():
    out = certify()
    assert out.certified and out.exact_contract_binding
    assert out.accounting_binding_digest == P5
    assert out.reduction_identity == P6
    assert out.construction_multiplicative_cost_bound == 256.0
    assert out.charged_log2_reduction_cost == 8.0
    assert out.total_cost_binding_identity.startswith("sha256:")


def test_preserves_exact_empty_distinction():
    out = certify(
        p=rev700_cert(result_status="exact_empty"),
        c=rev800_cert(outcome="exact_empty"),
    )
    assert out.certified and out.result_status == "exact_empty"


def test_replay_roundtrip_and_drift():
    p = rev700_cert()
    c = rev800_cert()
    out = certify(p, c)
    assert replay_recursive_production_provenance_total_cost_binding(
        out,
        p,
        c,
        production_provenance_replay_verified=True,
        total_cost_coherence_replay_verified=True,
    )
    assert not replay_recursive_production_provenance_total_cost_binding(
        replace(out, reason="drift"),
        p,
        c,
        production_provenance_replay_verified=True,
        total_cost_coherence_replay_verified=True,
    )


def test_requires_both_independent_replay_gates():
    assert not certify(pr=False).certified
    assert not certify(cr=False).certified


def test_rejects_accounting_binding_mismatch():
    assert not certify(c=rev800_cert(accounting="sha256:" + "b" * 64)).certified


def test_rejects_reduction_identity_mismatch():
    assert not certify(c=rev800_cert(reduction="sha256:" + "c" * 64)).certified


def test_rejects_nonempty_exact_empty_semantic_mismatch():
    assert not certify(c=rev800_cert(outcome="exact_empty")).certified
    assert not certify(
        p=rev700_cert(result_status="exact_empty"), c=rev800_cert(outcome="nonempty")
    ).certified


def test_rejects_rev700_identity_drift():
    assert not certify(
        p=rev700_cert(production_identity="sha256:" + "d" * 64)
    ).certified


def test_rejects_rev800_identity_drift():
    assert not certify(
        c=rev800_cert(coherence_identity="sha256:" + "e" * 64)
    ).certified


def test_rejects_non_power_of_two_bound_even_if_rehashed():
    assert not certify(c=rev800_cert(bound=300.0, charge=8.0)).certified


def test_rejects_wrong_charge_even_if_rehashed():
    assert not certify(c=rev800_cert(bound=256.0, charge=7.0)).certified


def test_rejects_coercible_booleans():
    p = rev700_cert()
    p.certified = 1
    assert not certify(p=p).certified
    c = rev800_cert()
    c.exact = 1
    assert not certify(c=c).certified


def test_rejects_noncanonical_digest_encodings():
    p = rev700_cert()
    p.accounting_binding_digest = "abc"
    assert not certify(p=p).certified


def test_rejects_invalid_recursive_measure():
    assert not certify(c=rev800_cert(parent=8, child=8)).certified


def test_rejects_unknown_contract_status():
    p = rev700_cert()
    p.status = "something_else"
    assert not certify(p=p).certified


def test_total_binding_identity_is_deterministic_and_sensitive():
    a = certify()
    b = certify()
    assert a.total_cost_binding_identity == b.total_cost_binding_identity
    changed = certify(c=rev800_cert(bound=512.0, charge=9.0))
    assert changed.certified
    assert changed.total_cost_binding_identity != a.total_cost_binding_identity


if __name__ == "__main__":
    tests = [
        (name, value)
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for name, test in tests:
        test()
        print("PASS", name)
    print(f"{len(tests)}/{len(tests)} passed")
