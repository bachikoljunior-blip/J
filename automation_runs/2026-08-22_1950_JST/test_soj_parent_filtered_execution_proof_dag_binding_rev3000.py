from __future__ import annotations

import unittest
from dataclasses import dataclass, replace

import soj_parent_filtered_execution_proof_dag_binding_v2 as m


def psha(ch: str) -> str:
    return "sha256:" + ch * 64


@dataclass(frozen=True)
class ChildProofIdentity:
    token: str
    replay_stable: bool = True


def parent_result(*, parent_outcome: str = "nonempty", child_identity: str = psha("2"), reduction: str = psha("1")):
    if parent_outcome == "nonempty":
        status = m.PARENT_NONEMPTY_STATUS
        candidate_count = 3
        accepted_count = 2
        representative = (0, 1, 2, 3)
        stabilizer = ((0, 1, 2, 3),)
    elif parent_outcome == "filtered_empty":
        status = m.PARENT_EMPTY_STATUS
        candidate_count = 3
        accepted_count = 0
        representative = None
        stabilizer = ()
    else:
        status = m.PARENT_EMPTY_STATUS
        candidate_count = 0
        accepted_count = 0
        representative = None
        stabilizer = ()
    payload = {
        "schema_version": 1,
        "status": status,
        "reduction_identity": reduction,
        "semantic_binding_identity": psha("3"),
        "child_instance_identity": psha("4"),
        "child_result_identity": child_identity,
        "action_degree": 4,
        "candidate_count": candidate_count,
        "accepted_count": accepted_count,
        "representative": representative,
        "parent_stabilizer_elements": stabilizer,
        "work_bound": 200,
    }
    return payload | {
        "certified": True,
        "exact": True,
        "complete": True,
        "result_identity": m._sha256(payload),
        "reason": "fixture",
    }


def execution_result(*, outcome: str = "nonempty", child_identity: str = psha("2"), reduction: str = psha("1")):
    status = m.EXEC_NONEMPTY_STATUS if outcome == "nonempty" else m.EXEC_EMPTY_STATUS
    closure = psha("5")
    lift = psha("6")
    child_proof = ChildProofIdentity("child")
    proof_identity = {
        "schema": "corrected-soj-recursive-production-execution-proof-dag-v1",
        "closure_identity": closure,
        "result_lift_digest": lift,
        "child_result_identity": child_identity,
        "child_proof_identity": child_proof,
        "parent_values_digest": psha("7"),
        "original_root_n": 6,
        "replay_stable": True,
    }
    return {
        "schema_version": 1,
        "status": status,
        "certified": True,
        "exact": True,
        "complete": True,
        "outcome_kind": outcome,
        "parent_action_degree": 6,
        "child_ground_size": 4,
        "reduction_identity": reduction,
        "closure_identity": closure,
        "child_result_identity": child_identity,
        "result_lift_digest": lift,
        "proof_identity": proof_identity,
        "reason": "fixture",
    }


