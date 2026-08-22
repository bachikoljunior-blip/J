from dataclasses import replace
import unittest

from coset_stabilizer_primitives import RightCoset
from exact_result_replay_verifier_v1 import ReplayStatus
from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_small_order_production_admission_v1 import (
    ProductionAdmissionCaps,
    ProductionAdmissionStatus,
    preflight_small_order_production_admission,
    run_proof_carrying_small_order_production_admission,
    verify_small_order_production_result,
)
from proof_carrying_small_order_si_v1 import exact_small_order_group_string_isomorphism


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


class ProofCarryingSmallOrderProductionAdmissionTests(unittest.TestCase):
    def test_nonidentity_cyclic_coset_is_admitted_only_after_independent_replay(self):
        n = 7
        c = cycle(n)
        group = schreier_stabilizer_chain([c])
        source = tuple(range(n))
        target = relabel_target(source, c)

        got = run_proof_carrying_small_order_production_admission(
            group,
            source,
            target,
            root_n=32,
            caps=ProductionAdmissionCaps(max_group_order=64),
        )

        self.assertTrue(got.admitted)
        self.assertEqual(got.status, ProductionAdmissionStatus.ADMITTED_EXACT)
        self.assertTrue(got.producer_invoked)
        self.assertEqual(got.producer_status, "exact_small_order_group_coset")
        self.assertEqual(got.producer_group_elements_checked, 14)
        self.assertTrue(got.recurrence_certified)
        self.assertIsNotNone(got.replay)
        self.assertEqual(got.replay.status, ReplayStatus.VERIFIED_EXACT)
        self.assertEqual(got.claimed_match_count, 1)
        self.assertEqual(got.replay.target_stabilizer_size, 1)
        self.assertEqual(len(got.certificate_sha256), 64)

    def test_exact_empty_is_admitted_with_complete_group_replay(self):
        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = tuple(range(n))
        target = (0, 1, 2, 3, 99)

        got = run_proof_carrying_small_order_production_admission(
            group,
            source,
            target,
            root_n=16,
            caps=ProductionAdmissionCaps(max_group_order=32),
        )

        self.assertTrue(got.admitted)
        self.assertEqual(got.producer_status, "exact_empty_small_order_group")
        self.assertEqual(got.producer_group_elements_checked, 5)
        self.assertEqual(got.claimed_match_count, 0)
        self.assertEqual(got.replay.replayed_match_count, 0)

    def test_repeated_color_target_stabilizer_order_must_match_producer_coset(self):
        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = (0,) * n

        got = run_proof_carrying_small_order_production_admission(
            group,
            source,
            source,
            root_n=16,
            caps=ProductionAdmissionCaps(max_group_order=32),
        )

        self.assertTrue(got.admitted)
        self.assertEqual(got.claimed_match_count, 5)
        self.assertEqual(got.replay.target_stabilizer_size, 5)

    def test_order_cap_rejects_before_producer_execution(self):
        n = 9
        group = schreier_stabilizer_chain([cycle(n), transposition(n)])
        source = (0,) * n

        got = run_proof_carrying_small_order_production_admission(
            group,
            source,
            source,
            root_n=64,
            caps=ProductionAdmissionCaps(max_group_order=64),
        )

        self.assertFalse(got.admitted)
        self.assertEqual(got.status, ProductionAdmissionStatus.UNKNOWN_RESOURCE_CAP)
        self.assertFalse(got.producer_invoked)
        self.assertIsNone(got.producer_status)
        self.assertIsNone(got.replay)

    def test_quadratic_replay_cap_rejects_before_producer_execution(self):
        n = 7
        group = schreier_stabilizer_chain([cycle(n)])
        source = tuple(range(n))
        caps = ProductionAdmissionCaps(
            max_group_order=64,
            max_group_compositions=10,
        )

        preflight = preflight_small_order_production_admission(
            group, source, source, root_n=32, caps=caps
        )
        got = run_proof_carrying_small_order_production_admission(
            group, source, source, root_n=32, caps=caps
        )

        self.assertFalse(preflight.admitted)
        self.assertEqual(preflight.required_group_compositions, 49)
        self.assertFalse(got.producer_invoked)
        self.assertEqual(got.status, ProductionAdmissionStatus.UNKNOWN_RESOURCE_CAP)

    def test_tampered_certified_group_order_is_rejected(self):
        n = 7
        group = schreier_stabilizer_chain([cycle(n)])
        source = tuple(range(n))
        producer = exact_small_order_group_string_isomorphism(
            group, source, source, root_n=32, max_group_order=64
        )
        tampered = replace(
            producer,
            certified_group_order=producer.certified_group_order + 1,
        )

        got = verify_small_order_production_result(
            group,
            source,
            source,
            tampered,
            root_n=32,
            caps=ProductionAdmissionCaps(max_group_order=64),
        )

        self.assertFalse(got.admitted)
        self.assertEqual(got.status, ProductionAdmissionStatus.REJECTED_PRODUCER_PROOF)

    def test_wrong_producer_coset_is_rejected_by_complete_replay(self):
        n = 7
        c = cycle(n)
        group = schreier_stabilizer_chain([c])
        source = tuple(range(n))
        target = relabel_target(source, c)
        producer = exact_small_order_group_string_isomorphism(
            group, source, target, root_n=32, max_group_order=64
        )
        wrong = replace(producer, coset=RightCoset(group, identity(n)))

        got = verify_small_order_production_result(
            group,
            source,
            target,
            wrong,
            root_n=32,
            caps=ProductionAdmissionCaps(max_group_order=64),
        )

        self.assertFalse(got.admitted)
        self.assertEqual(got.status, ProductionAdmissionStatus.REJECTED_REPLAY)
        self.assertEqual(got.replay.status, ReplayStatus.REJECTED)

    def test_tampered_accounting_leaf_is_rejected_before_replay(self):
        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = tuple(range(n))
        producer = exact_small_order_group_string_isomorphism(
            group, source, source, root_n=16, max_group_order=32
        )
        bad_accounting = replace(producer.accounting, cost_certified=False)
        tampered = replace(producer, accounting=bad_accounting)

        got = verify_small_order_production_result(
            group,
            source,
            source,
            tampered,
            root_n=16,
            caps=ProductionAdmissionCaps(max_group_order=32),
        )

        self.assertFalse(got.admitted)
        self.assertEqual(got.status, ProductionAdmissionStatus.REJECTED_PRODUCER_PROOF)
        self.assertIsNone(got.replay)

    def test_opaque_color_is_rejected_before_producer_execution(self):
        class Opaque:
            pass

        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = (Opaque(),) * n

        got = run_proof_carrying_small_order_production_admission(
            group,
            source,
            source,
            root_n=16,
            caps=ProductionAdmissionCaps(max_group_order=32),
        )

        self.assertFalse(got.admitted)
        self.assertEqual(got.status, ProductionAdmissionStatus.REJECTED_INPUT)
        self.assertFalse(got.producer_invoked)


if __name__ == "__main__":
    unittest.main()
