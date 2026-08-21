import unittest
from dataclasses import replace

from bounded_arity_relation_image_solver import BoundedArityRelationImage, RelationSpec
from implicit_relation_image_action_v1 import prepare_implicit_relation_image_action
from implicit_image_value_proof_dag_consumer_v1 import (
    implicit_image_value_proof_dag_consumer,
    validate_implicit_image_value_identity,
)


def binary_image(binary=((0, 1),)):
    return BoundedArityRelationImage(
        (0, 1, 2),
        (RelationSpec("R", 2, binary),),
    )


def unary_binary_image():
    return BoundedArityRelationImage(
        (0, 1, 2),
        (
            RelationSpec("U", 1, ((0,),)),
            RelationSpec("R", 2, ((0, 1),)),
        ),
    )


class ImplicitImageValueProofDAGConsumerTests(unittest.TestCase):
    def test_exact_nonempty_rev262_phase_enters_shared_proof_dag(self):
        action = prepare_implicit_relation_image_action(
            binary_image(),
            binary_image(binary=((2, 0),)),
            ((1, 2, 0), (1, 0, 2)),
        )
        result = implicit_image_value_proof_dag_consumer(
            action, original_root_n=3
        )
        self.assertEqual(result.status, "certified_implicit_image_value_proof_dag")
        self.assertTrue(result.value_coset.exact)
        self.assertTrue(result.value_coset.complete)
        self.assertIsNotNone(result.value_coset.coset)
        self.assertTrue(result.identity_validation.certified)
        self.assertTrue(result.dag_validation.certified)
        self.assertEqual(result.proof.proof_identity.auxiliary_degree, 12)

    def test_exact_empty_rev262_phase_is_also_a_certified_terminal(self):
        action = prepare_implicit_relation_image_action(
            binary_image(),
            binary_image(binary=((2, 0),)),
            ((0, 1, 2),),
        )
        result = implicit_image_value_proof_dag_consumer(
            action, original_root_n=3
        )
        self.assertEqual(result.status, "certified_implicit_image_value_proof_dag")
        self.assertEqual(
            result.value_coset.status, "exact_empty_implicit_image_value_coset"
        )
        self.assertIsNone(result.value_coset.coset)
        self.assertTrue(result.dag_validation.certified)

    def test_partition_cap_remains_nonexact_and_identity_free(self):
        action = prepare_implicit_relation_image_action(
            binary_image(),
            binary_image(binary=((2, 0),)),
            ((1, 2, 0), (1, 0, 2)),
        )
        result = implicit_image_value_proof_dag_consumer(
            action, original_root_n=3, max_partition_states=1
        )
        self.assertEqual(
            result.status, "underlying_implicit_image_value_phase_not_exact"
        )
        self.assertFalse(result.value_coset.exact)
        self.assertIsNone(result.proof)
        self.assertIsNone(result.dag_validation)

    def test_identity_tamper_is_detected_independently(self):
        action = prepare_implicit_relation_image_action(
            binary_image(), binary_image(), ((1, 2, 0), (1, 0, 2))
        )
        result = implicit_image_value_proof_dag_consumer(
            action, original_root_n=3
        )
        expected = result.proof.proof_identity
        tampered = replace(
            result.proof,
            proof_identity=replace(expected, original_root_n=4),
        )
        validation = validate_implicit_image_value_identity(tampered, expected)
        self.assertFalse(validation.certified)
        self.assertEqual(
            validation.status, "mismatched_implicit_image_value_proof_identity"
        )

    def test_opaque_feature_identity_fails_closed_before_execution(self):
        action = prepare_implicit_relation_image_action(
            binary_image(), binary_image(), ((0, 1, 2),)
        )
        opaque = replace(
            action,
            source_features=(object(),) + action.source_features[1:],
        )
        result = implicit_image_value_proof_dag_consumer(
            opaque, original_root_n=3
        )
        self.assertEqual(
            result.status, "unstable_opaque_implicit_image_value_identity"
        )
        self.assertIsNone(result.value_coset)
        self.assertIsNone(result.proof)

    def test_auxiliary_lift_above_n_plus_n_squared_is_rejected(self):
        action = prepare_implicit_relation_image_action(
            unary_binary_image(), unary_binary_image(), ((0, 1, 2),)
        )
        self.assertGreater(action.auxiliary_degree, 3 + 3 * 3)
        with self.assertRaises(ValueError):
            implicit_image_value_proof_dag_consumer(action, original_root_n=3)

    def test_quasipolynomial_envelope_failure_stays_uncertified(self):
        action = prepare_implicit_relation_image_action(
            binary_image(), binary_image(), ((0, 1, 2),)
        )
        result = implicit_image_value_proof_dag_consumer(
            action,
            original_root_n=3,
            quasipoly_constant=0.000001,
        )
        self.assertEqual(
            result.status, "proof_dag_quasipolynomial_envelope_exceeded"
        )
        self.assertFalse(result.dag_validation.certified)


if __name__ == "__main__":
    unittest.main()