class Rev3000BindingTests(unittest.TestCase):
    def test_nonempty_shared_child_execution_binds_and_replays(self):
        parent = parent_result()
        execution = execution_result()
        out = m.certify_parent_filtered_execution_proof_dag_binding(parent, execution)
        self.assertTrue(out.certified, out.reason)
        self.assertEqual(out.status, m.OUTPUT_STATUS)
        self.assertTrue(out.same_child_execution_certified)
        self.assertFalse(out.parent_result_identity_equivalence_certified)
        self.assertTrue(m.replay_parent_filtered_execution_proof_dag_binding(out, parent, execution))

    def test_projection_false_positive_filtering_may_make_parent_empty(self):
        parent = parent_result(parent_outcome="filtered_empty")
        execution = execution_result(outcome="nonempty")
        out = m.certify_parent_filtered_execution_proof_dag_binding(parent, execution)
        self.assertTrue(out.certified, out.reason)
        self.assertEqual(out.parent_outcome_kind, "exact_empty")
        self.assertEqual(out.proof_dag_outcome_kind, "nonempty")

    def test_exact_empty_child_execution_requires_exact_empty_parent(self):
        parent = parent_result(parent_outcome="child_empty")
        execution = execution_result(outcome="exact_empty")
        out = m.certify_parent_filtered_execution_proof_dag_binding(parent, execution)
        self.assertTrue(out.certified, out.reason)
        self.assertEqual(out.parent_outcome_kind, "exact_empty")

    def test_exact_empty_child_execution_rejects_nonempty_parent(self):
        out = m.certify_parent_filtered_execution_proof_dag_binding(
            parent_result(), execution_result(outcome="exact_empty")
        )
        self.assertFalse(out.certified)
        self.assertIn("exact-empty", out.reason)

    def test_reduction_identity_mismatch_fails_closed(self):
        out = m.certify_parent_filtered_execution_proof_dag_binding(
            parent_result(), execution_result(reduction=psha("8"))
        )
        self.assertFalse(out.certified)
        self.assertIn("reduction_identity mismatch", out.reason)

    def test_child_result_identity_mismatch_fails_closed(self):
        out = m.certify_parent_filtered_execution_proof_dag_binding(
            parent_result(), execution_result(child_identity=psha("8"))
        )
        self.assertFalse(out.certified)
        self.assertIn("child_result_identity mismatch", out.reason)

    def test_parent_result_identity_tamper_fails_closed(self):
        parent = parent_result() | {"result_identity": psha("0")}
        out = m.certify_parent_filtered_execution_proof_dag_binding(parent, execution_result())
        self.assertFalse(out.certified)
        self.assertIn("result_identity replay failed", out.reason)

    def test_execution_proof_identity_link_tamper_fails_closed(self):
        execution = execution_result()
        execution["proof_identity"] = dict(execution["proof_identity"])
        execution["proof_identity"]["child_result_identity"] = psha("9")
        out = m.certify_parent_filtered_execution_proof_dag_binding(parent_result(), execution)
        self.assertFalse(out.certified)
        self.assertIn("proof_identity child_result_identity mismatch", out.reason)

    def test_unstable_child_proof_identity_fails_closed(self):
        execution = execution_result()
        execution["proof_identity"] = dict(execution["proof_identity"])
        execution["proof_identity"]["child_proof_identity"] = ChildProofIdentity("child", False)
        out = m.certify_parent_filtered_execution_proof_dag_binding(parent_result(), execution)
        self.assertFalse(out.certified)
        self.assertIn("replay_stable", out.reason)

    def test_action_degree_must_equal_execution_child_ground(self):
        execution = execution_result()
        execution["child_ground_size"] = 3
        out = m.certify_parent_filtered_execution_proof_dag_binding(parent_result(), execution)
        self.assertFalse(out.certified)
        self.assertIn("action degree differs", out.reason)

    def test_parent_nonempty_coset_shape_is_checked(self):
        parent = parent_result()
        parent["representative"] = (0, 0, 2, 3)
        payload = {k: parent[k] for k in (
            "schema_version", "status", "reduction_identity", "semantic_binding_identity",
            "child_instance_identity", "child_result_identity", "action_degree", "candidate_count",
            "accepted_count", "representative", "parent_stabilizer_elements", "work_bound"
        )}
        parent["result_identity"] = m._sha256(payload)
        out = m.certify_parent_filtered_execution_proof_dag_binding(parent, execution_result())
        self.assertFalse(out.certified)
        self.assertIn("not a permutation", out.reason)

    def test_binding_identity_is_deterministic_and_tamper_replay_fails(self):
        parent = parent_result()
        execution = execution_result()
        first = m.certify_parent_filtered_execution_proof_dag_binding(parent, execution)
        second = m.certify_parent_filtered_execution_proof_dag_binding(parent, execution)
        self.assertEqual(first.binding_identity, second.binding_identity)
        tampered = replace(first, binding_identity=psha("0"))
        self.assertFalse(m.replay_parent_filtered_execution_proof_dag_binding(tampered, parent, execution))


if __name__ == "__main__":
    unittest.main()
