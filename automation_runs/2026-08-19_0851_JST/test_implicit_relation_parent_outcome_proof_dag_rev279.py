from __future__ import annotations

import hashlib
import unittest
from dataclasses import replace
from fractions import Fraction
from types import SimpleNamespace

from implicit_relation_parent_outcome_proof_dag_v1 import (
    build_parent_outcome_proof_identity,
    parent_outcome_contract_proof_dag_consumer,
    validate_parent_outcome_proof_identity,
)
from implicit_relation_parent_outcome_v1 import (
    EXACT_EMPTY_STATUSES,
    ParentExactOutcomeContract,
    normalize_parent_exact_outcome,
    transcript_from_exact_empty_promotion,
    transcript_from_nonempty_promotion,
)


def digest(label: str) -> str:
    return f"sha256:{hashlib.sha256(label.encode('utf-8')).hexdigest()}"


SOURCE = digest("rev279-source")
TARGET = digest("rev279-target")
ARTIFACT = digest("rev279-upstream")


def nonempty_outcome() -> ParentExactOutcomeContract:
    evidence = SimpleNamespace(
        status="exact_implicit_relation_parent_coset",
        exact=True,
        complete=True,
        domain_degree=7,
        auxiliary_degree=63,
        coset=object(),
    )
    transcript = transcript_from_nonempty_promotion(
        evidence,
        source_relation_digest=SOURCE,
        target_relation_digest=TARGET,
        upstream_artifact_digest=ARTIFACT,
    )
    return normalize_parent_exact_outcome(
        [transcript],
        expected_source_relation_digest=SOURCE,
        expected_target_relation_digest=TARGET,
        expected_domain_degree=7,
    )


def empty_outcome(status: str) -> ParentExactOutcomeContract:
    evidence = SimpleNamespace(
        status=status,
        exact=True,
        complete=True,
        domain_degree=7,
        auxiliary_degree=(
            63 if status == "exact_empty_parent_feature_inventory_mismatch" else 0
        ),
    )
    transcript = transcript_from_exact_empty_promotion(
        evidence,
        source_relation_digest=SOURCE,
        target_relation_digest=TARGET,
        upstream_artifact_digest=ARTIFACT,
    )
    return normalize_parent_exact_outcome(
        [transcript],
        expected_source_relation_digest=SOURCE,
        expected_target_relation_digest=TARGET,
        expected_domain_degree=7,
    )


