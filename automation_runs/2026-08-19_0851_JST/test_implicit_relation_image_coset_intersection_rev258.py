import unittest
from unittest.mock import patch

from bounded_arity_relation_image_solver import BoundedArityRelationImage, RelationSpec
from implicit_relation_image_coset_intersection_v1 import (
    exact_implicit_relation_image_coset_intersection,
)


def image(unary=(0,), binary=((0, 1),)):
    return BoundedArityRelationImage(
        (0, 1, 2),
        (
            RelationSpec("U", 1, tuple((x,) for x in unary)),
            RelationSpec("R", 2, binary),
        ),
    )


class ImplicitRelationImageCosetIntersectionTests(unittest.TestCase):
    def test_s3_relabeling_returns_complete_exact_image_coset(self):
        result = exact_implicit_relation_image_coset_intersection(
            image(),
            image(unary=(2,), binary=((2, 0),)),
            ((1, 2, 0), (1, 0, 2)),
        )
        self.assertEqual(result.status, "exact_implicit_image_value_coset_intersection")
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertIsNotNone(result.coset)
        self.assertEqual(result.action.domain_group.order, 6)
        self.assertEqual(result.action.image_group.order, 6)

    def test_value_multiplicity_mismatch_is_exact_empty_inside_image(self):
        result = exact_implicit_relation_image_coset_intersection(
            image(unary=(0,)),
            image(unary=(0, 1)),
            ((1, 2, 0), (1, 0, 2)),
        )
        self.assertEqual(result.status, "exact_empty_implicit_image_value_coset")
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertIsNone(result.coset)

    def test_signature_mismatch_short_circuits_as_exact_empty(self):
        target = BoundedArityRelationImage(
            (0, 1, 2), (RelationSpec("different", 1, ((0,),)),)
        )
        result = exact_implicit_relation_image_coset_intersection(
            image(), target, ((1, 2, 0),)
        )
        self.assertEqual(result.status, "exact_empty_relation_signature_mismatch")
        self.assertTrue(result.exact)
        self.assertIsNone(result.proof)

    def test_action_cap_fails_closed_before_u2(self):
        with patch(
            "implicit_relation_image_coset_intersection_v1.candidate_coset_string_isomorphism_u2",
            side_effect=AssertionError("U2 must not start"),
        ):
            result = exact_implicit_relation_image_coset_intersection(
                image(), image(), ((1, 2, 0),), max_auxiliary_degree=14
            )
        self.assertEqual(result.status, "undetermined_implicit_relation_image_action")
        self.assertFalse(result.exact)
        self.assertIsNone(result.proof)

    def test_unresolved_u2_is_not_promoted(self):
        class Stub:
            exact = False
            coset = None
            reason = "forced unresolved"

        with patch(
            "implicit_relation_image_coset_intersection_v1.candidate_coset_string_isomorphism_u2",
            return_value=Stub(),
        ):
            result = exact_implicit_relation_image_coset_intersection(
                image(), image(), ((1, 2, 0),)
            )
        self.assertEqual(result.status, "undetermined_implicit_image_value_coset_intersection")
        self.assertFalse(result.exact)
        self.assertFalse(result.complete)


if __name__ == "__main__":
    unittest.main()
