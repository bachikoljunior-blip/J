import unittest

from bounded_arity_relation_image_solver import BoundedArityRelationImage, RelationSpec
from bounded_relation_image_coset_v1 import _induced_permutation, _relation_signature
from implicit_relation_image_action_v1 import prepare_implicit_relation_image_action
from implicit_relation_image_value_coset_v1 import exact_implicit_relation_image_value_coset
from implicit_relation_image_preimage_coset_v1 import (
    exact_implicit_relation_image_preimage_coset,
)


def image(unary=(0,), binary=((0, 1),)):
    return BoundedArityRelationImage(
        (0, 1, 2),
        (
            RelationSpec("U", 1, tuple((x,) for x in unary)),
            RelationSpec("R", 2, binary),
        ),
    )


class ImplicitRelationImagePreimageCosetTests(unittest.TestCase):
    def test_s3_auxiliary_coset_lifts_to_complete_original_coset(self):
        source = image()
        target = image(unary=(2,), binary=((2, 0),))
        action = prepare_implicit_relation_image_action(
            source, target, ((1, 2, 0), (1, 0, 2))
        )
        image_result = exact_implicit_relation_image_value_coset(action)
        result = exact_implicit_relation_image_preimage_coset(action, image_result)

        self.assertEqual(result.status, "exact_original_domain_relation_preimage_coset")
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertIsNotNone(result.coset)
        self.assertTrue(action.domain_group.contains(result.representative))
        induced = _induced_permutation(
            result.representative, _relation_signature(source), len(source.domain)
        )
        self.assertEqual(induced, image_result.coset.representative)
        self.assertEqual(result.preimage_subgroup_order, image_result.coset.subgroup.order)

    def test_nontrivial_target_stabilizer_is_lifted_with_exact_order(self):
        symmetric = BoundedArityRelationImage(
            (0, 1, 2),
            (
                RelationSpec("U", 1, ()),
                RelationSpec("R", 2, ()),
            ),
        )
        action = prepare_implicit_relation_image_action(
            symmetric, symmetric, ((1, 2, 0), (1, 0, 2))
        )
        image_result = exact_implicit_relation_image_value_coset(action)
        result = exact_implicit_relation_image_preimage_coset(action, image_result)

        self.assertEqual(result.status, "exact_original_domain_relation_preimage_coset")
        self.assertEqual(image_result.coset.subgroup.order, 6)
        self.assertEqual(result.preimage_subgroup_order, 6)
        self.assertEqual(result.coset.subgroup.order, action.domain_group.order)

    def test_exact_empty_auxiliary_result_lifts_to_exact_empty(self):
        action = prepare_implicit_relation_image_action(
            image(),
            image(unary=(2,), binary=((2, 0),)),
            ((0, 1, 2),),
        )
        image_result = exact_implicit_relation_image_value_coset(action)
        self.assertTrue(image_result.exact)
        self.assertIsNone(image_result.coset)
        result = exact_implicit_relation_image_preimage_coset(action, image_result)
        self.assertEqual(result.status, "exact_empty_original_domain_relation_coset")
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertIsNone(result.coset)

    def test_unresolved_auxiliary_result_is_not_promoted(self):
        action = prepare_implicit_relation_image_action(
            image(),
            image(unary=(2,), binary=((2, 0),)),
            ((1, 2, 0), (1, 0, 2)),
        )
        image_result = exact_implicit_relation_image_value_coset(
            action, max_partition_states=1
        )
        self.assertFalse(image_result.exact)
        result = exact_implicit_relation_image_preimage_coset(action, image_result)
        self.assertEqual(result.status, "undetermined_original_preimage_image_coset")
        self.assertFalse(result.exact)
        self.assertFalse(result.complete)


if __name__ == "__main__":
    unittest.main()
