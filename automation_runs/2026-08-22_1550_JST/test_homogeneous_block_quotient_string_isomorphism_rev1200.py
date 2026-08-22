from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "2026-08-19_0851_JST"
if str(LEGACY) not in sys.path:
    sys.path.insert(0, str(LEGACY))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from homogeneous_block_action_kernel_v1 import certify_block_action_kernel_factorization
from homogeneous_block_action_provenance_v1 import certify_group_block_action_equivariance
from homogeneous_block_quotient_string_isomorphism_v1 import (
    STATUS_EMPTY_INVENTORY,
    STATUS_EMPTY_ORBIT,
    STATUS_EXACT,
    STATUS_FAIL,
    STATUS_UNDETERMINED_LIMIT,
    exact_homogeneous_block_quotient_string_isomorphism,
)
from permutation_group_schreier import identity


SWAP_BLOCKS = (2, 3, 0, 1)


def paired_provenance(*, block_bijection=(0, 1), with_swap=True):
    generators = (SWAP_BLOCKS,) if with_swap else ()
    provenance = certify_group_block_action_equivariance(
        ((0, 1), (2, 3)),
        ((0, 1), (2, 3)),
        block_bijection,
        generators,
        generators,
    )
    if not provenance.exact:
        raise AssertionError(provenance.reason)
    factorization = certify_block_action_kernel_factorization(provenance)
    if not factorization.exact:
        raise AssertionError(factorization.reason)
    return provenance, factorization


class Rev1200HomogeneousBlockQuotientStringIsomorphismTests(unittest.TestCase):
    def test_exact_swap_returns_complete_target_right_coset(self):
        provenance, factorization = paired_provenance()
        result = exact_homogeneous_block_quotient_string_isomorphism(
            provenance, factorization, ("red", "blue"), ("blue", "red")
        )
        self.assertEqual(result.status, STATUS_EXACT)
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertEqual(result.quotient_group_order, 2)
        self.assertEqual(result.target_stabilizer_order, 1)
        self.assertIsNotNone(result.coset)
        self.assertTrue(result.coset.contains((1, 0)))
        self.assertFalse(result.coset.contains(identity(2)))

    def test_constant_feature_string_returns_whole_quotient_group(self):
        provenance, factorization = paired_provenance()
        result = exact_homogeneous_block_quotient_string_isomorphism(
            provenance, factorization, ("same", "same"), ("same", "same")
        )
        self.assertEqual(result.status, STATUS_EXACT)
        self.assertEqual(result.target_stabilizer_order, 2)
        self.assertTrue(result.coset.contains(identity(2)))
        self.assertTrue(result.coset.contains((1, 0)))

    def test_nonidentity_certified_block_bijection_is_cross_coordinate_representative(self):
        provenance, factorization = paired_provenance(block_bijection=(1, 0), with_swap=False)
        result = exact_homogeneous_block_quotient_string_isomorphism(
            provenance, factorization, ("a", "b"), ("b", "a")
        )
        self.assertEqual(result.status, STATUS_EXACT)
        self.assertEqual(result.coset.representative, (1, 0))
        self.assertTrue(result.coset.contains((1, 0)))
        self.assertFalse(result.coset.contains(identity(2)))

    def test_inventory_mismatch_is_exact_empty(self):
        provenance, factorization = paired_provenance()
        result = exact_homogeneous_block_quotient_string_isomorphism(
            provenance, factorization, ("a", "a"), ("a", "b")
        )
        self.assertEqual(result.status, STATUS_EMPTY_INVENTORY)
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertIsNone(result.coset)

    def test_completed_trivial_orbit_without_transporter_is_exact_empty(self):
        provenance, factorization = paired_provenance(with_swap=False)
        result = exact_homogeneous_block_quotient_string_isomorphism(
            provenance, factorization, ("a", "b"), ("b", "a")
        )
        self.assertEqual(result.status, STATUS_EMPTY_ORBIT)
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertEqual(result.partition_orbit_states, 1)
        self.assertIsNone(result.coset)

    def test_partition_orbit_cap_is_undetermined_not_empty(self):
        provenance, factorization = paired_provenance()
        result = exact_homogeneous_block_quotient_string_isomorphism(
            provenance,
            factorization,
            ("a", "b"),
            ("b", "a"),
            max_partition_states=1,
        )
        self.assertEqual(result.status, STATUS_UNDETERMINED_LIMIT)
        self.assertFalse(result.exact)
        self.assertFalse(result.complete)
        self.assertIsNone(result.coset)

    def test_invalid_cap_fails_closed(self):
        provenance, factorization = paired_provenance()
        result = exact_homogeneous_block_quotient_string_isomorphism(
            provenance, factorization, ("a", "b"), ("b", "a"), max_partition_states=0
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertFalse(result.exact)

    def test_non_string_feature_fails_closed(self):
        provenance, factorization = paired_provenance()
        result = exact_homogeneous_block_quotient_string_isomorphism(
            provenance, factorization, ("a", 1), ("a", 1)
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertFalse(result.complete)

    def test_wrong_feature_length_fails_closed(self):
        provenance, factorization = paired_provenance()
        result = exact_homogeneous_block_quotient_string_isomorphism(
            provenance, factorization, ("a",), ("a",)
        )
        self.assertEqual(result.status, STATUS_FAIL)

    def test_tampered_factorization_fails_closed(self):
        provenance, factorization = paired_provenance()
        tampered = replace(factorization, quotient_image_order=factorization.quotient_image_order + 1)
        result = exact_homogeneous_block_quotient_string_isomorphism(
            provenance, tampered, ("a", "b"), ("b", "a")
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertFalse(result.exact)

    def test_tampered_provenance_fails_closed(self):
        provenance, factorization = paired_provenance()
        tampered = replace(provenance, block_bijection=(1, 0))
        result = exact_homogeneous_block_quotient_string_isomorphism(
            tampered, factorization, ("a", "b"), ("b", "a")
        )
        self.assertEqual(result.status, STATUS_FAIL)

    def test_digest_binding_is_preserved(self):
        provenance, factorization = paired_provenance()
        result = exact_homogeneous_block_quotient_string_isomorphism(
            provenance, factorization, ("a", "b"), ("b", "a")
        )
        self.assertEqual(result.provenance_digest, provenance.certificate_digest)
        self.assertEqual(result.factorization_digest, factorization.certificate_digest)


if __name__ == "__main__":
    unittest.main()
