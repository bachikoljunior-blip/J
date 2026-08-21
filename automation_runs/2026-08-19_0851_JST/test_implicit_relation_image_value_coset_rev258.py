import unittest

from bounded_arity_relation_image_solver import BoundedArityRelationImage, RelationSpec
from implicit_relation_image_action_v1 import prepare_implicit_relation_image_action
from implicit_relation_image_value_coset_v1 import exact_implicit_relation_image_value_coset


def image(unary=(0,), binary=((0, 1),)):
    return BoundedArityRelationImage(
        (0, 1, 2),
        (
            RelationSpec("U", 1, tuple((x,) for x in unary)),
            RelationSpec("R", 2, binary),
        ),
    )


class ImplicitRelationImageValueCosetTests(unittest.TestCase):
    def test_s3_implicit_image_returns_complete_nonempty_coset(self):
        action = prepare_implicit_relation_image_action(
            image(),
            image(unary=(2,), binary=((2, 0),)),
            ((1, 2, 0), (1, 0, 2)),
        )
        result = exact_implicit_relation_image_value_coset(action)
        self.assertEqual(result.status, "exact_implicit_relation_image_value_coset")
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertIsNotNone(result.coset)
        r = result.coset.representative
        self.assertTrue(action.image_group.contains(r))
        self.assertTrue(all(
            action.source_features[i] == action.target_features[r[i]]
            for i in range(action.auxiliary_degree)
        ))
        self.assertEqual(result.coset.subgroup.order, 1)

    def test_trivial_implicit_group_proves_empty_for_relabelled_relation(self):
        action = prepare_implicit_relation_image_action(
            image(),
            image(unary=(2,), binary=((2, 0),)),
            ((0, 1, 2),),
        )
        result = exact_implicit_relation_image_value_coset(action)
        self.assertEqual(result.status, "exact_empty_implicit_image_value_coset")
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertIsNone(result.coset)

    def test_partition_state_cap_fails_closed(self):
        action = prepare_implicit_relation_image_action(
            image(),
            image(unary=(2,), binary=((2, 0),)),
            ((1, 2, 0), (1, 0, 2)),
        )
        result = exact_implicit_relation_image_value_coset(
            action, max_partition_states=1
        )
        self.assertEqual(result.status, "undetermined_image_value_partition_orbit_limit")
        self.assertFalse(result.exact)
        self.assertFalse(result.complete)
        self.assertIsNone(result.coset)

    def test_exact_empty_rev257_status_is_preserved(self):
        target = BoundedArityRelationImage(
            (0, 1, 2), (RelationSpec("different", 1, ((0,),)),)
        )
        action = prepare_implicit_relation_image_action(
            image(), target, ((1, 2, 0),)
        )
        result = exact_implicit_relation_image_value_coset(action)
        self.assertEqual(result.status, "exact_empty_relation_signature_mismatch")
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)


if __name__ == "__main__":
    unittest.main()
