import unittest
from itertools import permutations

from bounded_arity_relation_image_solver import BoundedArityRelationImage, RelationSpec
from bounded_group_transport import enumerate_group
from implicit_relation_image_action_v1 import prepare_implicit_relation_image_action
from implicit_relation_image_value_coset_v2 import (
    exact_implicit_relation_image_value_coset,
)


def image(unary=(0,), binary=((0, 1),)):
    return BoundedArityRelationImage(
        (0, 1, 2),
        (
            RelationSpec("U", 1, tuple((x,) for x in unary)),
            RelationSpec("R", 2, binary),
        ),
    )


def transports(action, permutation):
    return all(
        action.source_features[i] == action.target_features[permutation[i]]
        for i in range(action.auxiliary_degree)
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
        elements = enumerate_group(action.image_group, max_elements=100)
        self.assertIsNotNone(elements)
        expected = {g for g in elements if transports(action, g)}
        actual = {g for g in elements if result.coset.contains(g)}
        self.assertEqual(actual, expected)
        self.assertEqual(result.coset.subgroup.order, len(expected))

    def test_all_s3_relation_relabellings_match_complete_enumeration(self):
        source = image()
        generators = ((1, 2, 0), (1, 0, 2))
        for permutation in permutations(range(3)):
            with self.subTest(permutation=permutation):
                target = image(
                    unary=(permutation[0],),
                    binary=((permutation[0], permutation[1]),),
                )
                action = prepare_implicit_relation_image_action(
                    source, target, generators
                )
                result = exact_implicit_relation_image_value_coset(action)
                self.assertEqual(
                    result.status, "exact_implicit_relation_image_value_coset"
                )
                elements = enumerate_group(action.image_group, max_elements=100)
                expected = {g for g in elements if transports(action, g)}
                actual = {g for g in elements if result.coset.contains(g)}
                self.assertEqual(actual, expected)
                self.assertEqual(result.coset.subgroup.order, len(expected))

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

    def test_partition_state_cap_fails_closed_before_exact_promotion(self):
        action = prepare_implicit_relation_image_action(
            image(),
            image(unary=(2,), binary=((2, 0),)),
            ((1, 2, 0), (1, 0, 2)),
        )
        result = exact_implicit_relation_image_value_coset(
            action, max_partition_states=1
        )
        self.assertEqual(
            result.status, "undetermined_image_value_partition_orbit_limit"
        )
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

    def test_invalid_partition_cap_is_rejected(self):
        action = prepare_implicit_relation_image_action(
            image(), image(), ((0, 1, 2),)
        )
        for bad in (True, 0, -1, 1.5):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    exact_implicit_relation_image_value_coset(
                        action, max_partition_states=bad
                    )


if __name__ == "__main__":
    unittest.main()
