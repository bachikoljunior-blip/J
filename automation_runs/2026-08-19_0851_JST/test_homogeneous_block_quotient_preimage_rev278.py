from __future__ import annotations

import os
import sys
import unittest
from dataclasses import replace

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from giant_block_action_certificates import _block_action
from homogeneous_block_action_provenance_v1 import certify_group_block_action_equivariance
from homogeneous_block_quotient_preimage_v1 import (
    STATUS_EXACT,
    STATUS_EXACT_EMPTY,
    STATUS_FAIL,
    lift_certified_block_quotient_preimage,
    replay_homogeneous_block_quotient_preimage,
)


BLOCKS = ((0, 1), (2, 3), (4, 5), (6, 7))
WITHIN = (1, 0, 3, 2, 5, 4, 7, 6)
BLOCK_CYCLE = (2, 3, 4, 5, 6, 7, 0, 1)
Q_CYCLE = (1, 2, 3, 0)
Q_OUTSIDE = (1, 0, 2, 3)


def provenance():
    return certify_group_block_action_equivariance(
        BLOCKS,
        BLOCKS,
        (0, 1, 2, 3),
        (WITHIN, BLOCK_CYCLE),
        (WITHIN, BLOCK_CYCLE),
    )


class HomogeneousBlockQuotientPreimageRev278Tests(unittest.TestCase):
    def test_source_lift_is_complete_kernel_coset(self):
        prov = provenance()
        cert = lift_certified_block_quotient_preimage(prov, "source", Q_CYCLE)
        self.assertEqual(cert.status, STATUS_EXACT)
        self.assertTrue(cert.exact)
        self.assertTrue(cert.complete)
        self.assertEqual(cert.domain_order, 8)
        self.assertEqual(cert.image_order, 4)
        self.assertEqual(cert.kernel_order, 2)
        self.assertIsNotNone(cert.representative)
        point_to_block = {u: i for i, block in enumerate(prov.source_blocks) for u in block}
        self.assertEqual(_block_action(cert.representative, prov.source_blocks, point_to_block), Q_CYCLE)
        self.assertTrue(replay_homogeneous_block_quotient_preimage(prov, cert))

    def test_target_side_uses_target_certified_action(self):
        prov = provenance()
        cert = lift_certified_block_quotient_preimage(prov, "target", Q_CYCLE)
        self.assertEqual(cert.status, STATUS_EXACT)
        self.assertEqual(cert.provenance_digest, prov.certificate_digest)
        self.assertEqual(cert.kernel_order, 2)
        self.assertTrue(replay_homogeneous_block_quotient_preimage(prov, cert))

    def test_quotient_nonmembership_is_exact_empty(self):
        prov = provenance()
        cert = lift_certified_block_quotient_preimage(prov, "source", Q_OUTSIDE)
        self.assertEqual(cert.status, STATUS_EXACT_EMPTY)
        self.assertTrue(cert.exact)
        self.assertTrue(cert.complete)
        self.assertIsNone(cert.representative)
        self.assertEqual(cert.domain_order, cert.image_order * cert.kernel_order)
        self.assertTrue(replay_homogeneous_block_quotient_preimage(prov, cert))

    def test_tampered_rev274_provenance_fails_closed(self):
        prov = replace(provenance(), certificate_digest="sha256:" + "0" * 64)
        cert = lift_certified_block_quotient_preimage(prov, "source", Q_CYCLE)
        self.assertEqual(cert.status, STATUS_FAIL)
        self.assertFalse(cert.exact)
        self.assertFalse(cert.complete)

    def test_invalid_side_and_invalid_quotient_fail_closed(self):
        prov = provenance()
        wrong_side = lift_certified_block_quotient_preimage(prov, "other", Q_CYCLE)
        wrong_degree = lift_certified_block_quotient_preimage(prov, "source", (0, 1, 2))
        repeated = lift_certified_block_quotient_preimage(prov, "source", (0, 0, 2, 3))
        for cert in (wrong_side, wrong_degree, repeated):
            self.assertEqual(cert.status, STATUS_FAIL)
            self.assertFalse(cert.exact)
            self.assertFalse(cert.complete)

    def test_replay_rejects_tampered_result(self):
        prov = provenance()
        cert = lift_certified_block_quotient_preimage(prov, "source", Q_CYCLE)
        tampered = replace(cert, kernel_order=cert.kernel_order + 1)
        self.assertFalse(replay_homogeneous_block_quotient_preimage(prov, tampered))


if __name__ == "__main__":
    unittest.main()
