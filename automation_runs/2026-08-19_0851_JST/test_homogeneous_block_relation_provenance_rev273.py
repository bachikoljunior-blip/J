import unittest

from homogeneous_block_relation_provenance_v1 import (
    build_structure,
    certify_homogeneous_block_transport,
)


class Rev273HomogeneousBlockProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.source_partition = ((0, 1), (2, 3))
        self.target_partition = ((0, 2), (1, 3))
        self.block_map = (1, 0)
        self.source = build_structure(
            4,
            unary={"marked": {0, 1}},
            binary={
                "edge": {(u, v) for u in (0, 1) for v in (2, 3)},
                "loopish": {(u, v) for u in (2, 3) for v in (2, 3)},
            },
        )
        self.target = build_structure(
            4,
            unary={"marked": {1, 3}},
            binary={
                "edge": {(u, v) for u in (1, 3) for v in (0, 2)},
                "loopish": {(u, v) for u in (0, 2) for v in (0, 2)},
            },
        )

    def test_exact_relabelled_homogeneous_transport(self):
        result = certify_homogeneous_block_transport(
            self.source,
            self.target,
            self.source_partition,
            self.target_partition,
            self.block_map,
        )
        self.assertTrue(result.exact)
        self.assertEqual(result.reason, "exact_homogeneous_block_transport")
        self.assertIsNotNone(result.certificate)
        self.assertEqual(result.certificate.point_map, (1, 3, 0, 2))
        self.assertEqual(result.certificate.block_map, (1, 0))

    def test_nonuniform_unary_fibre_fails_closed(self):
        source = build_structure(4, unary={"marked": {0}})
        target = build_structure(4, unary={"marked": {1, 3}})
        result = certify_homogeneous_block_transport(
            source, target, self.source_partition, self.target_partition, self.block_map
        )
        self.assertFalse(result.exact)
        self.assertIn("source_not_block_homogeneous", result.reason)
        self.assertIsNone(result.certificate)

    def test_nonuniform_binary_block_pair_fails_closed(self):
        source = build_structure(4, binary={"edge": {(0, 2)}})
        target = build_structure(4, binary={"edge": set()})
        result = certify_homogeneous_block_transport(
            source, target, self.source_partition, self.target_partition, self.block_map
        )
        self.assertFalse(result.exact)
        self.assertIn("binary block pair", result.reason)

    def test_homogeneous_quotient_mismatch_fails_closed(self):
        target = build_structure(
            4,
            unary={"marked": {1, 3}},
            binary={
                "edge": {(u, v) for u in (0, 2) for v in (1, 3)},
                "loopish": {(u, v) for u in (0, 2) for v in (0, 2)},
            },
        )
        result = certify_homogeneous_block_transport(
            self.source, target, self.source_partition, self.target_partition, self.block_map
        )
        self.assertFalse(result.exact)
        self.assertEqual(result.reason, "quotient_relation_transport_mismatch")

    def test_block_size_mismatch_fails_closed(self):
        source = build_structure(4)
        target = build_structure(4)
        result = certify_homogeneous_block_transport(
            source, target, ((0,), (1, 2, 3)), ((0, 1), (2, 3)), (0, 1)
        )
        self.assertFalse(result.exact)
        self.assertEqual(result.reason, "mapped_block_size_mismatch")

    def test_malformed_partition_fails_closed(self):
        result = certify_homogeneous_block_transport(
            self.source,
            self.target,
            ((0, 1), (1, 2, 3)),
            self.target_partition,
            self.block_map,
        )
        self.assertFalse(result.exact)
        self.assertTrue(result.reason.startswith("invalid_partition:"))

    def test_signature_mismatch_fails_closed(self):
        target = build_structure(4, unary={"different": {1, 3}})
        source = build_structure(4, unary={"marked": {0, 1}})
        result = certify_homogeneous_block_transport(
            source, target, self.source_partition, self.target_partition, self.block_map
        )
        self.assertFalse(result.exact)
        self.assertEqual(result.reason, "relation_signature_mismatch")

    def test_nonbijective_block_map_fails_closed(self):
        result = certify_homogeneous_block_transport(
            self.source,
            self.target,
            self.source_partition,
            self.target_partition,
            (0, 0),
        )
        self.assertFalse(result.exact)
        self.assertEqual(result.reason, "block_map_not_bijective")


if __name__ == "__main__":
    unittest.main()
