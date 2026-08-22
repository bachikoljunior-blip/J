from dataclasses import replace
import unittest

from permutation_group_schreier import schreier_stabilizer_chain
from proof_carrying_small_order_production_admission_v1 import ProductionAdmissionCaps
from small_order_production_proof_dag_consumer_v1 import (
    small_order_production_proof_dag_consumer,
    validate_small_order_production_identity,
)


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


class SmallOrderProductionProofDAGConsumerTests(unittest.TestCase):
    def test_nonidentity_exact_coset_is_replay_bound_and_dag_certified(self):
        n = 7
        c = cycle(n)
        group = schreier_stabilizer_chain([c])
        source = tuple(range(n))
        target = relabel_target(source, c)

        got = small_order_production_proof_dag_consumer(
            group,
            source,
            target,
            root_n=32,
            caps=ProductionAdmissionCaps(max_group_order=64),
        )

        self.assertTrue(got.certified)
        self.assertEqual(got.status, "certified_small_order_production_proof_dag")
        self.assertEqual(got.proof.status, "exact_small_order_group_coset")
        self.assertEqual(got.proof.group_elements_checked, 14)
        self.assertTrue(got.admission.admitted)
        self.assertEqual(got.admission.claimed_match_count, 1)
        self.assertTrue(got.identity_validation.certified)
        self.assertEqual(got.dag_validation.unique_nodes, 1)
        self.assertEqual(got.dag_validation.execution_occurrences, 1)
        self.assertGreater(got.proof.proof_identity.external_log2_cost_bound, 0.0)

    def test_exact_empty_is_replay_bound_and_dag_certified(self):
        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = tuple(range(n))
        target = (0, 1, 2, 3, 99)

        got = small_order_production_proof_dag_consumer(
            group,
            source,
            target,
            root_n=16,
            caps=ProductionAdmissionCaps(max_group_order=32),
        )

        self.assertTrue(got.certified)
        self.assertEqual(got.proof.status, "exact_empty_small_order_group")
        self.assertIsNone(got.proof.coset)
        self.assertEqual(got.proof.group_elements_checked, 5)
        self.assertEqual(got.admission.claimed_match_count, 0)
        self.assertEqual(got.admission.replay.replayed_match_count, 0)

    def test_repeated_colors_preserve_replayed_stabilizer_identity(self):
        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = (0,) * n

        got = small_order_production_proof_dag_consumer(
            group,
            source,
            source,
            root_n=16,
            caps=ProductionAdmissionCaps(max_group_order=32),
        )

        self.assertTrue(got.certified)
        self.assertEqual(got.admission.claimed_match_count, 5)
        self.assertEqual(got.admission.replay.target_stabilizer_size, 5)
        self.assertIn(5, got.proof.proof_identity.replay_identity)

    def test_order_cap_stays_fail_closed_before_exact_producer(self):
        n = 9
        group = schreier_stabilizer_chain([cycle(n), transposition(n)])
        source = (0,) * n

        got = small_order_production_proof_dag_consumer(
            group,
            source,
            source,
            root_n=64,
            caps=ProductionAdmissionCaps(max_group_order=64),
        )

        self.assertFalse(got.certified)
        self.assertEqual(got.status, "small_order_production_resource_cap")
        self.assertIsNone(got.proof)
        self.assertIsNone(got.admission)
        self.assertIsNone(got.dag_validation)

    def test_quadratic_replay_cap_stays_fail_closed(self):
        n = 7
        group = schreier_stabilizer_chain([cycle(n)])
        source = tuple(range(n))

        got = small_order_production_proof_dag_consumer(
            group,
            source,
            source,
            root_n=32,
            caps=ProductionAdmissionCaps(max_group_order=64, max_group_compositions=10),
        )

        self.assertFalse(got.certified)
        self.assertEqual(got.status, "small_order_production_resource_cap")
        self.assertIn("compositions", got.reason)

    def test_opaque_color_is_rejected_before_exact_producer(self):
        class Opaque:
            pass

        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = (Opaque(),) * n

        got = small_order_production_proof_dag_consumer(
            group,
            source,
            source,
            root_n=16,
            caps=ProductionAdmissionCaps(max_group_order=32),
        )

        self.assertFalse(got.certified)
        self.assertEqual(got.status, "rejected_small_order_input_snapshot")
        self.assertIsNone(got.proof)
        self.assertIsNone(got.admission)

    def test_identity_tamper_is_rejected(self):
        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = tuple(range(n))
        got = small_order_production_proof_dag_consumer(
            group,
            source,
            source,
            root_n=16,
            caps=ProductionAdmissionCaps(max_group_order=32),
        )
        self.assertTrue(got.certified)
        expected = got.proof.proof_identity
        tampered_identity = replace(expected, certificate_sha256="0" * 64)
        tampered_proof = replace(got.proof, proof_identity=tampered_identity)

        checked = validate_small_order_production_identity(
            tampered_proof,
            got.admission,
            expected,
        )

        self.assertFalse(checked.certified)
        self.assertEqual(checked.status, "mismatched_small_order_production_proof_identity")

    def test_accounting_tamper_is_rejected(self):
        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = tuple(range(n))
        got = small_order_production_proof_dag_consumer(
            group,
            source,
            source,
            root_n=16,
            caps=ProductionAdmissionCaps(max_group_order=32),
        )
        self.assertTrue(got.certified)
        bad_accounting = replace(got.proof.accounting, cost_certified=False)
        tampered = replace(got.proof, accounting=bad_accounting)

        checked = validate_small_order_production_identity(
            tampered,
            got.admission,
            got.proof.proof_identity,
        )

        self.assertFalse(checked.certified)
        self.assertEqual(checked.status, "inconsistent_small_order_production_accounting")

    def test_nonfinite_global_envelope_fails_closed(self):
        n = 5
        group = schreier_stabilizer_chain([cycle(n)])
        source = tuple(range(n))

        got = small_order_production_proof_dag_consumer(
            group,
            source,
            source,
            root_n=16,
            caps=ProductionAdmissionCaps(max_group_order=32),
            quasipoly_constant=float("nan"),
        )

        self.assertFalse(got.certified)
        self.assertEqual(got.status, "invalid_proof_dag_envelope")
        self.assertIsNotNone(got.dag_validation)
        self.assertFalse(got.dag_validation.certified)


if __name__ == "__main__":
    unittest.main()
