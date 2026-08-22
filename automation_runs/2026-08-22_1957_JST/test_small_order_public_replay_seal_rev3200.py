from dataclasses import replace
import unittest

from small_order_public_replay_seal_v1 import (
    ProductionAdmissionCaps,
    build_small_order_public_replay_seal,
    verify_small_order_public_replay_seal,
)
from permutation_group_schreier import schreier_stabilizer_chain


def cycle(n):
    return tuple((i + 1) % n for i in range(n))


def transposition(n, a=0, b=1):
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def relabel_target(source, p):
    inv = [0] * len(p)
    for i, j in enumerate(p):
        inv[j] = i
    return tuple(source[inv[j]] for j in range(len(p)))


class SmallOrderPublicReplaySealTests(unittest.TestCase):
    def test_nonempty_rev620_execution_gets_deterministic_public_seal(self):
        n = 7
        c = cycle(n)
        group = schreier_stabilizer_chain([c])
        source = tuple(range(n))
        target = relabel_target(source, c)

        got = build_small_order_public_replay_seal(
            group,
            source,
            target,
            root_n=32,
            caps=ProductionAdmissionCaps(max_group_order=64),
        )

        self.assertTrue(got.certified)
        self.assertEqual(got.status, "certified_small_order_public_replay_seal")
        self.assertEqual(got.seal.outcome, "exact_nonempty")
        self.assertEqual(got.seal.proof_status, "exact_small_order_group_coset")
        self.assertEqual(got.seal.claimed_match_count, 1)
        self.assertEqual(got.seal.dag_unique_nodes, 1)
        self.assertEqual(got.seal.dag_execution_occurrences, 1)
        self.assertEqual(len(got.seal.seal_sha256), 64)

        replay = verify_small_order_public_replay_seal(
            group,
            source,
            target,
            got.seal,
            root_n=32,
            caps=ProductionAdmissionCaps(max_group_order=64),
        )
        self.assertTrue(replay.certified)
        self.assertEqual(replay.status, "verified_small_order_public_replay_seal")

    def test_exact_empty_rev620_execution_gets_distinct_public_seal(self):
        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = tuple(range(n))
        target = (0, 1, 2, 3, 99)

        got = build_small_order_public_replay_seal(
            group,
            source,
            target,
            root_n=16,
            caps=ProductionAdmissionCaps(max_group_order=32),
        )

        self.assertTrue(got.certified)
        self.assertEqual(got.seal.outcome, "exact_empty")
        self.assertEqual(got.seal.proof_status, "exact_empty_small_order_group")
        self.assertEqual(got.seal.claimed_match_count, 0)

    def test_two_independent_builds_are_byte_identity_equivalent(self):
        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = (0,) * n
        kwargs = dict(root_n=16, caps=ProductionAdmissionCaps(max_group_order=32))

        first = build_small_order_public_replay_seal(group, source, source, **kwargs)
        second = build_small_order_public_replay_seal(group, source, source, **kwargs)

        self.assertTrue(first.certified)
        self.assertTrue(second.certified)
        self.assertEqual(first.seal, second.seal)
        self.assertEqual(first.seal.claimed_match_count, 5)

    def test_tampered_seal_digest_fails_before_reexecution(self):
        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = tuple(range(n))
        kwargs = dict(root_n=16, caps=ProductionAdmissionCaps(max_group_order=32))
        got = build_small_order_public_replay_seal(group, source, source, **kwargs)
        self.assertTrue(got.certified)
        tampered = replace(got.seal, seal_sha256="0" * 64)

        checked = verify_small_order_public_replay_seal(group, source, source, tampered, **kwargs)

        self.assertFalse(checked.certified)
        self.assertEqual(checked.status, "invalid_small_order_public_replay_seal")
        self.assertIn("digest", checked.reason)
        self.assertIsNone(checked.execution)

    def test_tampered_exact_outcome_fails_closed(self):
        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = tuple(range(n))
        kwargs = dict(root_n=16, caps=ProductionAdmissionCaps(max_group_order=32))
        got = build_small_order_public_replay_seal(group, source, source, **kwargs)
        self.assertTrue(got.certified)
        tampered = replace(got.seal, outcome="exact_empty", claimed_match_count=0)

        checked = verify_small_order_public_replay_seal(group, source, source, tampered, **kwargs)

        self.assertFalse(checked.certified)
        self.assertEqual(checked.status, "invalid_small_order_public_replay_seal")

    def test_different_target_cannot_replay_original_seal(self):
        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = tuple(range(n))
        kwargs = dict(root_n=16, caps=ProductionAdmissionCaps(max_group_order=32))
        got = build_small_order_public_replay_seal(group, source, source, **kwargs)
        self.assertTrue(got.certified)
        changed_target = (0, 1, 2, 3, 99)

        checked = verify_small_order_public_replay_seal(
            group, source, changed_target, got.seal, **kwargs
        )

        self.assertFalse(checked.certified)
        self.assertEqual(checked.status, "small_order_public_replay_seal_mismatch")

    def test_rev620_resource_cap_remains_fail_closed_without_seal(self):
        n = 9
        group = schreier_stabilizer_chain([cycle(n), transposition(n)])
        source = (0,) * n

        got = build_small_order_public_replay_seal(
            group,
            source,
            source,
            root_n=64,
            caps=ProductionAdmissionCaps(max_group_order=64),
        )

        self.assertFalse(got.certified)
        self.assertEqual(got.status, "rev620_execution_not_certified")
        self.assertIsNone(got.seal)
        self.assertEqual(got.execution.status, "small_order_production_resource_cap")

    def test_invalid_global_envelope_remains_fail_closed_without_seal(self):
        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = tuple(range(n))

        got = build_small_order_public_replay_seal(
            group,
            source,
            source,
            root_n=16,
            caps=ProductionAdmissionCaps(max_group_order=32),
            quasipoly_constant=float("nan"),
        )

        self.assertFalse(got.certified)
        self.assertIsNone(got.seal)
        self.assertEqual(got.execution.status, "invalid_proof_dag_envelope")


if __name__ == "__main__":
    unittest.main()
