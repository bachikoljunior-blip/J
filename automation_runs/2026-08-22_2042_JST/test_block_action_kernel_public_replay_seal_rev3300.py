import dataclasses
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
REV950 = HERE.parent / "2026-08-22_1453_JST"
LEGACY = HERE.parent / "2026-08-19_0851_JST"
for path in (HERE, REV950, LEGACY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from block_action_kernel_public_replay_seal_v1 import (
    build_block_action_kernel_public_replay_seal,
    verify_block_action_kernel_public_replay_seal,
)
from homogeneous_block_action_kernel_v1 import certify_block_action_kernel_factorization
from homogeneous_block_action_provenance_v1 import certify_group_block_action_equivariance


class BlockActionKernelPublicReplaySealRev3300Test(unittest.TestCase):
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
        self.assertTrue(certificate.complete)
        return provenance, certificate

    def test_exact_factorization_builds_public_replay_seal(self):
        provenance, certificate = self.wreath_fixture()
        result = build_block_action_kernel_public_replay_seal(provenance, certificate)
        self.assertTrue(result.certified, result.reason)
        self.assertEqual(result.status, "certified_block_action_kernel_public_replay_seal")
        self.assertEqual(result.seal.schema, "block-action-kernel-public-replay-seal-v1")
        self.assertEqual(result.seal.provenance_digest, provenance.certificate_digest)
        self.assertEqual(result.seal.factorization_digest, certificate.certificate_digest)
        self.assertEqual(len(result.seal.seal_sha256), 64)
        self.assertEqual(result.seal.dag_unique_nodes, 1)
        self.assertEqual(result.seal.dag_execution_occurrences, 1)

    def test_independent_reexecution_verifies_exact_seal(self):
        provenance, certificate = self.wreath_fixture()
        built = build_block_action_kernel_public_replay_seal(provenance, certificate, root_n=8)
        self.assertTrue(built.certified, built.reason)
        verified = verify_block_action_kernel_public_replay_seal(
            provenance,
            certificate,
            built.seal,
            root_n=8,
        )
        self.assertTrue(verified.certified, verified.reason)
        self.assertEqual(verified.status, "verified_block_action_kernel_public_replay_seal")
        self.assertEqual(verified.seal, built.seal)

    def test_seal_is_deterministic(self):
        provenance, certificate = self.wreath_fixture()
        first = build_block_action_kernel_public_replay_seal(provenance, certificate)
        second = build_block_action_kernel_public_replay_seal(provenance, certificate)
        self.assertTrue(first.certified)
        self.assertTrue(second.certified)
        self.assertEqual(first.seal, second.seal)
        self.assertEqual(first.seal.seal_sha256, second.seal.seal_sha256)

    def test_root_and_factorization_identities_are_frozen(self):
        provenance, certificate = self.wreath_fixture()
        result = build_block_action_kernel_public_replay_seal(provenance, certificate, root_n=8)
        self.assertTrue(result.certified, result.reason)
        seal = result.seal
        self.assertEqual(seal.root_n, 8)
        self.assertEqual(seal.domain_degree, 4)
        self.assertEqual(seal.block_count, 2)
        self.assertEqual(dict(seal.order_identity)["source_group_order"], 8)
        self.assertEqual(dict(seal.order_identity)["quotient_image_order"], 2)
        self.assertEqual(dict(seal.order_identity)["source_kernel_order"], 4)
        self.assertGreater(dict(seal.work_identity)["work_cap"], 0)

    def test_tampered_seal_digest_fails_closed(self):
        provenance, certificate = self.wreath_fixture()
        built = build_block_action_kernel_public_replay_seal(provenance, certificate)
        tampered = dataclasses.replace(built.seal, seal_sha256="0" * 64)
        verified = verify_block_action_kernel_public_replay_seal(provenance, certificate, tampered)
        self.assertFalse(verified.certified)
        self.assertEqual(verified.status, "invalid_block_action_kernel_public_replay_seal")
        self.assertIn("digest", verified.reason)

    def test_tampered_proof_identity_digest_fails_closed(self):
        provenance, certificate = self.wreath_fixture()
        built = build_block_action_kernel_public_replay_seal(provenance, certificate)
        tampered = dataclasses.replace(built.seal, proof_identity_sha256="0" * 64)
        verified = verify_block_action_kernel_public_replay_seal(provenance, certificate, tampered)
        self.assertFalse(verified.certified)
        self.assertIn("digest", verified.reason)

    def test_tampered_kernel_generator_digest_fails_closed(self):
        provenance, certificate = self.wreath_fixture()
        built = build_block_action_kernel_public_replay_seal(provenance, certificate)
        tampered = dataclasses.replace(built.seal, source_kernel_generators_sha256="0" * 64)
        verified = verify_block_action_kernel_public_replay_seal(provenance, certificate, tampered)
        self.assertFalse(verified.certified)
        self.assertIn("digest", verified.reason)

    def test_tampered_order_identity_fails_before_reexecution(self):
        provenance, certificate = self.wreath_fixture()
        built = build_block_action_kernel_public_replay_seal(provenance, certificate)
        orders = list(built.seal.order_identity)
        orders[0] = (orders[0][0], orders[0][1] + 1)
        tampered = dataclasses.replace(built.seal, order_identity=tuple(orders))
        verified = verify_block_action_kernel_public_replay_seal(provenance, certificate, tampered)
        self.assertFalse(verified.certified)
        self.assertIn("source order factorization", verified.reason)

    def test_wrong_provenance_fails_reexecution(self):
        provenance, certificate = self.wreath_fixture()
        built = build_block_action_kernel_public_replay_seal(provenance, certificate)
        wrong = self.provenance([[0, 1, 2, 3]], [(1, 0, 2, 3)])
        verified = verify_block_action_kernel_public_replay_seal(wrong, certificate, built.seal)
        self.assertFalse(verified.certified)
        self.assertEqual(verified.status, "block_action_kernel_public_replay_execution_failed")
        self.assertIn("does not replay", verified.reason)

    def test_tampered_factorization_certificate_fails_reexecution(self):
        provenance, certificate = self.wreath_fixture()
        built = build_block_action_kernel_public_replay_seal(provenance, certificate)
        tampered_certificate = dataclasses.replace(
            certificate,
            certificate_digest="sha256:" + "0" * 64,
        )
        verified = verify_block_action_kernel_public_replay_seal(
            provenance,
            tampered_certificate,
            built.seal,
        )
        self.assertFalse(verified.certified)
        self.assertEqual(verified.status, "block_action_kernel_public_replay_execution_failed")

    def test_root_must_dominate_original_domain(self):
        provenance, certificate = self.wreath_fixture()
        result = build_block_action_kernel_public_replay_seal(provenance, certificate, root_n=3)
        self.assertFalse(result.certified)
        self.assertEqual(result.status, "rev950_execution_not_certified")
        self.assertIn("dominating", result.reason)

    def test_nonexact_certificate_does_not_receive_seal(self):
        provenance, certificate = self.wreath_fixture()
        tampered = dataclasses.replace(certificate, exact=False, complete=False)
        result = build_block_action_kernel_public_replay_seal(provenance, tampered)
        self.assertFalse(result.certified)
        self.assertEqual(result.status, "rev950_execution_not_certified")
        self.assertIn("only exact complete", result.reason)

    def test_tiny_quasipolynomial_envelope_fails_closed(self):
        provenance, certificate = self.wreath_fixture()
        result = build_block_action_kernel_public_replay_seal(
            provenance,
            certificate,
            quasipoly_constant=0.000001,
        )
        self.assertFalse(result.certified)
        self.assertEqual(result.status, "rev950_execution_not_certified")
        self.assertIn("envelope", result.reason)

    def test_nonfinite_public_accounting_bound_is_rejected(self):
        provenance, certificate = self.wreath_fixture()
        built = build_block_action_kernel_public_replay_seal(provenance, certificate)
        tampered = dataclasses.replace(built.seal, external_log2_cost_bound_hex=float("nan").hex())
        verified = verify_block_action_kernel_public_replay_seal(provenance, certificate, tampered)
        self.assertFalse(verified.certified)
        self.assertIn("not finite", verified.reason)

    def test_boolean_root_in_public_seal_is_rejected(self):
        provenance, certificate = self.wreath_fixture()
        built = build_block_action_kernel_public_replay_seal(provenance, certificate)
        tampered = dataclasses.replace(built.seal, root_n=True)
        verified = verify_block_action_kernel_public_replay_seal(provenance, certificate, tampered)
        self.assertFalse(verified.certified)
        self.assertIn("root_n", verified.reason)

    def test_asymmetric_source_target_kernels_still_seal(self):
        provenance = self.provenance(
            [[0, 1], [2, 3]],
            [(1, 0, 2, 3)],
            [(0, 1, 2, 3)],
        )
        certificate = certify_block_action_kernel_factorization(provenance)
        self.assertEqual(certificate.source_kernel_order, 2)
        self.assertEqual(certificate.target_kernel_order, 1)
        result = build_block_action_kernel_public_replay_seal(provenance, certificate)
        self.assertTrue(result.certified, result.reason)
        orders = dict(result.seal.order_identity)
        self.assertEqual(orders["source_kernel_order"], 2)
        self.assertEqual(orders["target_kernel_order"], 1)


if __name__ == "__main__":
    unittest.main()
