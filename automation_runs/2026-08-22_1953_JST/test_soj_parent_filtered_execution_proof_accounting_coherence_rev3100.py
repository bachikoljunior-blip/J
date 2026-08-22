from __future__ import annotations

import hashlib
import json
import math
import unittest
from dataclasses import replace

import soj_parent_filtered_execution_proof_accounting_coherence_v1 as m


def digest(value):
    return "sha256:" + hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    ).hexdigest()


def sid(label):
    return digest({"id": label})


def make_execution(*, parent_outcome="nonempty", child_outcome="nonempty", child_ground_size=4):
    payload = {
        "schema_version": 1,
        "status": m.EXECUTION_STATUS,
        "parent_outcome_kind": parent_outcome,
        "proof_dag_outcome_kind": child_outcome,
        "reduction_identity": sid("reduction"),
        "child_result_identity": sid("child-result"),
        "parent_filtered_result_identity": sid("parent-result"),
        "execution_closure_identity": sid("closure"),
        "execution_result_lift_digest": sid("lift"),
        "execution_proof_identity_digest": sid("execution-proof"),
        "child_proof_identity_digest": sid("child-proof"),
        "child_ground_size": child_ground_size,
        "same_child_execution_certified": True,
        "parent_result_identity_equivalence_certified": False,
    }
    return {
        **payload,
        "certified": True,
        "exact": True,
        "complete": True,
        "binding_identity": digest(payload),
        "reason": "fixture",
    }


def make_proof_accounting(*, outcome="nonempty", child_ground_size=4):
    source_status = m.PARENT_NONEMPTY_STATUS if outcome == "nonempty" else m.PARENT_EMPTY_STATUS
    accepted = 2 if outcome == "nonempty" else 0
    payload = {
        "schema_version": 1,
        "status": m.PROOF_ACCOUNTING_STATUS,
        "outcome_kind": outcome,
        "source_status": source_status,
        "reduction_identity": sid("reduction"),
        "semantic_binding_identity": sid("semantic"),
        "child_instance_identity": sid("child-instance"),
        "child_result_identity": sid("child-result"),
        "parent_result_identity": sid("parent-result"),
        "proof_dag_identity": sid("parent-proof-dag"),
        "accounting_coherence_identity": sid("accounting"),
        "handoff_digest": sid("handoff"),
        "parent_action_degree": 7,
        "child_ground_size": child_ground_size,
        "candidate_count": 3,
        "accepted_count": accepted,
        "parent_filter_work_bound": 64,
        "charged_log2_reduction_cost": 5.0,
    }
    return {
        **payload,
        "certified": True,
        "exact": True,
        "complete": True,
        "coherence_identity": digest(payload),
        "reason": "fixture",
    }


def rehash_execution(value):
    payload = {k: value[k] for k in (
        "schema_version", "status", "parent_outcome_kind", "proof_dag_outcome_kind",
        "reduction_identity", "child_result_identity", "parent_filtered_result_identity",
        "execution_closure_identity", "execution_result_lift_digest", "execution_proof_identity_digest",
        "child_proof_identity_digest", "child_ground_size", "same_child_execution_certified",
        "parent_result_identity_equivalence_certified",
    )}
    value["binding_identity"] = digest(payload)


def rehash_proof_accounting(value):
    payload = {k: value[k] for k in (
        "schema_version", "status", "outcome_kind", "source_status", "reduction_identity",
        "semantic_binding_identity", "child_instance_identity", "child_result_identity",
        "parent_result_identity", "proof_dag_identity", "accounting_coherence_identity",
        "handoff_digest", "parent_action_degree", "child_ground_size", "candidate_count",
        "accepted_count", "parent_filter_work_bound", "charged_log2_reduction_cost",
    )}
    value["coherence_identity"] = digest(payload)


class DictSubclass(dict):
    pass


class StringSubclass(str):
    pass


