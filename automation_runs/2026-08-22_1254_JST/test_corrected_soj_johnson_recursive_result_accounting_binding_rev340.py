from __future__ import annotations

import copy
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from corrected_soj_johnson_recursive_result_accounting_binding_v1 import (  # noqa: E402
    HANDOFF_STATUS,
    LIFT_EMPTY_STATUS,
    LIFT_NONEMPTY_STATUS,
    certify_johnson_recursive_result_accounting_binding,
    replay_johnson_recursive_result_accounting_binding,
)

D0 = "sha256:" + "0" * 64
D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
D3 = "sha256:" + "3" * 64


def ns(**kwargs):
    return SimpleNamespace(**kwargs)


def make_handoff():
    child_node = ns(n=10, m=5, operation_kind="terminal", canonical=True, cost_certified=True)
    edge = ns(node=child_node, multiplicity=1)
    accounting_root = ns(
        n=10,
        m=10,
        operation_kind="aux_shrink",
        canonical=True,
        cost_certified=True,
        children=(edge,),
    )
    reduction = ns(
        canonical=True,
        exact=True,
        progress_certified=True,
        solution_transport_certified=True,
        ambient_membership_transport_certified=True,
        complement_ambiguity_handled=True,
        source_action_degree=10,
        johnson_ground_size=5,
        child_ground_size=5,
        reduction_identity=D0,
    )
    return ns(
        status=HANDOFF_STATUS,
        certified=True,
        reduction=reduction,
        accounting_root=accounting_root,
        validation=ns(certified=True),
        charged_log2_reduction_cost=3.0,
        handoff_digest=D1,
    )


def make_lift(*, empty=False):
    return ns(
        status=LIFT_EMPTY_STATUS if empty else LIFT_NONEMPTY_STATUS,
        certified=True,
        exact=True,
        complete=True,
        parent_action_degree=10,
        child_ground_size=5,
        reduction_identity=D0,
        child_result_identity=D2,
        transcript_digest=D3,
        parent_representative=None if empty else tuple(range(10)),
        parent_stabilizer_generators=(),
    )


def test_nonempty_binding_success_and_replay():
    handoff = make_handoff()
    lift = make_lift()
    cert = certify_johnson_recursive_result_accounting_binding(
        handoff,
        lift,
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )
    assert cert.certified
    assert cert.exact and cert.complete
    assert cert.outcome_kind == "nonempty"
    assert cert.parent_action_degree == 10
    assert cert.child_ground_size == 5
    assert cert.reduction_identity == D0
    assert cert.handoff_digest == D1
    assert cert.child_result_identity == D2
    assert cert.result_lift_digest == D3
    assert cert.binding_digest.startswith("sha256:")
    assert replay_johnson_recursive_result_accounting_binding(
        cert,
        handoff,
        lift,
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )


def test_exact_empty_binding_success():
    cert = certify_johnson_recursive_result_accounting_binding(
        make_handoff(),
        make_lift(empty=True),
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )
    assert cert.certified
    assert cert.outcome_kind == "exact_empty"


def test_handoff_replay_is_mandatory():
    cert = certify_johnson_recursive_result_accounting_binding(
        make_handoff(),
        make_lift(),
        handoff_replay_verified=False,
        result_lift_replay_verified=True,
    )
    assert not cert.certified
    assert "handoff" in cert.reason


def test_result_lift_replay_is_mandatory():
    cert = certify_johnson_recursive_result_accounting_binding(
        make_handoff(),
        make_lift(),
        handoff_replay_verified=True,
        result_lift_replay_verified=False,
    )
    assert not cert.certified
    assert "result lift" in cert.reason


def test_reduction_identity_mismatch_fails_closed():
    lift = make_lift()
    lift.reduction_identity = "sha256:" + "9" * 64
    cert = certify_johnson_recursive_result_accounting_binding(
        make_handoff(),
        lift,
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )
    assert not cert.certified
    assert "different reduction identities" in cert.reason


def test_parent_action_degree_mismatch_fails_closed():
    lift = make_lift(empty=True)
    lift.parent_action_degree = 11
    cert = certify_johnson_recursive_result_accounting_binding(
        make_handoff(),
        lift,
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )
    assert not cert.certified
    assert "different represented parent action degree" in cert.reason


def test_child_ground_measure_mismatch_fails_closed():
    lift = make_lift(empty=True)
    lift.child_ground_size = 4
    cert = certify_johnson_recursive_result_accounting_binding(
        make_handoff(),
        lift,
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )
    assert not cert.certified
    assert "different Johnson recursive child measure" in cert.reason


def test_uncertified_recurrence_validation_fails_closed():
    handoff = make_handoff()
    handoff.validation.certified = False
    cert = certify_johnson_recursive_result_accounting_binding(
        handoff,
        make_lift(),
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )
    assert not cert.certified
    assert "recurrence validation" in cert.reason


def test_wrong_accounting_edge_measure_fails_closed():
    handoff = make_handoff()
    handoff.accounting_root.children[0].node.m = 4
    cert = certify_johnson_recursive_result_accounting_binding(
        handoff,
        make_lift(),
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )
    assert not cert.certified
    assert "child measure" in cert.reason


def test_nonempty_requires_valid_parent_permutation():
    lift = make_lift()
    lift.parent_representative = (0,) * 10
    cert = certify_johnson_recursive_result_accounting_binding(
        make_handoff(),
        lift,
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )
    assert not cert.certified
    assert "not a permutation" in cert.reason


def test_empty_may_not_smuggle_nonempty_payload():
    lift = make_lift(empty=True)
    lift.parent_stabilizer_generators = (tuple(range(10)),)
    cert = certify_johnson_recursive_result_accounting_binding(
        make_handoff(),
        lift,
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )
    assert not cert.certified
    assert "exact-empty" in cert.reason


def test_malformed_digest_fails_closed():
    handoff = make_handoff()
    handoff.handoff_digest = "not-a-digest"
    cert = certify_johnson_recursive_result_accounting_binding(
        handoff,
        make_lift(),
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )
    assert not cert.certified
    assert "sha256" in cert.reason


def test_replay_rejects_tampered_certificate():
    handoff = make_handoff()
    lift = make_lift()
    cert = certify_johnson_recursive_result_accounting_binding(
        handoff,
        lift,
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )
    tampered = copy.copy(cert)
    object.__setattr__(tampered, "binding_digest", "sha256:" + "f" * 64)
    assert not replay_johnson_recursive_result_accounting_binding(
        tampered,
        handoff,
        lift,
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )


def test_wrong_handoff_status_fails_closed():
    handoff = make_handoff()
    handoff.status = "certified_but_different_contract"
    cert = certify_johnson_recursive_result_accounting_binding(
        handoff,
        make_lift(),
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )
    assert not cert.certified
    assert "certified rev291-style status" in cert.reason


def test_wrong_lift_status_fails_closed():
    lift = make_lift()
    lift.status = "some_other_exact_status"
    cert = certify_johnson_recursive_result_accounting_binding(
        make_handoff(),
        lift,
        handoff_replay_verified=True,
        result_lift_replay_verified=True,
    )
    assert not cert.certified
    assert "unexpected recursive result-lift status" in cert.reason
