from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import sys

MODULE_PATH = pathlib.Path(__file__).with_name("soj_parent_filtered_proof_dag_integrity_v1.py")
SPEC = importlib.util.spec_from_file_location("rev2707_impl", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def sha(value):
    return "sha256:" + hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def source_result(*, empty=False):
    reduction = sha(["reduction", 1])
    semantic = sha(["semantic", 2])
    instance = sha(["instance", 3])
    child = sha(["child", 4])
    if empty:
        status = MODULE.SOURCE_EMPTY_STATUS
        accepted = 0
        representative = None
        stabilizer = []
    else:
        status = MODULE.SOURCE_NONEMPTY_STATUS
        accepted = 2
        representative = [1, 2, 0]
        stabilizer = [[0, 1, 2], [1, 0, 2]]
    payload = {
        "schema_version": 1,
        "status": status,
        "reduction_identity": reduction,
        "semantic_binding_identity": semantic,
        "child_instance_identity": instance,
        "child_result_identity": child,
        "action_degree": 3,
        "candidate_count": 5,
        "accepted_count": accepted,
        "representative": representative,
        "parent_stabilizer_elements": stabilizer,
        "work_bound": 99,
    }
    return {
        **payload,
        "certified": True,
        "exact": True,
        "complete": True,
        "result_identity": sha(payload),
        "reason": "fixture",
    }


def rehash(result):
    keys = (
        "schema_version", "status", "reduction_identity", "semantic_binding_identity",
        "child_instance_identity", "child_result_identity", "action_degree",
        "candidate_count", "accepted_count", "representative",
        "parent_stabilizer_elements", "work_bound",
    )
    result["result_identity"] = sha({key: result[key] for key in keys})


def assert_rejected(result, needle=None):
    cert = MODULE.certify_parent_filtered_result_proof_dag(result)
    assert not cert.certified, cert
    if needle:
        assert needle in cert.reason, cert.reason


def test_nonempty_certifies_and_replays():
    result = source_result()
    cert = MODULE.certify_parent_filtered_result_proof_dag(result)
    assert cert.certified
    assert cert.status == MODULE.OUTPUT_STATUS
    assert cert.source_status == MODULE.SOURCE_NONEMPTY_STATUS
    assert cert.accepted_count == 2
    assert cert.node_count == 8
    assert cert.edge_count == 7
    replay = MODULE.replay_parent_filtered_result_proof_dag(result, cert)
    assert replay.certified
    assert replay.proof_dag_identity == cert.proof_dag_identity


def test_empty_certifies_without_hidden_witness_nodes():
    cert = MODULE.certify_parent_filtered_result_proof_dag(source_result(empty=True))
    assert cert.certified
    assert cert.node_count == 5
    assert cert.edge_count == 4
    assert all(not node["id"].startswith("witness:") for node in cert.proof_dag["nodes"])


def test_result_identity_tamper_fails_closed():
    result = source_result()
    result["result_identity"] = sha(["wrong"])
    assert_rejected(result, "result_identity")


def test_semantic_identity_tamper_without_rehash_fails_closed():
    result = source_result()
    result["semantic_binding_identity"] = sha(["changed"])
    assert_rejected(result, "result_identity")


def test_bool_is_not_an_integer():
    result = source_result()
    result["candidate_count"] = True
    assert_rejected(result, "strict integer")


def test_noncanonical_stabilizer_order_rejected_even_if_rehashed():
    result = source_result()
    result["parent_stabilizer_elements"] = list(reversed(result["parent_stabilizer_elements"]))
    rehash(result)
    assert_rejected(result, "canonically sorted")


def test_non_subgroup_stabilizer_rejected_even_if_rehashed():
    result = source_result()
    result["parent_stabilizer_elements"] = [[0, 1, 2], [1, 2, 0]]
    rehash(result)
    assert_rejected(result, "inverse closed")


def test_nonempty_cardinality_mismatch_rejected():
    result = source_result()
    result["accepted_count"] = 1
    rehash(result)
    assert_rejected(result, "cardinality")


def test_empty_hidden_representative_rejected():
    result = source_result(empty=True)
    result["representative"] = [0, 1, 2]
    rehash(result)
    assert_rejected(result, "must not carry a representative")


def test_empty_hidden_stabilizer_rejected():
    result = source_result(empty=True)
    result["parent_stabilizer_elements"] = [[0, 1, 2]]
    rehash(result)
    assert_rejected(result, "must not carry stabilizer witnesses")


def test_accepted_count_cannot_exceed_candidate_count():
    result = source_result()
    result["candidate_count"] = 1
    rehash(result)
    assert_rejected(result, "exceeds candidate_count")


def test_certificate_dag_tamper_fails_replay():
    result = source_result()
    cert = MODULE.certify_parent_filtered_result_proof_dag(result)
    tampered = cert.__dict__.copy()
    tampered["proof_dag"] = copy.deepcopy(cert.proof_dag)
    tampered["proof_dag"]["edges"] = list(tampered["proof_dag"]["edges"])[:-1]
    replay = MODULE.replay_parent_filtered_result_proof_dag(result, tampered)
    assert not replay.certified
    assert "proof_dag drift" in replay.reason


def test_certificate_identity_tamper_fails_replay():
    result = source_result()
    cert = MODULE.certify_parent_filtered_result_proof_dag(result)
    tampered = cert.__dict__.copy()
    tampered["proof_dag_identity"] = sha(["wrong"])
    replay = MODULE.replay_parent_filtered_result_proof_dag(result, tampered)
    assert not replay.certified
    assert "proof_dag_identity drift" in replay.reason


def test_deterministic_identity():
    result = source_result()
    left = MODULE.certify_parent_filtered_result_proof_dag(result)
    right = MODULE.certify_parent_filtered_result_proof_dag(copy.deepcopy(result))
    assert left.certified and right.certified
    assert left.proof_dag_identity == right.proof_dag_identity
    assert left.proof_dag == right.proof_dag


TESTS = [
    test_nonempty_certifies_and_replays,
    test_empty_certifies_without_hidden_witness_nodes,
    test_result_identity_tamper_fails_closed,
    test_semantic_identity_tamper_without_rehash_fails_closed,
    test_bool_is_not_an_integer,
    test_noncanonical_stabilizer_order_rejected_even_if_rehashed,
    test_non_subgroup_stabilizer_rejected_even_if_rehashed,
    test_nonempty_cardinality_mismatch_rejected,
    test_empty_hidden_representative_rejected,
    test_empty_hidden_stabilizer_rejected,
    test_accepted_count_cannot_exceed_candidate_count,
    test_certificate_dag_tamper_fails_replay,
    test_certificate_identity_tamper_fails_replay,
    test_deterministic_identity,
]


if __name__ == "__main__":
    failures = []
    for test in TESTS:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:
            failures.append((test.__name__, exc))
            print(f"FAIL {test.__name__}: {exc}")
    if failures:
        raise SystemExit(1)
    print(f"{len(TESTS)}/{len(TESTS)} rev2707 focused regressions passed")
