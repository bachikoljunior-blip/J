from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from permutation_group_schreier import identity, schreier_stabilizer_chain
from s1_proof_identity_v1 import (
    S1ProofIdentity,
    build_s1_proof_identity,
    validate_s1_proof_identity,
)
from s1_string_isomorphism_v4 import s1_string_isomorphism_v4


def _two_five_cycles():
    first = (1, 2, 3, 4, 0, 5, 6, 7, 8, 9)
    second = (0, 1, 2, 3, 4, 6, 7, 8, 9, 5)
    return schreier_stabilizer_chain((first, second))


def _nested_exact_proof(*, max_partition_states=4096):
    group = _two_five_cycles()
    source = (0, 0, 0, 0, 1, 2, 2, 2, 2, 3)
    target = (1, 0, 0, 0, 0, 3, 2, 2, 2, 2)
    proof = s1_string_isomorphism_v4(
        group,
        source,
        target,
        root_n=10,
        max_explicit_degree=8,
        max_group_order=1,
        max_partition_states=max_partition_states,
    )
    return group, source, target, proof


def test_every_nested_s1_result_carries_full_execution_identity():
    group, source, target, proof = _nested_exact_proof()
    assert proof.exact
    assert proof.operation_kind == "orbit_partition"
    assert len(proof.children) == 2
    assert isinstance(proof.proof_identity, S1ProofIdentity)
    assert proof.proof_identity.recursion_depth == 0
    assert proof.proof_identity.group_identity[0:2] == (10, 25)

    expected = build_s1_proof_identity(
        group,
        source,
        target,
        root_n=10,
        recursion_depth=0,
        polylog_power=2,
        max_explicit_degree=8,
        group_order_poly_power=2,
        max_group_order=1,
        max_partition_states=4096,
        max_recognition_nodes=500000,
        max_depth=64,
    )
    assert validate_s1_proof_identity(proof, expected).certified

    for child in proof.children:
        assert isinstance(child.proof_identity, S1ProofIdentity)
        assert child.proof_identity.recursion_depth == 1
        assert child.proof_identity.root_n == 10
        assert child.proof_identity.domain_size == 5
        assert child.proof_identity.group_identity[0] == 5


def test_orientation_root_and_resource_gates_are_distinct_identities():
    group, source, target, proof = _nested_exact_proof()
    changed_target = build_s1_proof_identity(
        group,
        source,
        tuple(reversed(target)),
        root_n=10,
        recursion_depth=0,
        polylog_power=2,
        max_explicit_degree=8,
        group_order_poly_power=2,
        max_group_order=1,
        max_partition_states=4096,
        max_recognition_nodes=500000,
        max_depth=64,
    )
    changed_root = build_s1_proof_identity(
        group,
        source,
        target,
        root_n=11,
        recursion_depth=0,
        polylog_power=2,
        max_explicit_degree=8,
        group_order_poly_power=2,
        max_group_order=1,
        max_partition_states=4096,
        max_recognition_nodes=500000,
        max_depth=64,
    )
    _, _, _, changed_resource_proof = _nested_exact_proof(max_partition_states=4095)

    assert proof.proof_identity != changed_target
    assert proof.proof_identity != changed_root
    assert proof.proof_identity != changed_resource_proof.proof_identity
    assert not validate_s1_proof_identity(proof, changed_target).certified


def test_identity_snapshots_mutable_values_and_is_frozen():
    group = schreier_stabilizer_chain((identity(2),))
    source = [["a"], ["b"]]
    target = [["b"], ["a"]]
    artifact = build_s1_proof_identity(
        group,
        source,
        target,
        root_n=2,
        recursion_depth=0,
        polylog_power=2,
        max_explicit_degree=8,
        group_order_poly_power=2,
        max_group_order=1,
        max_partition_states=4,
        max_recognition_nodes=8,
        max_depth=3,
    )
    snapshot = artifact.source_identity
    source[0].append("mutated")
    assert artifact.source_identity == snapshot
    assert artifact.replay_stable
    with pytest.raises(FrozenInstanceError):
        artifact.root_n = 3


def test_opaque_identity_is_recorded_but_not_replay_certified():
    class OpaqueColor:
        pass

    group = schreier_stabilizer_chain((identity(1),))
    color = OpaqueColor()
    artifact = build_s1_proof_identity(
        group,
        (color,),
        (color,),
        root_n=1,
        recursion_depth=0,
        polylog_power=2,
        max_explicit_degree=8,
        group_order_poly_power=2,
        max_group_order=1,
        max_partition_states=4,
        max_recognition_nodes=8,
        max_depth=3,
    )
    assert not artifact.replay_stable
    proof = s1_string_isomorphism_v4(
        group,
        (color,),
        (color,),
        root_n=1,
        max_group_order=1,
        max_partition_states=4,
        max_recognition_nodes=8,
        max_depth=3,
    )
    check = validate_s1_proof_identity(proof, artifact)
    assert not check.certified
    assert check.status == "unstable_opaque_s1_identity"
