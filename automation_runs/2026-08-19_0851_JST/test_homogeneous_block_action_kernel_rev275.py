import dataclasses
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from homogeneous_block_action_kernel_v1 import (
    STATUS_EXACT,
    STATUS_FAIL,
    certify_block_action_kernel_factorization,
    replay_block_action_kernel_factorization,
)
from homogeneous_block_action_provenance_v1 import certify_group_block_action_equivariance


class BlockActionKernelRev275Test(unittest.TestCase):
    def provenance(self, blocks, source_generators, target_generators=None):
        if target_generators is None:
            target_generators = source_generators
        return certify_group_block_action_equivariance(
            blocks,
            blocks,
            list(range(len(blocks))),
            source_generators,
            target_generators,
        )

    def test_wreath_subgroup_has_exact_kernel_factorization(self):
        blocks = [[0, 1], [2, 3]]
        generators = [
            (1, 0, 2, 3),
            (0, 1, 3, 2),
            (2, 3, 0, 1),
        ]
        provenance = self.provenance(blocks, generators)
        self.assertTrue(provenance.exact)
        result = certify_block_action_kernel_factorization(provenance)
        self.assertEqual(result.status, STATUS_EXACT)
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertEqual(result.source_group_order, 8)
        self.assertEqual(result.target_group_order, 8)
        self.assertEqual(result.quotient_image_order, 2)
        self.assertEqual(result.source_kernel_order, 4)
        self.assertEqual(result.target_kernel_order, 4)
        self.assertEqual(result.source_kernel_order * result.quotient_image_order, result.source_group_order)
        self.assertTrue(replay_block_action_kernel_factorization(result, provenance))

    def test_singleton_blocks_make_action_faithful(self):
        provenance = self.provenance([[0], [1], [2]], [(1, 2, 0)])
        result = certify_block_action_kernel_factorization(provenance)
        self.assertTrue(result.exact)
        self.assertEqual(result.source_group_order, 3)
        self.assertEqual(result.quotient_image_order, 3)
        self.assertEqual(result.source_kernel_order, 1)
        self.assertEqual(result.source_kernel_generators, ())

    def test_one_block_has_full_group_as_kernel(self):
        generators = [(1, 0, 2), (1, 2, 0)]
        provenance = self.provenance([[0, 1, 2]], generators)
        result = certify_block_action_kernel_factorization(provenance)
        self.assertTrue(result.exact)
        self.assertEqual(result.source_group_order, 6)
        self.assertEqual(result.quotient_image_order, 1)
        self.assertEqual(result.source_kernel_order, 6)

    def test_source_and_target_kernels_need_not_have_same_order(self):
        blocks = [[0, 1], [2, 3]]
        provenance = self.provenance(
            blocks,
            [(1, 0, 2, 3)],
            [(0, 1, 2, 3)],
        )
        self.assertTrue(provenance.exact)
        result = certify_block_action_kernel_factorization(provenance)
        self.assertTrue(result.exact)
        self.assertEqual(result.quotient_image_order, 1)
        self.assertEqual(result.source_group_order, 2)
        self.assertEqual(result.source_kernel_order, 2)
        self.assertEqual(result.target_group_order, 1)
        self.assertEqual(result.target_kernel_order, 1)

    def test_empty_generator_lists_certify_trivial_groups(self):
        provenance = self.provenance([[0, 1], [2, 3]], [])
        result = certify_block_action_kernel_factorization(provenance)
        self.assertTrue(result.exact)
        self.assertEqual(result.source_group_order, 1)
        self.assertEqual(result.target_group_order, 1)
        self.assertEqual(result.quotient_image_order, 1)
        self.assertEqual(result.source_kernel_order, 1)
        self.assertTrue(replay_block_action_kernel_factorization(result, provenance))

    def test_tampered_rev274_provenance_fails_closed(self):
        provenance = self.provenance([[0], [1]], [(1, 0)])
        tampered = dataclasses.replace(
            provenance,
            certificate_digest="sha256:" + "0" * 64,
        )
        result = certify_block_action_kernel_factorization(tampered)
        self.assertFalse(result.exact)
        self.assertEqual(result.status, STATUS_FAIL)
        self.assertIn("does not replay", result.reason)

    def test_preflight_generator_point_cap_fails_closed(self):
        provenance = self.provenance([[0], [1]], [(1, 0)])
        result = certify_block_action_kernel_factorization(
            provenance,
            max_generator_point_checks=1,
        )
        self.assertFalse(result.exact)
        self.assertIn("preflight cap", result.reason)

    def test_domain_and_generator_caps_fail_closed(self):
        provenance = self.provenance([[0], [1]], [(1, 0)])
        degree_fail = certify_block_action_kernel_factorization(provenance, max_domain_degree=1)
        generator_fail = certify_block_action_kernel_factorization(provenance, max_generators=1)
        self.assertFalse(degree_fail.exact)
        self.assertIn("domain degree", degree_fail.reason)
        self.assertTrue(generator_fail.exact)

    def test_result_digest_tampering_is_rejected(self):
        provenance = self.provenance([[0], [1]], [(1, 0)])
        result = certify_block_action_kernel_factorization(provenance)
        self.assertTrue(result.exact)
        tampered = dataclasses.replace(
            result,
            certificate_digest="sha256:" + "f" * 64,
        )
        self.assertFalse(replay_block_action_kernel_factorization(tampered, provenance))

    def test_wrong_provenance_is_rejected_by_replay(self):
        first = self.provenance([[0], [1]], [(1, 0)])
        second = self.provenance([[0, 1]], [(1, 0)])
        result = certify_block_action_kernel_factorization(first)
        self.assertTrue(result.exact)
        self.assertFalse(replay_block_action_kernel_factorization(result, second))


if __name__ == "__main__":
    unittest.main()
