import unittest
from unittest.mock import Mock

from coset_stabilizer_primitives import RightCoset
from implicit_relation_image_preimage_differential_v1 import (
    verify_paired_action_coset_preimage_differential,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def s3():
    return schreier_stabilizer_chain(
        ((1, 2, 0), (1, 0, 2))
    )


def singleton_coset(degree, representative):
    trivial = schreier_stabilizer_chain((identity(degree),))
    return RightCoset(trivial, representative)


class PairedActionPreimageDifferentialTests(unittest.TestCase):
    def test_unique_nonidentity_s3_transporter_agrees(self):
        group = s3()
        images = tuple(group.original_generators)
        representative = (1, 2, 0)
        result = verify_paired_action_coset_preimage_differential(
            group,
            images,
            singleton_coset(3, representative),
            image_of=lambda g: g,
            direct_accepts=lambda _g, q: q == representative,
        )
        self.assertTrue(result.accepted)
        self.assertEqual(
            result.status,
            "verified_paired_action_coset_preimage_differential",
        )
        self.assertEqual(result.elements_checked, 6)
        self.assertEqual(
            (
                result.direct_match_count,
                result.image_match_count,
                result.preimage_match_count,
                result.distinct_image_match_count,
            ),
            (1, 1, 1, 1),
        )

    def test_full_s3_coset_agrees(self):
        group = s3()
        images = tuple(group.original_generators)
        result = verify_paired_action_coset_preimage_differential(
            group,
            images,
            RightCoset(group, identity(3)),
            image_of=lambda g: g,
            direct_accepts=lambda _g, _q: True,
        )
        self.assertTrue(result.accepted)
        self.assertEqual(
            (
                result.direct_match_count,
                result.image_match_count,
                result.preimage_match_count,
                result.distinct_image_match_count,
            ),
            (6, 6, 6, 6),
        )

    def test_nonfaithful_trivial_action_replays_kernel_fibers(self):
        group = s3()
        images = tuple((0,) for _ in group.original_generators)
        target = singleton_coset(1, (0,))
        result = verify_paired_action_coset_preimage_differential(
            group,
            images,
            target,
            image_of=lambda _g: (0,),
            direct_accepts=lambda _g, _q: True,
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.image_order, 1)
        self.assertEqual(result.kernel_order, 6)
        self.assertEqual(result.preimage_match_count, 6)
        self.assertEqual(result.distinct_image_match_count, 1)

    def test_exact_empty_replays_without_preimage(self):
        group = s3()
        images = tuple(group.original_generators)
        result = verify_paired_action_coset_preimage_differential(
            group,
            images,
            None,
            image_of=lambda g: g,
            direct_accepts=lambda _g, _q: False,
            exact_empty=True,
        )
        self.assertTrue(result.accepted)
        self.assertEqual(
            result.status,
            "verified_exact_empty_paired_action_preimage_differential",
        )
        self.assertEqual(result.preimage_match_count, 0)

    def test_order_cap_rejects_before_callbacks(self):
        group = s3()
        image_of = Mock(side_effect=AssertionError("must not evaluate image"))
        direct = Mock(side_effect=AssertionError("must not evaluate semantics"))
        result = verify_paired_action_coset_preimage_differential(
            group,
            tuple(group.original_generators),
            RightCoset(group, identity(3)),
            image_of=image_of,
            direct_accepts=direct,
            max_group_order=5,
        )
        self.assertFalse(result.accepted)
        self.assertEqual(
            result.status,
            "undetermined_differential_group_order_cap",
        )
        image_of.assert_not_called()
        direct.assert_not_called()

    def test_forged_equal_cardinality_coset_is_detected_as_set_mismatch(self):
        group = s3()
        images = tuple(group.original_generators)
        direct_representative = (1, 2, 0)
        forged_representative = (2, 0, 1)
        result = verify_paired_action_coset_preimage_differential(
            group,
            images,
            singleton_coset(3, forged_representative),
            image_of=lambda g: g,
            direct_accepts=lambda _g, q: q == direct_representative,
        )
        self.assertFalse(result.accepted)
        self.assertEqual(
            result.status,
            "differential_direct_image_coset_mismatch",
        )
        self.assertEqual(
            (result.direct_match_count, result.image_match_count),
            (1, 1),
        )

    def test_generator_pairing_mismatch_is_detected(self):
        group = s3()
        images = tuple(group.original_generators)
        forged = list(images)
        forged[0] = identity(3)
        result = verify_paired_action_coset_preimage_differential(
            group,
            tuple(forged),
            singleton_coset(3, identity(3)),
            image_of=lambda g: g,
            direct_accepts=lambda _g, q: q == identity(3),
        )
        self.assertFalse(result.accepted)
        self.assertIn(
            result.status,
            {
                "differential_action_image_outside_generated_group",
                "differential_generator_pairing_mismatch",
            },
        )

    def test_incomplete_or_contradictory_image_result_fails_closed(self):
        group = s3()
        images = tuple(group.original_generators)
        result = verify_paired_action_coset_preimage_differential(
            group,
            images,
            None,
            image_of=lambda g: g,
            direct_accepts=lambda _g, _q: False,
            complete_image_result=False,
        )
        self.assertEqual(
            result.status,
            "undetermined_differential_requires_complete_image_result",
        )
        with self.assertRaisesRegex(ValueError, "contradicts"):
            verify_paired_action_coset_preimage_differential(
                group,
                images,
                RightCoset(group, identity(3)),
                image_of=lambda g: g,
                direct_accepts=lambda _g, _q: True,
                exact_empty=True,
            )

    def test_invalid_limits_and_callbacks_are_rejected(self):
        group = s3()
        images = tuple(group.original_generators)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            verify_paired_action_coset_preimage_differential(
                group,
                images,
                RightCoset(group, identity(3)),
                image_of=lambda g: g,
                direct_accepts=lambda _g, _q: True,
                max_group_order=0,
            )
        with self.assertRaisesRegex(TypeError, "callable"):
            verify_paired_action_coset_preimage_differential(
                group,
                images,
                RightCoset(group, identity(3)),
                image_of=None,
                direct_accepts=lambda _g, _q: True,
            )


if __name__ == "__main__":
    unittest.main()
