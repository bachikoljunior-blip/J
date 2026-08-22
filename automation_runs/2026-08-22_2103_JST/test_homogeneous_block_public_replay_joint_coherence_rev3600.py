import copy
import unittest

from homogeneous_block_public_replay_joint_coherence_v1 import (
    JointCoherenceError, build_joint_coherence, verify_joint_coherence,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64
E = "e" * 64
F = "f" * 64
G = "1" * 64


def action():
    return {
        "schema_version": 1,
        "replay_verified": True,
        "status": "ok",
        "original_root_sha256": A,
        "domain_degree": 12,
        "block_count": 4,
        "block_size": 3,
        "block_action_provenance_sha256": B,
        "kernel_factorization_sha256": C,
        "public_seal_sha256": D,
    }


def relation(status="ok"):
    return {
        "schema_version": 1,
        "replay_verified": True,
        "status": status,
        "original_root_sha256": A,
        "domain_degree": 12,
        "block_count": 4,
        "block_size": 3,
        "relation_provenance_sha256": E,
        "relation_transcript_sha256": F,
        "public_seal_sha256": G,
    }


class Rev3600Tests(unittest.TestCase):
    def test_ok(self):
        cert = build_joint_coherence(action(), relation())
        self.assertTrue(cert.certified)
        self.assertEqual(cert.status, "ok")
        self.assertTrue(verify_joint_coherence(cert.to_dict(), action(), relation()))

    def test_exact_empty_preserved(self):
        cert = build_joint_coherence(action(), relation("exact_empty"))
        self.assertEqual(cert.status, "exact_empty")
        self.assertTrue(verify_joint_coherence(cert.to_dict(), action(), relation("exact_empty")))

    def test_action_replay_false(self):
        x = action(); x["replay_verified"] = False
        with self.assertRaises(JointCoherenceError): build_joint_coherence(x, relation())

    def test_relation_replay_false(self):
        x = relation(); x["replay_verified"] = False
        with self.assertRaises(JointCoherenceError): build_joint_coherence(action(), x)

    def test_bool_coercion_rejected(self):
        x = action(); x["schema_version"] = True
        with self.assertRaises(JointCoherenceError): build_joint_coherence(x, relation())

    def test_extra_field_rejected(self):
        x = relation(); x["smuggled"] = "x"
        with self.assertRaises(JointCoherenceError): build_joint_coherence(action(), x)

    def test_bad_digest_rejected(self):
        x = relation(); x["public_seal_sha256"] = "ABC"
        with self.assertRaises(JointCoherenceError): build_joint_coherence(action(), x)

    def test_action_status_closed(self):
        x = action(); x["status"] = "exact_empty"
        with self.assertRaises(JointCoherenceError): build_joint_coherence(x, relation())

    def test_relation_status_closed(self):
        x = relation(); x["status"] = "unknown"
        with self.assertRaises(JointCoherenceError): build_joint_coherence(action(), x)

    def test_block_arithmetic(self):
        x = action(); x["block_size"] = 4
        with self.assertRaises(JointCoherenceError): build_joint_coherence(x, relation())

    def test_cross_domain_drift(self):
        x = relation(); x["domain_degree"] = 15; x["block_count"] = 5
        with self.assertRaises(JointCoherenceError): build_joint_coherence(action(), x)

    def test_cross_root_drift(self):
        x = relation(); x["original_root_sha256"] = B
        with self.assertRaises(JointCoherenceError): build_joint_coherence(action(), x)

    def test_same_upstream_seal_rejected(self):
        x = relation(); x["public_seal_sha256"] = D
        with self.assertRaises(JointCoherenceError): build_joint_coherence(action(), x)

    def test_certificate_tamper(self):
        cert = build_joint_coherence(action(), relation()).to_dict()
        cert["block_count"] = 5
        self.assertFalse(verify_joint_coherence(cert, action(), relation()))

    def test_certificate_schema_drift(self):
        cert = build_joint_coherence(action(), relation()).to_dict()
        cert["extra"] = 1
        self.assertFalse(verify_joint_coherence(cert, action(), relation()))

    def test_deterministic(self):
        first = build_joint_coherence(action(), relation()).coherence_identity
        second = build_joint_coherence(copy.deepcopy(action()), copy.deepcopy(relation())).coherence_identity
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
