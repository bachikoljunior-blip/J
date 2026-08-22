from dataclasses import replace
from itertools import permutations

from bounded_group_transport import act_string
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_state_orbit_candidate_v1 import (
    build_state_orbit_candidate_proof_identity,
    exact_state_orbit_candidate_string_isomorphism,
    state_orbit_candidate_envelope,
    validate_state_orbit_candidate_proof_identity,
)
from proof_dag_accounting_v1 import validate_execution_proof_dag


def _symmetric_group(n):
    return schreier_stabilizer_chain(tuple(permutations(range(n))))


def test_exact_state_orbit_terminal_is_an_execution_proof_dag_consumer():
    group = _symmetric_group(5)
    candidate = RightCoset(group, (1, 2, 3, 4, 0))
    source = (0, 0, 0, 1, 1)
    target = act_string(source, (2, 0, 1, 4, 3))
    max_work = 10**20

    proof = exact_state_orbit_candidate_string_isomorphism(
        candidate,
        source,
        target,
        root_n=5,
        max_work=max_work,
    )
    envelope = state_orbit_candidate_envelope(
        candidate,
        target,
        max_work=max_work,
    )
    expected = build_state_orbit_candidate_proof_identity(
        candidate,
        source,
        target,
        root_n=5,
        envelope=envelope,
    )

    identity_check = validate_state_orbit_candidate_proof_identity(proof, expected)
    assert identity_check.certified, identity_check
    assert proof.coset is not None
    assert act_string(source, proof.coset.representative) == target

    dag_check = validate_execution_proof_dag(proof, original_root_n=5)
    assert dag_check.certified, dag_check
    assert dag_check.status == "certified_execution_proof_dag"
    assert dag_check.unique_nodes == 1
    assert dag_check.execution_occurrences == 1
    _ = hash(proof.proof_identity)


def test_state_orbit_resource_gate_is_part_of_the_execution_identity():
    group = _symmetric_group(5)
    candidate = RightCoset(group, identity(5))
    values = (0, 0, 0, 0, 1)

    first = exact_state_orbit_candidate_string_isomorphism(
        candidate,
        values,
        values,
        root_n=5,
        max_work=10**19,
    )
    second = exact_state_orbit_candidate_string_isomorphism(
        candidate,
        values,
        values,
        root_n=5,
        max_work=10**20,
    )

    assert first.exact and second.exact
    assert first.coset is not None and second.coset is not None
    assert first.coset.subgroup.order == second.coset.subgroup.order
    assert first.proof_identity != second.proof_identity
    assert dict(first.proof_identity.resource_identity)["max_work"] == 10**19
    assert dict(second.proof_identity.resource_identity)["max_work"] == 10**20


def test_opaque_hashable_color_executes_but_proof_dag_reuse_fails_closed():
    class OpaqueColor:
        def __init__(self, label):
            self.label = label

        def __hash__(self):
            return hash(self.label)

        def __eq__(self, other):
            return isinstance(other, OpaqueColor) and self.label == other.label

        def __repr__(self):
            return f"OpaqueColor({self.label!r})"

    group = _symmetric_group(4)
    candidate = RightCoset(group, identity(4))
    x = OpaqueColor("x")
    values = (x, x, "y", "y")

    proof = exact_state_orbit_candidate_string_isomorphism(
        candidate,
        values,
        values,
        root_n=4,
        max_work=10**20,
    )

    assert proof.exact
    assert proof.proof_identity is not None
    assert not proof.proof_identity.replay_stable
    dag_check = validate_execution_proof_dag(proof, original_root_n=4)
    assert not dag_check.certified
    assert dag_check.status == "unstable_root_proof_identity"


def test_cap_rejection_stays_unshareable_and_measure_tampering_is_rejected():
    group = _symmetric_group(5)
    candidate = RightCoset(group, identity(5))
    values = tuple(range(5))

    rejected = exact_state_orbit_candidate_string_isomorphism(
        candidate,
        values,
        values,
        root_n=5,
        max_work=1,
    )
    assert rejected.status == "undetermined_state_orbit_work_cap"
    assert not rejected.exact
    assert rejected.proof_identity is None

    exact = exact_state_orbit_candidate_string_isomorphism(
        candidate,
        values,
        values,
        root_n=5,
        max_work=10**20,
    )
    tampered = replace(exact, root_n=6)
    identity_check = validate_state_orbit_candidate_proof_identity(
        tampered,
        exact.proof_identity,
    )
    assert not identity_check.certified
    assert identity_check.status == "inconsistent_state_orbit_proof_measure"


def test_identity_builder_rejects_a_misdeclared_derived_envelope():
    group = _symmetric_group(5)
    candidate = RightCoset(group, identity(5))
    values = (0, 0, 0, 0, 1)
    envelope = state_orbit_candidate_envelope(
        candidate,
        values,
        max_work=10**20,
    )
    tampered = replace(
        envelope,
        state_image_upper_bound=envelope.state_image_upper_bound + 1,
    )

    try:
        build_state_orbit_candidate_proof_identity(
            candidate,
            values,
            values,
            root_n=5,
            envelope=tampered,
        )
    except ValueError as exc:
        assert "exact admitted envelope" in str(exc)
    else:
        raise AssertionError("a misdeclared state-orbit envelope was accepted")
