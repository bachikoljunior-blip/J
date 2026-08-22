import unittest
from dataclasses import dataclass

from bounded_arity_relation_image_solver import BoundedArityRelationImage, RelationSpec
from bounded_relation_image_coset_v1 import _induced_permutation, _relation_signature
from coset_stabilizer_primitives import RightCoset
from implicit_relation_image_action_v1 import prepare_implicit_relation_image_action
from implicit_relation_image_preimage_coset_v2 import (
    exact_implicit_relation_image_preimage_coset,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


@dataclass(frozen=True)
class ImageResult:
    status: str
    exact: bool
    complete: bool
    auxiliary_degree: int
    coset: RightCoset | None


def image(*, domain=(0, 1, 2), unary=(), binary=()):
    return BoundedArityRelationImage(
        tuple(domain),
        (
            RelationSpec("U", 1, tuple((x,) for x in unary)),
            RelationSpec("R", 2, tuple(binary)),
        ),
    )


def exact_action():
    symmetric = image()
    return symmetric, prepare_implicit_relation_image_action(
        symmetric,
        symmetric,
        ((1, 2, 0), (1, 0, 2)),
    )


def auxiliary(action, source, permutation):
    return _induced_permutation(
        permutation,
        _relation_signature(source),
        action.domain_degree,
    )


class ImplicitRelationImagePreimageCosetRev267Tests(unittest.TestCase):
    def test_singleton_image_coset_lifts_without_group_enumeration(self):
        source, action = exact_action()
        cycle = (1, 2, 0)
        image_cycle = auxiliary(action, source, cycle)
        subgroup = schreier_stabilizer_chain((identity(action.auxiliary_degree),))
        image_result = ImageResult(
            "exact_implicit_relation_image_value_coset",
            True,
            True,
            action.auxiliary_degree,
            RightCoset(subgroup, image_cycle),
        )

        result = exact_implicit_relation_image_preimage_coset(action, image_result)

        self.assertEqual(result.status, "exact_original_domain_relation_preimage_coset")
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertEqual(result.preimage_subgroup_order, 1)
        self.assertEqual(
            auxiliary(action, source, result.representative),
            image_cycle,
        )
        self.assertTrue(result.coset.contains(result.representative))
        self.assertTrue(action.domain_group.contains(result.representative))

    def test_full_image_subgroup_lifts_to_full_domain_group(self):
        source, action = exact_action()
        image_result = ImageResult(
            "exact_implicit_relation_image_value_coset",
            True,
            True,
            action.auxiliary_degree,
            RightCoset(action.image_group, identity(action.auxiliary_degree)),
        )

        result = exact_implicit_relation_image_preimage_coset(action, image_result)

        self.assertEqual(action.domain_group.order, 6)
        self.assertEqual(action.image_group.order, 6)
        self.assertEqual(result.image_subgroup_order, 6)
        self.assertEqual(result.preimage_subgroup_order, 6)
        self.assertEqual(result.subgroup.order, action.domain_group.order)

    def test_exact_empty_image_contract_lifts_to_exact_empty(self):
        _source, action = exact_action()
        image_result = ImageResult(
            "exact_empty_implicit_image_value_coset",
            True,
            True,
            action.auxiliary_degree,
            None,
        )

        result = exact_implicit_relation_image_preimage_coset(action, image_result)

        self.assertEqual(result.status, "exact_empty_original_domain_relation_coset")
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertIsNone(result.coset)

    def test_rev257_exact_empty_requires_compatible_empty_image_evidence(self):
        source = image(domain=(0, 1, 2))
        target = image(domain=(0, 1))
        action = prepare_implicit_relation_image_action(source, target, ((0, 1, 2),))
        compatible = ImageResult(
            action.status,
            True,
            True,
            action.auxiliary_degree,
            None,
        )
        result = exact_implicit_relation_image_preimage_coset(action, compatible)
        self.assertEqual(result.status, "exact_empty_original_domain_relation_coset")

        contradictory = ImageResult(
            "undetermined_image_value_partition_transporter",
            False,
            False,
            action.auxiliary_degree,
            None,
        )
        result = exact_implicit_relation_image_preimage_coset(action, contradictory)
        self.assertEqual(
            result.status,
            "undetermined_original_preimage_contradictory_exact_evidence",
        )
        self.assertFalse(result.exact)

    def test_incomplete_image_result_is_not_promoted(self):
        _source, action = exact_action()
        image_result = ImageResult(
            "undetermined_image_value_partition_orbit_limit",
            False,
            False,
            action.auxiliary_degree,
            None,
        )
        result = exact_implicit_relation_image_preimage_coset(action, image_result)
        self.assertEqual(result.status, "undetermined_original_preimage_image_coset")
        self.assertFalse(result.exact)
        self.assertFalse(result.complete)

    def test_nonempty_result_must_use_rev262_exact_contract_status(self):
        _source, action = exact_action()
        image_result = ImageResult(
            "forged_exact_coset",
            True,
            True,
            action.auxiliary_degree,
            RightCoset(action.image_group, identity(action.auxiliary_degree)),
        )
        result = exact_implicit_relation_image_preimage_coset(action, image_result)
        self.assertEqual(
            result.status,
            "undetermined_original_preimage_image_coset_contract",
        )

    def test_image_result_auxiliary_degree_mismatch_fails_closed(self):
        _source, action = exact_action()
        image_result = ImageResult(
            "exact_empty_implicit_image_value_coset",
            True,
            True,
            action.auxiliary_degree + 1,
            None,
        )
        with self.assertRaises(ValueError):
            exact_implicit_relation_image_preimage_coset(action, image_result)

    def test_image_representative_outside_exact_image_group_is_rejected(self):
        _source, action = exact_action()
        forged = list(range(action.auxiliary_degree))
        forged[3], forged[4] = forged[4], forged[3]
        forged = tuple(forged)
        self.assertFalse(action.image_group.contains(forged))
        subgroup = schreier_stabilizer_chain((identity(action.auxiliary_degree),))
        image_result = ImageResult(
            "exact_implicit_relation_image_value_coset",
            True,
            True,
            action.auxiliary_degree,
            RightCoset(subgroup, forged),
        )
        with self.assertRaises(AssertionError):
            exact_implicit_relation_image_preimage_coset(action, image_result)

    def test_image_subgroup_generator_outside_exact_image_group_is_rejected(self):
        _source, action = exact_action()
        forged = list(range(action.auxiliary_degree))
        forged[3], forged[4] = forged[4], forged[3]
        forged_subgroup = schreier_stabilizer_chain((tuple(forged),))
        image_result = ImageResult(
            "exact_implicit_relation_image_value_coset",
            True,
            True,
            action.auxiliary_degree,
            RightCoset(forged_subgroup, identity(action.auxiliary_degree)),
        )
        with self.assertRaises(AssertionError):
            exact_implicit_relation_image_preimage_coset(action, image_result)


if __name__ == "__main__":
    unittest.main()
