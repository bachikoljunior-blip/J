import dataclasses
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from homogeneous_block_action_provenance_v1 import (
    STATUS_EXACT,
    certify_group_block_action_equivariance,
    replay_group_block_action_equivariance,
)


def conjugate(g, p):
    inv = [0] * len(p)
    for i, image in enumerate(p):
        inv[image] = i
    return tuple(p[g[inv[i]]] for i in range(len(p)))


class BlockActionProvenanceRev274Test(unittest.TestCase):
    def test_exact_two_block_swap(self):
        result = certify_group_block_action_equivariance(
            [[0, 2], [1, 3]],
            [[0, 2], [1, 3]],
            [0, 1],
            [(1, 2, 3, 0)],
            [(1, 2, 3, 0)],
        )
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertEqual(result.status, STATUS_EXACT)
        self.assertEqual(result.source_quotient_generators, ((1, 0),))
        self.assertTrue(replay_group_block_action_equivariance(result))

    def test_point_relabel_and_block_order_do_not_change_digest(self):
        source_generator = (1, 2, 3, 0)
        point_bijection = (2, 0, 3, 1)
        target_generator = conjugate(source_generator, point_bijection)
        source_blocks = [[0, 2], [1, 3]]
        target_blocks = [[point_bijection[x] for x in block] for block in source_blocks]
        first = certify_group_block_action_equivariance(
            source_blocks,
            target_blocks,
            [0, 1],
            [source_generator],
            [target_generator],
        )
        second = certify_group_block_action_equivariance(
            list(reversed(source_blocks)),
            list(reversed(target_blocks)),
            [0, 1],
            [source_generator],
            [target_generator],
        )
        self.assertTrue(first.exact)
        self.assertTrue(second.exact)
        self.assertEqual(first.certificate_digest, second.certificate_digest)

    def test_overlapping_partition_fails_closed(self):
        result = certify_group_block_action_equivariance(
            [[0, 1], [1, 2]], [[0, 1], [2, 3]], [0, 1], [], []
        )
        self.assertFalse(result.exact)
        self.assertIn("overlap", result.reason)

    def test_nonuniform_partition_fails_closed(self):
        result = certify_group_block_action_equivariance(
            [[0], [1, 2]], [[0], [1, 2]], [0, 1], [], []
        )
        self.assertFalse(result.exact)
        self.assertIn("uniform", result.reason)

    def test_source_generator_must_preserve_blocks(self):
        result = certify_group_block_action_equivariance(
            [[0, 1], [2, 3]],
            [[0, 1], [2, 3]],
            [0, 1],
            [(1, 2, 3, 0)],
            [(1, 2, 3, 0)],
        )
        self.assertFalse(result.exact)
        self.assertIn("source generator", result.reason)

    def test_target_generator_must_preserve_blocks(self):
        result = certify_group_block_action_equivariance(
            [[0, 2], [1, 3]],
            [[0, 1], [2, 3]],
            [0, 1],
            [(1, 2, 3, 0)],
            [(1, 2, 3, 0)],
        )
        self.assertFalse(result.exact)
        self.assertIn("target generator", result.reason)

    def test_block_bijection_must_be_bijective(self):
        result = certify_group_block_action_equivariance(
            [[0], [1]], [[0], [1]], [0, 0], [], []
        )
        self.assertFalse(result.exact)
        self.assertIn("block_bijection", result.reason)

    def test_paired_quotient_actions_must_intertwine(self):
        source_generator = (1, 2, 3, 0)
        target_generator = (2, 3, 0, 1)
        result = certify_group_block_action_equivariance(
            [[0, 2], [1, 3]],
            [[0, 2], [1, 3]],
            [0, 1],
            [source_generator],
            [target_generator],
        )
        self.assertFalse(result.exact)
        self.assertIn("intertwine", result.reason)

    def test_generator_lists_are_paired(self):
        result = certify_group_block_action_equivariance(
            [[0], [1]], [[0], [1]], [0, 1], [(1, 0)], []
        )
        self.assertFalse(result.exact)
        self.assertIn("paired one-to-one", result.reason)

    def test_generator_must_be_permutation(self):
        result = certify_group_block_action_equivariance(
            [[0], [1]], [[0], [1]], [0, 1], [(0, 0)], [(0, 1)]
        )
        self.assertFalse(result.exact)
        self.assertIn("bijection", result.reason)

    def test_trivial_generated_group_is_valid_relative_to_supplied_generators(self):
        result = certify_group_block_action_equivariance(
            [[0, 1], [2, 3]], [[0, 1], [2, 3]], [0, 1], [], []
        )
        self.assertTrue(result.exact)
        self.assertTrue(replay_group_block_action_equivariance(result))

    def test_digest_tampering_is_rejected_by_replay(self):
        result = certify_group_block_action_equivariance(
            [[0], [1]], [[0], [1]], [0, 1], [(1, 0)], [(1, 0)]
        )
        self.assertTrue(result.exact)
        tampered = dataclasses.replace(
            result, certificate_digest="sha256:" + "0" * 64
        )
        self.assertFalse(replay_group_block_action_equivariance(tampered))


if __name__ == "__main__":
    unittest.main()
