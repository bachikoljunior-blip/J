from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "2026-08-19_0851_JST"
if str(LEGACY) not in sys.path:
    sys.path.insert(0, str(LEGACY))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from homogeneous_block_action_kernel_v1 import certify_block_action_kernel_factorization
from homogeneous_block_action_provenance_v1 import certify_group_block_action_equivariance
from homogeneous_block_relation_provenance_v1 import build_structure, certify_homogeneous_block_transport
from homogeneous_block_joint_compatibility_proof_dag_v1 import (
    build_homogeneous_block_joint_compatibility_identity,
    homogeneous_block_joint_compatibility_proof_dag_consumer,
    validate_homogeneous_block_joint_compatibility_identity,
)


BLOCKS = ((0, 1), (2, 3))
WITHIN = (1, 0, 3, 2)
BLOCK_SWAP = (2, 3, 0, 1)


def fixture(*, relation_block_map=(1, 0), action_block_map=(1, 0), uniform_all=False):
    if uniform_all:
        source = build_structure(4, unary={"U": {0, 1, 2, 3}})
        target = build_structure(4, unary={"U": {0, 1, 2, 3}})
    else:
        source = build_structure(
            4,
            unary={"U": {0, 1}},
            binary={"R": {(u, v) for u in (0, 1) for v in (2, 3)}},
        )
        target = build_structure(
            4,
            unary={"U": {2, 3}},
            binary={"R": {(u, v) for u in (2, 3) for v in (0, 1)}},
        )
    relation = certify_homogeneous_block_transport(
        source, target, BLOCKS, BLOCKS, relation_block_map
    )
    action = certify_group_block_action_equivariance(
        BLOCKS,
        BLOCKS,
        action_block_map,
        (WITHIN, BLOCK_SWAP),
        (WITHIN, BLOCK_SWAP),
    )
    kernel = certify_block_action_kernel_factorization(
        action,
        max_domain_degree=16,
        max_block_count=16,
        max_generators=16,
        max_generator_point_checks=10_000_000,
    )
    assert relation.exact, relation.reason
    assert action.exact, action.reason
    assert kernel.exact, kernel.reason
    return source, target, relation, action, kernel


