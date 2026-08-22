from dataclasses import replace

import pytest

from signed_johnson_ground_proof_dag_consumer_v1 import (
    build_signed_johnson_ground_identity,
    signed_johnson_ground_proof_dag_consumer,
    validate_signed_johnson_ground_identity,
)
from signed_johnson_ground_relational_si_v1 import (
    signed_johnson_ground_relational_small_order_terminal,
)
from test_signed_johnson_ground_relational_si_rev176 import pgl2_8_on_pairs, relabel_target


def _nonempty_fixture():
    group, generators = pgl2_8_on_pairs()
    source = tuple(range(group.degree))
    witness = generators[0]
    target = relabel_target(source, witness)
    return group, source, target, witness


def test_exact_nonempty_signed_ground_terminal_enters_shared_proof_dag():
    group, source, target, witness = _nonempty_fixture()
    got = signed_johnson_ground_proof_dag_consumer(
        group,
        source,
        target,
        root_n=64,
        max_group_order=1024,
    )
    assert got.status == "certified_signed_johnson_ground_proof_dag", got
    assert got.identity_validation is not None and got.identity_validation.certified
    assert got.dag_validation is not None and got.dag_validation.certified
    assert got.dag_validation.status == "certified_execution_proof_dag"
    assert got.dag_validation.unique_nodes == 1
    assert got.dag_validation.execution_occurrences == 1
    assert got.proof.coset is not None and got.proof.coset.contains(witness)
    assert got.proof.ground_size == 9 and got.proof.subset_size == 2
    assert got.proof.certified_signed_group_order == 504
    assert got.proof.signed_elements_checked == 1008
    assert got.proof.proof_identity is not None
    assert got.proof.proof_identity.replay_stable


def test_exact_empty_signed_ground_terminal_enters_shared_proof_dag():
    group, _, _, _ = _nonempty_fixture()
    source = tuple(range(group.degree))
    target = list(source)
    target[0] = 999
    got = signed_johnson_ground_proof_dag_consumer(
        group,
        source,
        tuple(target),
        root_n=64,
        max_group_order=1024,
    )
    assert got.status == "certified_signed_johnson_ground_proof_dag", got
    assert got.proof.status == "exact_empty_signed_johnson_ground_relation"
    assert got.proof.coset is None
    assert got.proof.signed_elements_checked == 504
    assert got.identity_validation is not None and got.identity_validation.certified
    assert got.dag_validation is not None and got.dag_validation.certified


def test_group_order_cap_remains_nonexact_and_identity_free():
    group, source, _, _ = _nonempty_fixture()
    got = signed_johnson_ground_proof_dag_consumer(
        group,
        source,
        source,
        root_n=64,
        max_group_order=128,
    )
    assert got.status == "underlying_signed_johnson_ground_terminal_not_exact"
    assert got.proof.status == "undetermined_signed_ground_group_order_cap"
    assert not got.proof.exact
    assert got.proof.proof_identity is None
    assert got.identity_validation is None
    assert got.dag_validation is None


def test_opaque_value_executes_exactly_but_cannot_be_shared_by_identity():
    group, generators = pgl2_8_on_pairs()

    class Opaque:
        pass

    source = list(range(group.degree))
    marker = Opaque()
    source[0] = marker
    source = tuple(source)
    target = relabel_target(source, generators[0])
    got = signed_johnson_ground_proof_dag_consumer(
        group,
        source,
        target,
        root_n=64,
        max_group_order=1024,
    )
    assert got.status == "unstable_signed_johnson_ground_proof_identity", got
    assert got.proof.exact
    assert got.proof.proof_identity is None
    assert got.identity_validation is not None and not got.identity_validation.certified
    assert got.dag_validation is None


def test_identity_tampering_fails_closed_before_shared_dag_validation():
    group, source, target, _ = _nonempty_fixture()
    got = signed_johnson_ground_proof_dag_consumer(
        group,
        source,
        target,
        root_n=64,
        max_group_order=1024,
    )
    identity = got.proof.proof_identity
    tampered_identity = replace(identity, ground_size=identity.ground_size + 1)
    tampered = replace(got.proof, proof_identity=tampered_identity)
    checked = validate_signed_johnson_ground_identity(tampered, identity)
    assert checked.status == "mismatched_signed_johnson_ground_proof_identity"
    assert not checked.certified


def test_terminal_cost_or_accounting_drift_fails_closed():
    group, source, target, _ = _nonempty_fixture()
    proof = signed_johnson_ground_relational_small_order_terminal(
        group,
        source,
        target,
        root_n=64,
        max_group_order=1024,
    )
    identity = build_signed_johnson_ground_identity(
        group,
        source,
        target,
        proof,
        root_n=64,
        max_group_order=1024,
    )
    attached = replace(proof, proof_identity=identity)
    bad_accounting = replace(
        attached.accounting,
        local_log2_cost_bound=attached.accounting.local_log2_cost_bound + 1.0,
    )
    tampered = replace(attached, accounting=bad_accounting)
    checked = validate_signed_johnson_ground_identity(tampered, identity)
    assert checked.status == "inconsistent_signed_johnson_ground_accounting"
    assert not checked.certified


def test_nonfinite_quasipolynomial_envelope_fails_closed_in_shared_validator():
    group, source, target, _ = _nonempty_fixture()
    got = signed_johnson_ground_proof_dag_consumer(
        group,
        source,
        target,
        root_n=64,
        max_group_order=1024,
        quasipoly_constant=float("nan"),
    )
    assert got.status == "invalid_proof_dag_envelope"
    assert got.identity_validation is not None and got.identity_validation.certified
    assert got.dag_validation is not None and not got.dag_validation.certified


def test_invalid_root_is_rejected_without_numeric_coercion():
    group, source, target, _ = _nonempty_fixture()
    with pytest.raises(ValueError):
        signed_johnson_ground_proof_dag_consumer(
            group,
            source,
            target,
            root_n=True,
            max_group_order=1024,
        )
