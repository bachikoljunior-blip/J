import dataclasses
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from homogeneous_block_action_provenance_v1 import (
    certify_group_block_action_equivariance,
)
from quotient_relation_action_invariance_v1 import (
    STATUS_EXACT,
    certify_quotient_relation_action_invariance,
    replay_quotient_relation_action_invariance,
)


def identity_quotient_block_action():
    return certify_group_block_action_equivariance(
        [[0, 1], [2, 3]],
        [[0, 1], [2, 3]],
        [1, 0],
        [(1, 0, 3, 2)],
        [(1, 0, 3, 2)],
    )


def swapping_quotient_block_action():
    return certify_group_block_action_equivariance(
        [[0, 2], [1, 3]],
        [[0, 2], [1, 3]],
        [0, 1],
        [(1, 2, 3, 0)],
        [(1, 2, 3, 0)],
    )


class QuotientRelationActionInvariantRev281Test(unittest.TestCase):
    def test_exact_unary_and_binary_transport(self):
        action = identity_quotient_block_action()
        self.assertTrue(action.exact)
        result = certify_quotient_relation_action_invariance(
            action,
            {"marked": [0]},
            {"marked": [1]},
            {"arrow": [(0, 1)]},
            {"arrow": [(1, 0)]},
        )
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertEqual(result.status, STATUS_EXACT)
        self.assertEqual(result.block_bijection, (1, 0))
        self.assertTrue(replay_quotient_relation_action_invariance(result, action))

    def test_relation_input_order_does_not_change_digest(self):
        action = identity_quotient_block_action()
        first = certify_quotient_relation_action_invariance(
            action,
            {"z": [0], "a": [1]},
            {"z": [1], "a": [0]},
            {"r": [(0, 1), (1, 1)]},
            {"r": [(1, 0), (0, 0)]},
        )
        second = certify_quotient_relation_action_invariance(
            action,
            {"a": [1], "z": [0]},
            {"a": [0], "z": [1]},
            {"r": [(1, 1), (0, 1)]},
            {"r": [(0, 0), (1, 0)]},
        )
        self.assertTrue(first.exact)
        self.assertEqual(first.certificate_digest, second.certificate_digest)

    def test_unary_relation_names_must_match(self):
        result = certify_quotient_relation_action_invariance(
            identity_quotient_block_action(),
            {"left": [0]},
            {"right": [1]},
            {},
            {},
        )
        self.assertFalse(result.exact)
        self.assertIn("unary relation names differ", result.reason)

    def test_binary_relation_names_must_match(self):
        result = certify_quotient_relation_action_invariance(
            identity_quotient_block_action(),
            {},
            {},
            {"edge": [(0, 1)]},
            {"other": [(1, 0)]},
        )
        self.assertFalse(result.exact)
        self.assertIn("binary relation names differ", result.reason)

    def test_block_bijection_must_transport_relation_exactly(self):
        result = certify_quotient_relation_action_invariance(
            identity_quotient_block_action(),
            {"marked": [0]},
            {"marked": [0]},
            {},
            {},
        )
        self.assertFalse(result.exact)
        self.assertIn("does not transport unary", result.reason)

    def test_non_invariant_unary_relation_fails_closed(self):
        result = certify_quotient_relation_action_invariance(
            swapping_quotient_block_action(),
            {"marked": [0]},
            {"marked": [0]},
            {},
            {},
        )
        self.assertFalse(result.exact)
        self.assertIn("does not stabilize unary", result.reason)

    def test_non_invariant_binary_relation_fails_closed(self):
        result = certify_quotient_relation_action_invariance(
            swapping_quotient_block_action(),
            {},
            {},
            {"directed": [(0, 0)]},
            {"directed": [(0, 0)]},
        )
        self.assertFalse(result.exact)
        self.assertIn("does not stabilize binary", result.reason)

    def test_out_of_range_quotient_point_fails_closed(self):
        result = certify_quotient_relation_action_invariance(
            identity_quotient_block_action(),
            {"bad": [2]},
            {"bad": [0]},
            {},
            {},
        )
        self.assertFalse(result.exact)
        self.assertIn("out-of-range quotient point", result.reason)

    def test_vacuous_relation_family_is_not_certified(self):
        result = certify_quotient_relation_action_invariance(
            identity_quotient_block_action(), {}, {}, {}, {}
        )
        self.assertFalse(result.exact)
        self.assertIn("at least one", result.reason)

    def test_tampered_rev274_certificate_is_rejected(self):
        action = identity_quotient_block_action()
        tampered = dataclasses.replace(
            action, certificate_digest="sha256:" + "0" * 64
        )
        result = certify_quotient_relation_action_invariance(
            tampered, {"all": [0, 1]}, {"all": [0, 1]}, {}, {}
        )
        self.assertFalse(result.exact)
        self.assertIn("not exact/replay-valid", result.reason)

    def test_certificate_digest_tampering_is_rejected_by_replay(self):
        action = identity_quotient_block_action()
        result = certify_quotient_relation_action_invariance(
            action, {"marked": [0]}, {"marked": [1]}, {}, {}
        )
        self.assertTrue(result.exact)
        tampered = dataclasses.replace(
            result, certificate_digest="sha256:" + "0" * 64
        )
        self.assertFalse(
            replay_quotient_relation_action_invariance(tampered, action)
        )

    def test_wrong_block_action_is_rejected_by_replay(self):
        action = identity_quotient_block_action()
        result = certify_quotient_relation_action_invariance(
            action, {"marked": [0]}, {"marked": [1]}, {}, {}
        )
        other = swapping_quotient_block_action()
        self.assertTrue(result.exact)
        self.assertFalse(replay_quotient_relation_action_invariance(result, other))


if __name__ == "__main__":
    unittest.main()