class Rev2000JointCompatibilityTests(unittest.TestCase):
    def test_certifies_three_main_integrated_contracts_without_si_promotion(self):
        source, target, relation, action, kernel = fixture()
        result = homogeneous_block_joint_compatibility_proof_dag_consumer(
            source, target, relation, action, kernel, root_n=8
        )
        self.assertTrue(result.certified, result.reason)
        self.assertEqual(
            result.status,
            "certified_homogeneous_block_joint_reduction_compatibility_proof_dag",
        )
        self.assertFalse(result.semantic_si_exactness_certified)
        self.assertIsNone(result.proof.coset)
        self.assertFalse(result.proof.exact)
        self.assertEqual(result.proof.proof_identity.block_map, (1, 0))
        self.assertEqual(result.proof.proof_identity.quotient_image_order, 2)
        self.assertEqual(result.proof.proof_identity.source_kernel_order, 2)

    def test_identity_is_deterministic_and_hashable(self):
        source, target, relation, action, kernel = fixture()
        left = build_homogeneous_block_joint_compatibility_identity(
            source, target, relation, action, kernel, root_n=8
        )
        right = build_homogeneous_block_joint_compatibility_identity(
            source, target, relation, action, kernel, root_n=8
        )
        self.assertEqual(left, right)
        self.assertEqual(hash(left), hash(right))
        self.assertTrue(left.relation_transcript_digest.startswith("sha256:"))

    def test_valid_but_different_relation_and_action_block_maps_fail_closed(self):
        source, target, relation, action, kernel = fixture(
            relation_block_map=(0, 1), action_block_map=(1, 0), uniform_all=True
        )
        result = homogeneous_block_joint_compatibility_proof_dag_consumer(
            source, target, relation, action, kernel
        )
        self.assertFalse(result.certified)
        self.assertIn("block map", result.reason)

    def test_valid_noncanonical_relation_block_order_does_not_alias_action_order(self):
        source = build_structure(4, unary={"U": {0, 1, 2, 3}})
        target = build_structure(4, unary={"U": {0, 1, 2, 3}})
        reversed_blocks = ((2, 3), (0, 1))
        relation = certify_homogeneous_block_transport(
            source, target, reversed_blocks, reversed_blocks, (0, 1)
        )
        action = certify_group_block_action_equivariance(
            BLOCKS, BLOCKS, (0, 1), (WITHIN,), (WITHIN,)
        )
        kernel = certify_block_action_kernel_factorization(
            action,
            max_domain_degree=16,
            max_block_count=16,
            max_generators=16,
            max_generator_point_checks=10_000_000,
        )
        result = homogeneous_block_joint_compatibility_proof_dag_consumer(
            source, target, relation, action, kernel
        )
        self.assertFalse(result.certified)
        self.assertIn("source partition", result.reason)

    def test_tampered_action_digest_fails_before_joint_identity(self):
        source, target, relation, action, kernel = fixture()
        bad_action = replace(action, certificate_digest="sha256:" + "0" * 64)
        result = homogeneous_block_joint_compatibility_proof_dag_consumer(
            source, target, relation, bad_action, kernel
        )
        self.assertFalse(result.certified)
        self.assertIn("action provenance", result.reason)

    def test_tampered_kernel_factorization_fails_closed(self):
        source, target, relation, action, kernel = fixture()
        bad_kernel = replace(kernel, quotient_image_order=kernel.quotient_image_order + 1)
        result = homogeneous_block_joint_compatibility_proof_dag_consumer(
            source, target, relation, action, bad_kernel
        )
        self.assertFalse(result.certified)
        self.assertIn("kernel factorization", result.reason)

    def test_tampered_relation_certificate_fails_replay(self):
        source, target, relation, action, kernel = fixture()
        bad_certificate = replace(relation.certificate, block_map=(0, 1))
        bad_relation = replace(relation, certificate=bad_certificate)
        result = homogeneous_block_joint_compatibility_proof_dag_consumer(
            source, target, bad_relation, action, kernel
        )
        self.assertFalse(result.certified)
        self.assertIn("does not replay exactly", result.reason)

    def test_joint_identity_tamper_is_detected_independently(self):
        source, target, relation, action, kernel = fixture()
        result = homogeneous_block_joint_compatibility_proof_dag_consumer(
            source, target, relation, action, kernel, root_n=8
        )
        self.assertTrue(result.certified, result.reason)
        expected = result.proof.proof_identity
        forged = replace(expected, action_provenance_digest="sha256:" + "1" * 64)
        forged_proof = replace(result.proof, proof_identity=forged)
        validation = validate_homogeneous_block_joint_compatibility_identity(
            forged_proof, source, target, relation, action, kernel, forged
        )
        self.assertFalse(validation.certified)
        self.assertIn("replay", validation.status)

    def test_original_root_must_dominate_domain(self):
        source, target, relation, action, kernel = fixture()
        result = homogeneous_block_joint_compatibility_proof_dag_consumer(
            source, target, relation, action, kernel, root_n=3
        )
        self.assertFalse(result.certified)
        self.assertIn("dominating", result.reason)

    def test_zero_quasipoly_envelope_rejects_accounting(self):
        source, target, relation, action, kernel = fixture()
        result = homogeneous_block_joint_compatibility_proof_dag_consumer(
            source,
            target,
            relation,
            action,
            kernel,
            root_n=8,
            quasipoly_constant=0.0,
        )
        self.assertFalse(result.certified)
        self.assertIsNotNone(result.dag_validation)
        self.assertFalse(result.dag_validation.certified)


if __name__ == "__main__":
    unittest.main()
