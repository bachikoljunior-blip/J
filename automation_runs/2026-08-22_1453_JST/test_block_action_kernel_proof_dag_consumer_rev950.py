import dataclasses
import math
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
LEGACY = HERE.parent / "2026-08-19_0851_JST"
for path in (HERE, LEGACY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from block_action_kernel_proof_dag_consumer_v1 import (
    block_action_kernel_proof_dag_consumer,
    build_block_action_kernel_proof_identity,
    validate_block_action_kernel_proof_identity,
)
from homogeneous_block_action_kernel_v1 import certify_block_action_kernel_factorization
from homogeneous_block_action_provenance_v1 import certify_group_block_action_equivariance


class BlockActionKernelProofDAGRev950Test(unittest.TestCase):
    def provenance(self, blocks, source_generators, target_generators=None):
        if target_generators is None:
            target_generators = source_generators
        return certify_group_block_action_equivariance(
            blocks,
            blocks,
            list(range(len(blocks))),
            source_generators,
            target_generators,
        )

    def wreath_fixture(self):
        provenance = self.provenance(
            [[0, 1], [2, 3]],
            [
                (1, 0, 2, 3),
                (0, 1, 3, 2),
                (2, 3, 0, 1),
            ],
        )
        certificate = certify_block_action_kernel_factorization(provenance)
        self.assertTrue(certificate.exact)
        return provenance, certificate

    def test_exact_factorization_enters_shared_proof_dag(self):
        provenance, certificate = self.wreath_fixture()
        result = block_action_kernel_proof_dag_consumer(provenance, certificate)
        self.assertTrue(result.certified, result.reason)
        self.assertEqual(result.status, "certified_block_action_kernel_proof_dag")
        self.assertTrue(result.identity_validation.certified)
        self.assertTrue(result.dag_validation.certified)
        self.assertEqual(result.dag_validation.unique_nodes, 1)
        self.assertEqual(result.dag_validation.execution_occurrences, 1)
        self.assertEqual(result.proof.proof_identity.factorization_digest, certificate.certificate_digest)

    def test_identity_freezes_kernel_and_order_factorization(self):
        provenance, certificate = self.wreath_fixture()
        identity = build_block_action_kernel_proof_identity(certificate, provenance, root_n=8)
        self.assertEqual(identity.root_n, 8)
        self.assertEqual(dict(identity.order_identity)["source_group_order"], 8)
        self.assertEqual(dict(identity.order_identity)["quotient_image_order"], 2)
        self.assertEqual(dict(identity.order_identity)["source_kernel_order"], 4)
        self.assertEqual(identity.source_kernel_generators, certificate.source_kernel_generators)
        self.assertGreater(identity.external_log2_cost_bound, 0.0)
        self.assertTrue(identity.replay_stable)

    def test_identity_is_deterministic(self):
        provenance, certificate = self.wreath_fixture()
        first = build_block_action_kernel_proof_identity(certificate, provenance)
        second = build_block_action_kernel_proof_identity(certificate, provenance)
        self.assertEqual(first, second)
        self.assertEqual(hash(first), hash(second))

    def test_tampered_factorization_digest_fails_closed(self):
        provenance, certificate = self.wreath_fixture()
        tampered = dataclasses.replace(certificate, certificate_digest="sha256:" + "0" * 64)
        result = block_action_kernel_proof_dag_consumer(provenance, tampered)
        self.assertFalse(result.certified)
        self.assertEqual(result.status, "rejected_block_action_kernel_identity")
        self.assertIn("does not replay", result.reason)

    def test_wrong_provenance_fails_closed(self):
        provenance, certificate = self.wreath_fixture()
        wrong = self.provenance([[0, 1, 2, 3]], [(1, 0, 2, 3)])
        result = block_action_kernel_proof_dag_consumer(wrong, certificate)
        self.assertFalse(result.certified)
        self.assertIn("does not replay", result.reason)

    def test_root_must_dominate_domain(self):
        provenance, certificate = self.wreath_fixture()
        result = block_action_kernel_proof_dag_consumer(provenance, certificate, root_n=3)
        self.assertFalse(result.certified)
        self.assertIn("dominating", result.reason)

    def test_boolean_root_is_rejected(self):
        provenance, certificate = self.wreath_fixture()
        result = block_action_kernel_proof_dag_consumer(provenance, certificate, root_n=True)
        self.assertFalse(result.certified)
        self.assertIn("root_n", result.reason)

    def test_nonexact_factorization_is_rejected(self):
        provenance, certificate = self.wreath_fixture()
        tampered = dataclasses.replace(certificate, exact=False, complete=False)
        result = block_action_kernel_proof_dag_consumer(provenance, tampered)
        self.assertFalse(result.certified)
        self.assertIn("only exact complete", result.reason)

    def test_source_and_target_kernel_orders_may_differ(self):
        provenance = self.provenance(
            [[0, 1], [2, 3]],
            [(1, 0, 2, 3)],
            [(0, 1, 2, 3)],
        )
        certificate = certify_block_action_kernel_factorization(provenance)
        self.assertEqual(certificate.source_kernel_order, 2)
        self.assertEqual(certificate.target_kernel_order, 1)
        result = block_action_kernel_proof_dag_consumer(provenance, certificate)
        self.assertTrue(result.certified, result.reason)

    def test_envelope_nan_fails_closed(self):
        provenance, certificate = self.wreath_fixture()
        result = block_action_kernel_proof_dag_consumer(
            provenance,
            certificate,
            quasipoly_constant=float("nan"),
        )
        self.assertFalse(result.certified)
        self.assertEqual(result.status, "invalid_proof_dag_envelope")

    def test_tiny_envelope_fails_closed(self):
        provenance, certificate = self.wreath_fixture()
        result = block_action_kernel_proof_dag_consumer(
            provenance,
            certificate,
            quasipoly_constant=0.000001,
        )
        self.assertFalse(result.certified)
        self.assertIn("envelope", result.reason)

    def test_attached_identity_mismatch_is_rejected(self):
        provenance, certificate = self.wreath_fixture()
        result = block_action_kernel_proof_dag_consumer(provenance, certificate)
        self.assertTrue(result.certified)
        expected = result.proof.proof_identity
        altered = dataclasses.replace(expected, generator_count=expected.generator_count + 1)
        validation = validate_block_action_kernel_proof_identity(
            result.proof,
            certificate,
            provenance,
            altered,
        )
        self.assertFalse(validation.certified)
        self.assertEqual(validation.status, "mismatched_block_action_kernel_proof_identity")

    def test_local_and_external_costs_are_finite(self):
        provenance, certificate = self.wreath_fixture()
        result = block_action_kernel_proof_dag_consumer(provenance, certificate)
        self.assertTrue(result.certified)
        self.assertTrue(math.isfinite(result.proof.local_log2_cost_bound))
        self.assertTrue(math.isfinite(result.proof.proof_identity.external_log2_cost_bound))
        self.assertGreaterEqual(result.proof.proof_identity.external_log2_cost_bound, result.proof.local_log2_cost_bound)


if __name__ == "__main__":
    unittest.main()
