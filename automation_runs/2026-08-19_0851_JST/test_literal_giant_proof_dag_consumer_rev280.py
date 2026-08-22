from dataclasses import replace
from math import factorial

from literal_giant_proof_dag_consumer_v1 import (
    build_literal_giant_proof_identity,
    certify_literal_giant_execution_proof_dag,
    validate_literal_giant_proof_identity,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _swap(n, a, b):
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def _cycle3(n, a, b, c):
    p = list(range(n))
    p[a], p[b], p[c] = b, c, a
    return tuple(p)


def _symmetric_group(n):
    return schreier_stabilizer_chain(tuple(_swap(n, i, i + 1) for i in range(n - 1)))


def _alternating_group(n):
    return schreier_stabilizer_chain(tuple(_cycle3(n, 0, 1, i) for i in range(2, n)))


def test_symmetric_exact_coset_is_admitted_to_shared_proof_dag():
    n = 7
    group = _symmetric_group(n)
    assert group.order == factorial(n)
    target = ("a", "a", "b", "b", "c", "c", "c")
    witness = _swap(n, 0, 2)
    source = tuple(target[witness[i]] for i in range(n))

    admitted = certify_literal_giant_execution_proof_dag(group, source, target, root_n=n)

    assert admitted.certified
    assert admitted.status == "certified_execution_proof_dag"
    assert admitted.proof.proof_identity is not None
    assert admitted.proof.coset is not None
    assert admitted.proof.coset.contains(witness)
    assert admitted.dag_validation.unique_nodes == 1
    assert admitted.dag_validation.execution_occurrences == 1


def test_value_multiplicity_exact_empty_is_admitted():
    n = 7
    group = _symmetric_group(n)
    source = (0, 0, 0, 1, 1, 2, 2)
    target = (0, 0, 1, 1, 1, 2, 2)

    admitted = certify_literal_giant_execution_proof_dag(group, source, target, root_n=n)

    assert admitted.certified
    assert admitted.proof.status == "exact_empty_literal_giant_value_multiplicity"
    assert admitted.proof.coset is None


def test_alternating_parity_exact_empty_is_admitted():
    n = 7
    group = _alternating_group(n)
    assert group.order * 2 == factorial(n)
    target = tuple(range(n))
    odd = _swap(n, 0, 1)
    source = tuple(target[odd[i]] for i in range(n))

    admitted = certify_literal_giant_execution_proof_dag(group, source, target, root_n=n)

    assert admitted.certified
    assert admitted.proof.status == "exact_empty_literal_alternating_parity"
    assert admitted.proof.coset is None


def test_nonliteral_group_remains_fail_closed_and_identity_free():
    n = 7
    group = schreier_stabilizer_chain((identity(n),))
    values = tuple(range(n))

    admitted = certify_literal_giant_execution_proof_dag(group, values, values, root_n=n)

    assert not admitted.certified
    assert admitted.status == "missing_literal_giant_proof_identity"
    assert admitted.proof.status == "undetermined_not_literal_giant"
    assert admitted.proof.proof_identity is None


def test_opaque_hashable_values_execute_exactly_but_cannot_be_dag_shared():
    class Token:
        pass

    n = 7
    group = _symmetric_group(n)
    token = Token()
    values = (token,) * n

    admitted = certify_literal_giant_execution_proof_dag(group, values, values, root_n=n)

    assert admitted.proof.exact
    assert admitted.proof.proof_identity is not None
    assert not admitted.proof.proof_identity.replay_stable
    assert not admitted.certified
    assert admitted.status == "unstable_opaque_literal_giant_identity"


def test_tampered_identity_is_rejected_before_shared_dag_validation():
    n = 7
    group = _symmetric_group(n)
    values = (0, 0, 1, 1, 2, 2, 3)
    admitted = certify_literal_giant_execution_proof_dag(group, values, values, root_n=n)
    assert admitted.certified

    expected = build_literal_giant_proof_identity(group, values, values, root_n=n)
    tampered = replace(admitted.proof, proof_identity=replace(expected, root_n=n + 1))
    checked = validate_literal_giant_proof_identity(tampered, expected)

    assert not checked.certified
    assert checked.status == "mismatched_literal_giant_proof_identity"


def test_original_root_envelope_remains_fail_closed():
    n = 7
    group = _symmetric_group(n)
    values = (0, 0, 1, 1, 2, 2, 3)

    admitted = certify_literal_giant_execution_proof_dag(
        group,
        values,
        values,
        root_n=n,
        quasipoly_constant=0.000001,
    )

    assert not admitted.certified
    assert admitted.status == "proof_dag_quasipolynomial_envelope_exceeded"
