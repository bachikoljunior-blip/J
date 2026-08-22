import dataclasses
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
LEGACY = HERE.parent / "2026-08-19_0851_JST"
for path in (HERE, LEGACY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from homogeneous_block_action_provenance_v1 import certify_group_block_action_equivariance
from block_action_provenance_proof_dag_consumer_v1 import (
    block_action_provenance_proof_dag_consumer,
    build_block_action_provenance_proof_identity,
    validate_block_action_provenance_proof_identity,
)


def exact_certificate():
    return certify_group_block_action_equivariance(
        [[0, 2], [1, 3]],
        [[0, 2], [1, 3]],
        [0, 1],
        [(1, 2, 3, 0)],
        [(1, 2, 3, 0)],
    )


class BlockActionProvenanceProofDAGRev1600Test(unittest.TestCase):
    def test_exact_rev274_certificate_is_admitted(self):
        result = block_action_provenance_proof_dag_consumer(exact_certificate())
        self.assertTrue(result.certified)
        self.assertEqual(result.status, "certified_homogeneous_block_action_provenance_proof_dag")
        self.assertTrue(result.identity_validation.certified)
        self.assertEqual(result.proof.proof_identity.block_count, 2)

    def test_larger_original_root_is_bound_into_identity(self):
        result = block_action_provenance_proof_dag_consumer(exact_certificate(), root_n=8)
        self.assertTrue(result.certified)
        self.assertEqual(result.proof.proof_identity.root_n, 8)
        self.assertEqual(result.proof.accounting.n, 8)
        self.assertEqual(result.proof.accounting.m, 4)

    def test_root_smaller_than_domain_fails_closed(self):
        result = block_action_provenance_proof_dag_consumer(exact_certificate(), root_n=3)
        self.assertFalse(result.certified)
        self.assertEqual(result.status, "rejected_block_action_provenance_identity")

    def test_boolean_root_is_not_coerced(self):
        result = block_action_provenance_proof_dag_consumer(exact_certificate(), root_n=True)
        self.assertFalse(result.certified)
        self.assertEqual(result.status, "rejected_block_action_provenance_identity")

    def test_digest_tampering_fails_closed(self):
        certificate = dataclasses.replace(
            exact_certificate(), certificate_digest="sha256:" + "0" * 64
        )
        result = block_action_provenance_proof_dag_consumer(certificate)
        self.assertFalse(result.certified)
        self.assertEqual(result.status, "rejected_block_action_provenance_identity")

    def test_partition_tampering_fails_closed(self):
        certificate = exact_certificate()
        tampered = dataclasses.replace(
            certificate, source_blocks=((0, 1), (2, 3))
        )
        result = block_action_provenance_proof_dag_consumer(tampered)
        self.assertFalse(result.certified)
        self.assertEqual(result.status, "rejected_block_action_provenance_identity")

    def test_failed_rev274_result_is_not_promoted(self):
        failed = certify_group_block_action_equivariance(
            [[0, 1], [2, 3]],
            [[0, 1], [2, 3]],
            [0, 1],
            [(1, 2, 3, 0)],
            [(1, 2, 3, 0)],
        )
        self.assertFalse(failed.exact)
        result = block_action_provenance_proof_dag_consumer(failed)
        self.assertFalse(result.certified)
        self.assertEqual(result.status, "rejected_block_action_provenance_identity")

    def test_identity_mutation_is_detected(self):
        certificate = exact_certificate()
        identity = build_block_action_provenance_proof_identity(certificate)
        result = block_action_provenance_proof_dag_consumer(certificate)
        mutated = dataclasses.replace(identity, verification_work_units=identity.verification_work_units + 1)
        check = validate_block_action_provenance_proof_identity(result.proof, certificate, mutated)
        self.assertFalse(check.certified)
        self.assertEqual(check.status, "mismatched_block_action_provenance_proof_identity")

    def test_zero_envelope_constant_rejects_after_identity_replay(self):
        result = block_action_provenance_proof_dag_consumer(
            exact_certificate(), quasipoly_constant=0.0
        )
        self.assertFalse(result.certified)
        self.assertIsNotNone(result.dag_validation)
        self.assertEqual(result.dag_validation.status, "quasipolynomial_bound_exceeded")

    def test_trivial_generator_family_is_still_replay_stable(self):
        certificate = certify_group_block_action_equivariance(
            [[0, 1], [2, 3]],
            [[0, 1], [2, 3]],
            [0, 1],
            [],
            [],
        )
        result = block_action_provenance_proof_dag_consumer(certificate)
        self.assertTrue(result.certified)
        self.assertEqual(result.proof.proof_identity.source_generators, ())


if __name__ == "__main__":
    unittest.main()