class ParentOutcomeProofDAGRev279Test(unittest.TestCase):
    def test_nonempty_contract_enters_evidence_only_proof_dag(self):
        result = parent_outcome_contract_proof_dag_consumer(
            nonempty_outcome(), original_root_n=7
        )
        self.assertEqual(result.status, "certified_parent_outcome_contract_proof_dag")
        self.assertTrue(result.outcome.exact)
        self.assertTrue(result.identity_validation.certified)
        self.assertTrue(result.dag_validation.certified)
        self.assertFalse(result.semantic_exactness_certified)
        self.assertFalse(result.proof.exact)
        self.assertIsNone(result.proof.coset)

    def test_all_exact_empty_contracts_enter_same_evidence_boundary(self):
        for status in sorted(EXACT_EMPTY_STATUSES):
            with self.subTest(status=status):
                result = parent_outcome_contract_proof_dag_consumer(
                    empty_outcome(status), original_root_n=7
                )
                self.assertEqual(
                    result.status, "certified_parent_outcome_contract_proof_dag"
                )
                self.assertEqual(result.outcome.outcome_kind, "exact_empty")
                self.assertTrue(result.dag_validation.certified)
                self.assertFalse(result.semantic_exactness_certified)
                self.assertIsNone(result.proof.coset)

    def test_equal_contracts_build_equal_hashable_replay_identities(self):
        first = build_parent_outcome_proof_identity(
            nonempty_outcome(), original_root_n=11
        )
        second = build_parent_outcome_proof_identity(
            nonempty_outcome(), original_root_n=11
        )
        self.assertEqual(first, second)
        self.assertEqual(hash(first), hash(second))
        self.assertTrue(first.replay_stable)

    def test_transcript_digest_tamper_fails_before_proof_construction(self):
        corrupted = replace(
            nonempty_outcome(),
            transcript_digest=digest("tampered-transcript"),
        )
        result = parent_outcome_contract_proof_dag_consumer(
            corrupted, original_root_n=7
        )
        self.assertEqual(result.status, "invalid_parent_outcome_contract")
        self.assertIn("transcript digest", result.reason)
        self.assertIsNone(result.proof)

    def test_nonexact_fabricated_contract_fails_closed(self):
        fabricated = replace(nonempty_outcome(), exact=False)
        result = parent_outcome_contract_proof_dag_consumer(
            fabricated, original_root_n=7
        )
        self.assertEqual(result.status, "invalid_parent_outcome_contract")
        self.assertIsNone(result.dag_validation)

    def test_nonempty_source_revision_mismatch_is_rejected(self):
        fabricated = replace(
            nonempty_outcome(),
            source_evidence_revision=263,
        )
        result = parent_outcome_contract_proof_dag_consumer(
            fabricated, original_root_n=7
        )
        self.assertEqual(result.status, "invalid_parent_outcome_contract")

    def test_status_kind_mismatch_is_rejected(self):
        fabricated = replace(
            nonempty_outcome(),
            status="exact_parent_outcome_empty",
        )
        result = parent_outcome_contract_proof_dag_consumer(
            fabricated, original_root_n=7
        )
        self.assertEqual(result.status, "invalid_parent_outcome_contract")

    def test_original_root_must_dominate_parent_domain(self):
        result = parent_outcome_contract_proof_dag_consumer(
            nonempty_outcome(), original_root_n=6
        )
        self.assertEqual(result.status, "invalid_parent_outcome_contract")
        self.assertIn("dominate", result.reason)

    def test_zero_domain_contract_is_rejected_even_if_dataclass_is_fabricated(self):
        fabricated = replace(nonempty_outcome(), domain_degree=0)
        result = parent_outcome_contract_proof_dag_consumer(
            fabricated, original_root_n=7
        )
        self.assertEqual(result.status, "invalid_parent_outcome_contract")

    def test_identity_tamper_is_detected_independently(self):
        result = parent_outcome_contract_proof_dag_consumer(
            nonempty_outcome(), original_root_n=7
        )
        expected = result.proof.proof_identity
        tampered = replace(
            result.proof,
            proof_identity=replace(expected, original_root_n=8),
        )
        validation = validate_parent_outcome_proof_identity(tampered, expected)
        self.assertFalse(validation.certified)
        self.assertEqual(
            validation.status, "mismatched_parent_outcome_proof_identity"
        )

    def test_joint_expected_and_attached_schema_tamper_is_rejected(self):
        result = parent_outcome_contract_proof_dag_consumer(
            nonempty_outcome(), original_root_n=7
        )
        tampered_identity = replace(
            result.proof.proof_identity,
            schema="attacker-controlled-proof-identity-v1",
        )
        tampered_proof = replace(result.proof, proof_identity=tampered_identity)
        validation = validate_parent_outcome_proof_identity(
            tampered_proof, tampered_identity
        )
        self.assertFalse(validation.certified)
        self.assertEqual(
            validation.status, "malformed_parent_outcome_proof_identity"
        )

    def test_joint_expected_and_attached_solver_tamper_is_rejected(self):
        result = parent_outcome_contract_proof_dag_consumer(
            nonempty_outcome(), original_root_n=7
        )
        tampered_identity = replace(
            result.proof.proof_identity,
            solver_identity=("implicit_relation_parent_outcome_v1", "other-dag", 279),
        )
        tampered_proof = replace(result.proof, proof_identity=tampered_identity)
        validation = validate_parent_outcome_proof_identity(
            tampered_proof, tampered_identity
        )
        self.assertFalse(validation.certified)
        self.assertEqual(
            validation.status, "malformed_parent_outcome_proof_identity"
        )

    def test_joint_expected_and_attached_transcript_tamper_is_rejected(self):
        result = parent_outcome_contract_proof_dag_consumer(
            nonempty_outcome(), original_root_n=7
        )
        tampered_identity = replace(
            result.proof.proof_identity,
            transcript_digest=digest("jointly-tampered-transcript"),
        )
        tampered_proof = replace(result.proof, proof_identity=tampered_identity)
        validation = validate_parent_outcome_proof_identity(
            tampered_proof, tampered_identity
        )
        self.assertFalse(validation.certified)
        self.assertEqual(
            validation.status, "malformed_parent_outcome_proof_identity"
        )
        self.assertIn("transcript", validation.reason)

    def test_semantic_exactness_bit_or_coset_injection_is_forbidden(self):
        result = parent_outcome_contract_proof_dag_consumer(
            nonempty_outcome(), original_root_n=7
        )
        semantic_tamper = replace(result.proof, exact=True)
        validation = validate_parent_outcome_proof_identity(
            semantic_tamper, result.proof.proof_identity
        )
        self.assertFalse(validation.certified)
        self.assertEqual(
            validation.status,
            "semantic_promotion_forbidden_for_parent_outcome_contract",
        )

    def test_accounting_payload_tamper_is_detected(self):
        result = parent_outcome_contract_proof_dag_consumer(
            nonempty_outcome(), original_root_n=7
        )
        tampered_accounting = replace(
            result.proof.accounting,
            local_log2_cost_bound=result.proof.local_log2_cost_bound + 1.0,
        )
        tampered = replace(result.proof, accounting=tampered_accounting)
        validation = validate_parent_outcome_proof_identity(
            tampered, result.proof.proof_identity
        )
        self.assertFalse(validation.certified)
        self.assertEqual(
            validation.status, "mismatched_parent_outcome_accounting_payload"
        )

    def test_joint_local_charge_understatement_is_rejected(self):
        result = parent_outcome_contract_proof_dag_consumer(
            nonempty_outcome(), original_root_n=7
        )
        tampered_accounting = replace(
            result.proof.accounting,
            local_log2_cost_bound=0.0,
        )
        tampered = replace(
            result.proof,
            local_log2_cost_bound=0.0,
            accounting=tampered_accounting,
        )
        validation = validate_parent_outcome_proof_identity(
            tampered, result.proof.proof_identity
        )
        self.assertFalse(validation.certified)
        self.assertEqual(
            validation.status, "mismatched_parent_outcome_accounting_payload"
        )

    def test_nonfinite_joint_local_charge_tamper_is_rejected(self):
        result = parent_outcome_contract_proof_dag_consumer(
            nonempty_outcome(), original_root_n=7
        )
        tampered_accounting = replace(
            result.proof.accounting,
            local_log2_cost_bound=float("nan"),
        )
        tampered = replace(
            result.proof,
            local_log2_cost_bound=float("nan"),
            accounting=tampered_accounting,
        )
        validation = validate_parent_outcome_proof_identity(
            tampered, result.proof.proof_identity
        )
        self.assertFalse(validation.certified)
        self.assertEqual(
            validation.status, "mismatched_parent_outcome_accounting_payload"
        )

    def test_evidence_leaf_execution_counter_tamper_is_rejected(self):
        result = parent_outcome_contract_proof_dag_consumer(
            nonempty_outcome(), original_root_n=7
        )
        tampered = replace(result.proof, permutation_candidates_checked=1)
        validation = validate_parent_outcome_proof_identity(
            tampered, result.proof.proof_identity
        )
        self.assertFalse(validation.certified)
        self.assertEqual(
            validation.status, "mismatched_parent_outcome_execution_counter"
        )

    def test_evidence_leaf_child_injection_is_rejected(self):
        result = parent_outcome_contract_proof_dag_consumer(
            nonempty_outcome(), original_root_n=7
        )
        tampered = replace(result.proof, children=(result.proof,))
        validation = validate_parent_outcome_proof_identity(
            tampered, result.proof.proof_identity
        )
        self.assertFalse(validation.certified)
        self.assertEqual(
            validation.status, "nonterminal_parent_outcome_evidence_leaf"
        )

    def test_quasipolynomial_envelope_failure_remains_uncertified(self):
        result = parent_outcome_contract_proof_dag_consumer(
            nonempty_outcome(),
            original_root_n=7,
            quasipoly_constant=0.000001,
        )
        self.assertEqual(
            result.status, "proof_dag_quasipolynomial_envelope_exceeded"
        )
        self.assertFalse(result.dag_validation.certified)
        self.assertFalse(result.semantic_exactness_certified)

    def test_external_negative_cost_fails_closed_before_shared_validator(self):
        result = parent_outcome_contract_proof_dag_consumer(
            nonempty_outcome(),
            original_root_n=7,
            external_log2_cost_bound=-1.0,
        )
        self.assertEqual(result.status, "invalid_parent_outcome_resource_envelope")
        self.assertIsNone(result.proof)
        self.assertIsNone(result.dag_validation)

    def test_nonfinite_or_malformed_external_cost_never_fails_open(self):
        for value in (float("nan"), float("inf"), float("-inf"), True, "1.0"):
            with self.subTest(value=value):
                result = parent_outcome_contract_proof_dag_consumer(
                    nonempty_outcome(),
                    original_root_n=7,
                    external_log2_cost_bound=value,
                )
                self.assertEqual(
                    result.status, "invalid_parent_outcome_resource_envelope"
                )
                self.assertIsNone(result.proof)
                self.assertIsNone(result.dag_validation)

    def test_overflowing_real_envelope_values_fail_closed_without_exception(self):
        huge = Fraction(10**1000, 1)
        cases = (
            {"external_log2_cost_bound": huge},
            {"quasipoly_constant": huge},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                result = parent_outcome_contract_proof_dag_consumer(
                    nonempty_outcome(),
                    original_root_n=7,
                    **kwargs,
                )
                self.assertEqual(
                    result.status, "invalid_parent_outcome_resource_envelope"
                )
                self.assertIsNone(result.proof)
                self.assertIsNone(result.dag_validation)

    def test_malformed_quasipolynomial_parameters_never_reach_shared_validator(self):
        cases = (
            {"quasipoly_power": True},
            {"quasipoly_power": -1},
            {"quasipoly_power": 2.5},
            {"quasipoly_constant": float("nan")},
            {"quasipoly_constant": float("inf")},
            {"quasipoly_constant": 0.0},
            {"quasipoly_constant": True},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                result = parent_outcome_contract_proof_dag_consumer(
                    nonempty_outcome(),
                    original_root_n=7,
                    **kwargs,
                )
                self.assertEqual(
                    result.status, "invalid_parent_outcome_resource_envelope"
                )
                self.assertIsNone(result.proof)
                self.assertIsNone(result.dag_validation)

    def test_wrong_runtime_type_fails_closed(self):
        result = parent_outcome_contract_proof_dag_consumer(
            object(), original_root_n=7
        )
        self.assertEqual(result.status, "invalid_parent_outcome_contract")
        self.assertIsNone(result.outcome)
        self.assertIsNone(result.proof)


if __name__ == "__main__":
    unittest.main()