class Rev3100ExecutionProofAccountingCoherenceTests(unittest.TestCase):
    def certify(self, execution, proof_accounting, **kwargs):
        return m.certify_parent_filtered_execution_proof_accounting_coherence(
            execution,
            proof_accounting,
            execution_replay_verified=kwargs.get("execution_replay_verified", True),
            proof_accounting_replay_verified=kwargs.get("proof_accounting_replay_verified", True),
        )

    def test_nonempty_success_and_replay(self):
        execution = make_execution()
        proof_accounting = make_proof_accounting()
        cert = self.certify(execution, proof_accounting)
        self.assertTrue(cert.certified, cert.reason)
        self.assertEqual(cert.parent_outcome_kind, "nonempty")
        self.assertEqual(cert.child_execution_outcome_kind, "nonempty")
        self.assertTrue(m.replay_parent_filtered_execution_proof_accounting_coherence(
            cert, execution, proof_accounting,
            execution_replay_verified=True,
            proof_accounting_replay_verified=True,
        ))

    def test_parent_filter_can_make_exact_empty_after_nonempty_child_execution(self):
        execution = make_execution(parent_outcome="exact_empty", child_outcome="nonempty")
        proof_accounting = make_proof_accounting(outcome="exact_empty")
        cert = self.certify(execution, proof_accounting)
        self.assertTrue(cert.certified, cert.reason)
        self.assertEqual(cert.parent_outcome_kind, "exact_empty")
        self.assertEqual(cert.child_execution_outcome_kind, "nonempty")
        self.assertEqual(cert.accepted_count, 0)

    def test_exact_empty_child_execution_binds_only_exact_empty_parent(self):
        execution = make_execution(parent_outcome="exact_empty", child_outcome="exact_empty")
        proof_accounting = make_proof_accounting(outcome="exact_empty")
        self.assertTrue(self.certify(execution, proof_accounting).certified)
        execution = make_execution(parent_outcome="nonempty", child_outcome="exact_empty")
        self.assertFalse(self.certify(execution, make_proof_accounting()).certified)

    def test_replay_gates_are_literal_true(self):
        execution = make_execution()
        proof_accounting = make_proof_accounting()
        self.assertFalse(self.certify(execution, proof_accounting, execution_replay_verified=1).certified)
        self.assertFalse(self.certify(execution, proof_accounting, proof_accounting_replay_verified=1).certified)
        self.assertFalse(self.certify(execution, proof_accounting, execution_replay_verified=False).certified)

    def test_top_level_dict_subclasses_rejected(self):
        self.assertFalse(self.certify(DictSubclass(make_execution()), make_proof_accounting()).certified)
        self.assertFalse(self.certify(make_execution(), DictSubclass(make_proof_accounting())).certified)

    def test_string_subclass_digest_rejected(self):
        execution = make_execution()
        execution["reduction_identity"] = StringSubclass(execution["reduction_identity"])
        self.assertFalse(self.certify(execution, make_proof_accounting()).certified)

    def test_execution_binding_identity_tamper_fails(self):
        execution = make_execution()
        execution["execution_closure_identity"] = sid("other-closure")
        self.assertFalse(self.certify(execution, make_proof_accounting()).certified)

    def test_execution_rehash_cannot_hide_parent_result_mismatch(self):
        execution = make_execution()
        execution["parent_filtered_result_identity"] = sid("other-parent")
        rehash_execution(execution)
        self.assertFalse(self.certify(execution, make_proof_accounting()).certified)

    def test_proof_accounting_identity_tamper_fails(self):
        proof_accounting = make_proof_accounting()
        proof_accounting["parent_filter_work_bound"] = 65
        self.assertFalse(self.certify(make_execution(), proof_accounting).certified)

    def test_proof_accounting_rehash_cannot_hide_reduction_mismatch(self):
        proof_accounting = make_proof_accounting()
        proof_accounting["reduction_identity"] = sid("other-reduction")
        rehash_proof_accounting(proof_accounting)
        self.assertFalse(self.certify(make_execution(), proof_accounting).certified)

    def test_child_result_identity_mismatch_fails(self):
        proof_accounting = make_proof_accounting()
        proof_accounting["child_result_identity"] = sid("other-child")
        rehash_proof_accounting(proof_accounting)
        self.assertFalse(self.certify(make_execution(), proof_accounting).certified)

    def test_child_ground_mismatch_fails(self):
        proof_accounting = make_proof_accounting(child_ground_size=3)
        self.assertFalse(self.certify(make_execution(child_ground_size=4), proof_accounting).certified)

    def test_parent_outcome_mismatch_fails(self):
        execution = make_execution(parent_outcome="exact_empty")
        self.assertFalse(self.certify(execution, make_proof_accounting(outcome="nonempty")).certified)

    def test_source_status_must_match_parent_outcome(self):
        proof_accounting = make_proof_accounting(outcome="exact_empty")
        proof_accounting["source_status"] = m.PARENT_NONEMPTY_STATUS
        rehash_proof_accounting(proof_accounting)
        self.assertFalse(self.certify(make_execution(parent_outcome="exact_empty"), proof_accounting).certified)

    def test_parent_result_identity_equivalence_flag_must_remain_false(self):
        execution = make_execution()
        execution["parent_result_identity_equivalence_certified"] = True
        rehash_execution(execution)
        self.assertFalse(self.certify(execution, make_proof_accounting()).certified)

    def test_nonfinite_negative_and_bool_cost_fail(self):
        for value in (math.inf, math.nan, -1.0, True):
            with self.subTest(value=value):
                proof_accounting = make_proof_accounting()
                proof_accounting["charged_log2_reduction_cost"] = value
                self.assertFalse(self.certify(make_execution(), proof_accounting).certified)

    def test_non_strict_parent_to_child_shrink_fails(self):
        proof_accounting = make_proof_accounting()
        proof_accounting["parent_action_degree"] = 4
        rehash_proof_accounting(proof_accounting)
        self.assertFalse(self.certify(make_execution(), proof_accounting).certified)

    def test_output_mutation_breaks_replay(self):
        execution = make_execution()
        proof_accounting = make_proof_accounting()
        cert = self.certify(execution, proof_accounting)
        self.assertTrue(cert.certified)
        mutated = replace(cert, handoff_digest=sid("mutated"))
        self.assertFalse(m.replay_parent_filtered_execution_proof_accounting_coherence(
            mutated, execution, proof_accounting,
            execution_replay_verified=True,
            proof_accounting_replay_verified=True,
        ))


if __name__ == "__main__":
    unittest.main()
