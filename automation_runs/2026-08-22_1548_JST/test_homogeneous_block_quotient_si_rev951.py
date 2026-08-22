import dataclasses
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
LEGACY = HERE.parent / "2026-08-19_0851_JST"
for path in (HERE, LEGACY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from homogeneous_block_action_kernel_v1 import certify_block_action_kernel_factorization
from homogeneous_block_action_provenance_v1 import certify_group_block_action_equivariance
from homogeneous_block_quotient_si_v1 import (
    STATUS_EMPTY,
    STATUS_EXACT,
    STATUS_FAIL,
    exact_homogeneous_block_quotient_relation_si,
)
from homogeneous_block_relation_provenance_v1 import build_structure
from permutation_group_schreier import identity


class HomogeneousBlockQuotientSIRev951Test(unittest.TestCase):
    blocks = ((0, 1), (2, 3))
    block_swap = (2, 3, 0, 1)

    def action(self, block_bijection=(0, 1)):
        provenance = certify_group_block_action_equivariance(
            self.blocks,
            self.blocks,
            block_bijection,
            (self.block_swap,),
            (self.block_swap,),
        )
        self.assertTrue(provenance.exact, provenance.reason)
        factorization = certify_block_action_kernel_factorization(provenance)
        self.assertTrue(factorization.exact, factorization.reason)
        self.assertEqual(factorization.quotient_image_order, 2)
        return provenance, factorization

    def test_unique_nontrivial_quotient_transporter(self):
        provenance, factorization = self.action()
        source = build_structure(4, unary={"red": (0, 1)})
        target = build_structure(4, unary={"red": (2, 3)})
        result = exact_homogeneous_block_quotient_relation_si(
            source, target, provenance, factorization
        )
        self.assertEqual(result.status, STATUS_EXACT)
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertEqual(result.representative, (1, 0))
        self.assertEqual(result.target_stabilizer_order, 1)
        self.assertEqual(result.source_group_elements_checked, 2)
        self.assertEqual(result.target_stabilizer_elements_checked, 2)
        self.assertIsNotNone(result.coset)
        self.assertTrue(result.coset.contains((1, 0)))
        self.assertFalse(result.coset.contains(identity(2)))
        self.assertTrue(result.certificate_digest.startswith("sha256:"))

    def test_exact_empty_after_complete_quotient_image_scan(self):
        provenance, factorization = self.action()
        source = build_structure(4, unary={"red": (0, 1)})
        target = build_structure(4, unary={"red": (0, 1, 2, 3)})
        result = exact_homogeneous_block_quotient_relation_si(
            source, target, provenance, factorization
        )
        self.assertEqual(result.status, STATUS_EMPTY)
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertIsNone(result.coset)
        self.assertIsNone(result.representative)
        self.assertEqual(result.source_group_elements_checked, 2)

    def test_whole_image_is_returned_as_target_stabilizer_coset(self):
        provenance, factorization = self.action()
        source = build_structure(4)
        target = build_structure(4)
        result = exact_homogeneous_block_quotient_relation_si(
            source, target, provenance, factorization
        )
        self.assertEqual(result.status, STATUS_EXACT)
        self.assertEqual(result.target_stabilizer_order, 2)
        self.assertEqual(result.coset.subgroup.order, 2)
        self.assertTrue(result.coset.contains((0, 1)))
        self.assertTrue(result.coset.contains((1, 0)))

    def test_rev274_coordinate_bijection_is_part_of_candidate_coset(self):
        provenance, factorization = self.action((1, 0))
        source = build_structure(4, unary={"red": (0, 1)})
        target = build_structure(4, unary={"red": (0, 1)})
        result = exact_homogeneous_block_quotient_relation_si(
            source, target, provenance, factorization
        )
        self.assertEqual(result.status, STATUS_EXACT)
        self.assertEqual(result.representative, (0, 1))
        self.assertTrue(result.coset.contains((0, 1)))

    def test_nonhomogeneous_relation_fails_closed(self):
        provenance, factorization = self.action()
        source = build_structure(4, unary={"red": (0,)})
        target = build_structure(4, unary={"red": (0,)})
        result = exact_homogeneous_block_quotient_relation_si(
            source, target, provenance, factorization
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertFalse(result.exact)
        self.assertIn("nonhomogeneous", result.reason)

    def test_group_order_cap_fails_before_enumeration(self):
        provenance, factorization = self.action()
        source = build_structure(4)
        target = build_structure(4)
        result = exact_homogeneous_block_quotient_relation_si(
            source,
            target,
            provenance,
            factorization,
            max_quotient_group_order=1,
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertIn("exceeds", result.reason)
        self.assertEqual(result.source_group_elements_checked, 0)

    def test_relation_transport_cap_fails_closed(self):
        provenance, factorization = self.action()
        source = build_structure(4, binary={"edge": ((0, 0), (0, 1), (1, 0), (1, 1))})
        target = build_structure(4, binary={"edge": ((0, 0), (0, 1), (1, 0), (1, 1))})
        result = exact_homogeneous_block_quotient_relation_si(
            source,
            target,
            provenance,
            factorization,
            max_relation_transport_checks=1,
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertIn("transport work", result.reason)
        self.assertEqual(result.source_group_elements_checked, 0)

    def test_tampered_factorization_fails_replay(self):
        provenance, factorization = self.action()
        tampered = dataclasses.replace(
            factorization,
            certificate_digest="sha256:" + "0" * 64,
        )
        result = exact_homogeneous_block_quotient_relation_si(
            build_structure(4), build_structure(4), provenance, tampered
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertIn("rev275", result.reason)

    def test_relation_signature_mismatch_fails_closed(self):
        provenance, factorization = self.action()
        source = build_structure(4, unary={"red": (0, 1)})
        target = build_structure(4, unary={"blue": (0, 1)})
        result = exact_homogeneous_block_quotient_relation_si(
            source, target, provenance, factorization
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertIn("signatures", result.reason)

    def test_boolean_caps_are_rejected(self):
        provenance, factorization = self.action()
        result = exact_homogeneous_block_quotient_relation_si(
            build_structure(4),
            build_structure(4),
            provenance,
            factorization,
            max_quotient_group_order=True,
        )
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertIn("positive integer", result.reason)


if __name__ == "__main__":
    unittest.main()
