import unittest
from unittest.mock import patch

from bounded_arity_relation_image_solver import BoundedArityRelationImage, RelationSpec
from implicit_relation_image_action_v1 import prepare_implicit_relation_image_action


def image(unary=(0,), binary=((0, 1),)):
    return BoundedArityRelationImage(
        (0, 1, 2),
        (
            RelationSpec("U", 1, tuple((x,) for x in unary)),
            RelationSpec("R", 2, binary),
        ),
    )


class ImplicitRelationImageActionTests(unittest.TestCase):
    def test_s3_action_is_faithful_without_group_enumeration(self):
        result = prepare_implicit_relation_image_action(
            image(),
            image(unary=(2,), binary=((2, 0),)),
            ((1, 2, 0), (1, 0, 2)),
        )
        self.assertEqual(result.status, "exact_implicit_relation_image_paired_action")
        self.assertEqual(result.auxiliary_degree, 15)
        self.assertEqual(result.domain_group.order, 6)
        self.assertEqual(result.image_group.order, 6)
        self.assertEqual(result.kernel.order, 1)
        self.assertEqual(len(result.image_generators), 2)
        self.assertNotEqual(result.source_features, result.target_features)

    def test_trivial_group_uses_identity_generator(self):
        result = prepare_implicit_relation_image_action(
            image(), image(), ((0, 1, 2),)
        )
        self.assertEqual(result.domain_group.order, 1)
        self.assertEqual(result.image_group.order, 1)
        self.assertEqual(result.kernel.order, 1)

    def test_cap_rejects_before_induced_generator_materialization(self):
        with patch(
            "implicit_relation_image_action_v1._induced_permutation",
            side_effect=AssertionError("must not materialize"),
        ):
            result = prepare_implicit_relation_image_action(
                image(), image(), ((1, 2, 0),), max_auxiliary_degree=14
            )
        self.assertEqual(result.status, "undetermined_auxiliary_degree_cap")
        self.assertIsNone(result.image_group)

    def test_signature_mismatch_is_exact_empty(self):
        target = BoundedArityRelationImage(
            (0, 1, 2), (RelationSpec("different", 1, ((0,),)),)
        )
        result = prepare_implicit_relation_image_action(
            image(), target, ((1, 2, 0),)
        )
        self.assertEqual(result.status, "exact_empty_relation_signature_mismatch")

    def test_generator_degree_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "degree mismatch"):
            prepare_implicit_relation_image_action(image(), image(), ((1, 0),))


if __name__ == "__main__":
    unittest.main()
