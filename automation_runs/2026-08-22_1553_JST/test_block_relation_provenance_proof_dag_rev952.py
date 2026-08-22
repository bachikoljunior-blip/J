import dataclasses
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
LEGACY = HERE.parent / "2026-08-19_0851_JST"
for path in (HERE, LEGACY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from block_relation_provenance_proof_dag_consumer_v1 import (
    block_relation_provenance_proof_dag_consumer,
    build_block_relation_provenance_proof_identity,
    validate_block_relation_provenance_proof_identity,
)
from homogeneous_block_relation_provenance_v1 import (
    BlockProvenanceResult,
    build_structure,
    certify_homogeneous_block_transport,
)


class BlockRelationProvenanceProofDAGRev952Test(unittest.TestCase):
    partition = ((0, 1), (2, 3))

    def exact_fixture(self):
        source = build_structure(
            4,
            unary={"red": (0, 1)},
            binary={"arc": ((0, 2), (0, 3), (1, 2), (1, 3))},
        )
        target = build_structure(
            4,
            unary={"red": (2, 3)},
            binary={"arc": ((2, 0), (2, 1), (3, 0), (3, 1))},
        )
        result = certify_homogeneous_block_transport(
            source,
            target,
            self.partition,
            self.partition,
            (1, 0),
        )
        self.assertTrue(result.exact, result.reason)
        self.assertIsNotNone(result.certificate)
        return source, target, result

    def test_exact_rev273_provenance_is_admitted_to_shared_proof_dag(self):
        source, target, result = self.exact_fixture()
        admitted = block_relation_provenance_proof_dag_consumer(source, target, result)
        self.assertEqual(
            admitted.status,
            "certified_homogeneous_block_relation_provenance_proof_dag",
        )
        self.assertTrue(admitted.certified)
        self.assertTrue(admitted.identity_validation.certified)
        self.assertTrue(admitted.dag_validation.certified)
        self.assertEqual(admitted.proof.domain_size, 4)
        self.assertEqual(admitted.proof.proof_identity.block_count, 2)
        self.assertEqual(admitted.proof.proof_identity.unary_relation_count, 1)
        self.assertEqual(admitted.proof.proof_identity.binary_relation_count, 1)
        self.assertGreater(admitted.proof.proof_identity.verification_work_units, 0)

    def test_identity_binds_full_relation_and_certificate_transcripts(self):
        source, target, result = self.exact_fixture()
        identity = build_block_relation_provenance_proof_identity(source, target, result)
        self.assertEqual(identity.source_identity[0], 4)
        self.assertEqual(identity.target_identity[0], 4)
        self.assertEqual(identity.certificate_identity[0], self.partition)
        self.assertEqual(identity.certificate_identity[2], (1, 0))
        self.assertEqual(identity.certificate_identity[3], (2, 3, 0, 1))
        self.assertTrue(identity.replay_stable)
        hash(identity)

    def test_larger_original_root_is_preserved(self):
        source, target, result = self.exact_fixture()
        admitted = block_relation_provenance_proof_dag_consumer(
            source, target, result, root_n=16
        )
        self.assertTrue(admitted.certified)
        self.assertEqual(admitted.proof.root_n, 16)
        self.assertEqual(admitted.proof.accounting.n, 16)
        self.assertEqual(admitted.proof.accounting.m, 4)

    def test_root_smaller_than_relation_domain_fails_closed(self):
        source, target, result = self.exact_fixture()
        admitted = block_relation_provenance_proof_dag_consumer(
            source, target, result, root_n=3
        )
        self.assertFalse(admitted.certified)
        self.assertEqual(admitted.status, "rejected_block_relation_provenance_identity")
        self.assertIn("dominating", admitted.reason)

    def test_nonexact_rev273_outcome_is_not_promoted(self):
        source, target, _ = self.exact_fixture()
        bad = BlockProvenanceResult(False, "caller_nonexact", None)
        admitted = block_relation_provenance_proof_dag_consumer(source, target, bad)
        self.assertFalse(admitted.certified)
        self.assertIn("only exact", admitted.reason)

    def test_tampered_result_reason_breaks_exact_replay(self):
        source, target, result = self.exact_fixture()
        tampered = dataclasses.replace(result, reason="tampered")
        admitted = block_relation_provenance_proof_dag_consumer(source, target, tampered)
        self.assertFalse(admitted.certified)
        self.assertIn("does not replay", admitted.reason)

    def test_tampered_point_lift_breaks_exact_replay(self):
        source, target, result = self.exact_fixture()
        certificate = dataclasses.replace(
            result.certificate,
            point_map=(0, 1, 2, 3),
        )
        tampered = dataclasses.replace(result, certificate=certificate)
        admitted = block_relation_provenance_proof_dag_consumer(source, target, tampered)
        self.assertFalse(admitted.certified)
        self.assertIn("does not replay", admitted.reason)

    def test_terminal_payload_tamper_is_rejected_by_identity_validator(self):
        source, target, result = self.exact_fixture()
        admitted = block_relation_provenance_proof_dag_consumer(source, target, result)
        self.assertTrue(admitted.certified)
        proof = dataclasses.replace(
            admitted.proof,
            permutation_candidates_checked=admitted.proof.permutation_candidates_checked + 1,
        )
        validation = validate_block_relation_provenance_proof_identity(
            proof,
            source,
            target,
            result,
            admitted.proof.proof_identity,
        )
        self.assertFalse(validation.certified)
        self.assertEqual(validation.status, "inconsistent_block_relation_terminal_payload")

    def test_accounting_tamper_is_rejected_by_identity_validator(self):
        source, target, result = self.exact_fixture()
        admitted = block_relation_provenance_proof_dag_consumer(source, target, result)
        self.assertTrue(admitted.certified)
        accounting = dataclasses.replace(
            admitted.proof.accounting,
            terminal_certified=False,
        )
        proof = dataclasses.replace(admitted.proof, accounting=accounting)
        validation = validate_block_relation_provenance_proof_identity(
            proof,
            source,
            target,
            result,
            admitted.proof.proof_identity,
        )
        self.assertFalse(validation.certified)
        self.assertEqual(validation.status, "inconsistent_block_relation_accounting")

    def test_same_empty_relation_structure_remains_certifiable(self):
        source = build_structure(4)
        target = build_structure(4)
        result = certify_homogeneous_block_transport(
            source,
            target,
            self.partition,
            self.partition,
            (0, 1),
        )
        self.assertTrue(result.exact, result.reason)
        admitted = block_relation_provenance_proof_dag_consumer(source, target, result)
        self.assertTrue(admitted.certified)
        self.assertEqual(admitted.proof.proof_identity.unary_relation_count, 0)
        self.assertEqual(admitted.proof.proof_identity.binary_relation_count, 0)


if __name__ == "__main__":
    unittest.main()
