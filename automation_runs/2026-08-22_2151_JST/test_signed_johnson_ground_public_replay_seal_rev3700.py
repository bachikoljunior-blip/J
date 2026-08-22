from dataclasses import replace

from signed_johnson_ground_public_replay_seal_v1 import (
    build_signed_johnson_ground_public_replay_seal,
    verify_signed_johnson_ground_public_replay_seal,
)
from test_signed_johnson_ground_relational_si_rev176 import pgl2_8_on_pairs, relabel_target


def _nonempty_fixture():
    group, generators = pgl2_8_on_pairs()
    source = tuple(range(group.degree))
    target = relabel_target(source, generators[0])
    return group, source, target


def test_nonempty_exact_execution_receives_deterministic_public_replay_seal():
    group, source, target = _nonempty_fixture()
    first = build_signed_johnson_ground_public_replay_seal(group, source, target, root_n=64, max_group_order=1024)
    second = build_signed_johnson_ground_public_replay_seal(group, source, target, root_n=64, max_group_order=1024)
    assert first.certified and second.certified
    assert first.seal == second.seal
    assert first.seal.terminal_status == "exact_signed_johnson_ground_relation_coset"
    assert first.seal.signed_elements_checked == 1008
    assert first.seal.certified_signed_group_order == 504


def test_exact_empty_execution_receives_public_replay_seal():
    group, source, _ = _nonempty_fixture()
    target = list(source)
    target[0] = 999
    got = build_signed_johnson_ground_public_replay_seal(group, source, tuple(target), root_n=64, max_group_order=1024)
    assert got.certified
    assert got.seal.terminal_status == "exact_empty_signed_johnson_ground_relation"
    assert got.seal.signed_elements_checked == 504


def test_independent_replay_verifies_exact_seal():
    group, source, target = _nonempty_fixture()
    built = build_signed_johnson_ground_public_replay_seal(group, source, target, root_n=64, max_group_order=1024)
    verified = verify_signed_johnson_ground_public_replay_seal(built.seal, group, source, target, root_n=64, max_group_order=1024)
    assert verified.status == "verified_signed_johnson_ground_public_replay_seal"
    assert verified.certified


def test_payload_digest_tamper_fails_closed_before_replay():
    group, source, target = _nonempty_fixture()
    built = build_signed_johnson_ground_public_replay_seal(group, source, target, root_n=64, max_group_order=1024)
    tampered = replace(built.seal, ground_size=built.seal.ground_size + 1)
    checked = verify_signed_johnson_ground_public_replay_seal(tampered, group, source, target, root_n=64, max_group_order=1024)
    assert not checked.certified
    assert checked.status == "invalid_signed_johnson_ground_public_replay_seal"


def test_result_identity_tamper_fails_closed():
    group, source, target = _nonempty_fixture()
    built = build_signed_johnson_ground_public_replay_seal(group, source, target, root_n=64, max_group_order=1024)
    tampered = replace(built.seal, result_identity_sha256="0" * 64)
    checked = verify_signed_johnson_ground_public_replay_seal(tampered, group, source, target, root_n=64, max_group_order=1024)
    assert not checked.certified


def test_source_or_target_drift_changes_replay_and_is_rejected():
    group, source, target = _nonempty_fixture()
    built = build_signed_johnson_ground_public_replay_seal(group, source, target, root_n=64, max_group_order=1024)
    drifted = list(target)
    drifted[0] = 123456
    checked = verify_signed_johnson_ground_public_replay_seal(built.seal, group, source, tuple(drifted), root_n=64, max_group_order=1024)
    assert not checked.certified
    assert checked.status in {"signed_johnson_ground_public_replay_mismatch", "signed_johnson_ground_public_replay_failed"}


def test_resource_gate_drift_is_rejected_by_replay():
    group, source, target = _nonempty_fixture()
    built = build_signed_johnson_ground_public_replay_seal(group, source, target, root_n=64, max_group_order=1024)
    checked = verify_signed_johnson_ground_public_replay_seal(built.seal, group, source, target, root_n=64, max_group_order=2048)
    assert not checked.certified
    assert checked.status == "signed_johnson_ground_public_replay_mismatch"


def test_group_order_cap_nonexact_execution_is_not_sealed():
    group, source, target = _nonempty_fixture()
    got = build_signed_johnson_ground_public_replay_seal(group, source, target, root_n=64, max_group_order=128)
    assert not got.certified
    assert got.seal is None
    assert got.status == "rev295_execution_not_certified"


def test_nonfinite_envelope_is_not_sealed():
    group, source, target = _nonempty_fixture()
    got = build_signed_johnson_ground_public_replay_seal(group, source, target, root_n=64, max_group_order=1024, quasipoly_constant=float("nan"))
    assert not got.certified
    assert got.seal is None


def test_wrong_seal_type_fails_closed_without_execution():
    group, source, target = _nonempty_fixture()
    checked = verify_signed_johnson_ground_public_replay_seal(object(), group, source, target, root_n=64, max_group_order=1024)
    assert not checked.certified
    assert checked.status == "invalid_signed_johnson_ground_public_replay_seal"
