from __future__ import annotations

import hashlib
import json
import math
import unittest

from soj_parent_filtered_proof_accounting_coherence_v1 import (
    ACCOUNTING_STATUS,
    PARENT_EMPTY_STATUS,
    PARENT_NONEMPTY_STATUS,
    PROOF_STATUS,
    certify_parent_filtered_proof_accounting_coherence,
    replay_parent_filtered_proof_accounting_coherence,
)


def digest(value):
    return "sha256:" + hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    ).hexdigest()


def sid(label):
    return digest({"id": label})


def accounting_payload(accounting):
    return {k: v for k, v in accounting.items() if k not in {"certified", "exact", "complete", "coherence_identity", "reason"}}


def make_pair(*, empty=False):
    source_status = PARENT_EMPTY_STATUS if empty else PARENT_NONEMPTY_STATUS
    outcome = "exact_empty" if empty else "nonempty"
    candidate_count = 3
    accepted_count = 0 if empty else 2
    representative = None if empty else (1, 0, 2)
    stabilizer_elements = () if empty else ((0, 1, 2), (1, 0, 2))
    lineage = {
        "reduction": sid("reduction"),
        "semantic_binding": sid("semantic"),
        "child_instance": sid("child-instance"),
        "child_result": sid("child-result"),
    }
    source_payload = {
        "schema_version": 1,
        "status": source_status,
        "reduction_identity": lineage["reduction"],
        "semantic_binding_identity": lineage["semantic_binding"],
        "child_instance_identity": lineage["child_instance"],
        "child_result_identity": lineage["child_result"],
        "action_degree": 3,
        "candidate_count": candidate_count,
        "accepted_count": accepted_count,
        "representative": representative,
        "parent_stabilizer_elements": stabilizer_elements,
        "work_bound": 64,
    }
    lineage["parent_filtered_result"] = digest(source_payload)
    nodes = [{"id": f"lineage:{kind}", "kind": kind, "identity": identity} for kind, identity in lineage.items()]
    edges = [
        {"from": "lineage:reduction", "to": "lineage:semantic_binding"},
        {"from": "lineage:semantic_binding", "to": "lineage:child_instance"},
        {"from": "lineage:child_instance", "to": "lineage:child_result"},
        {"from": "lineage:child_result", "to": "lineage:parent_filtered_result"},
    ]
    if not empty:
        nodes.append({
            "id": "witness:representative",
            "kind": "right_coset_representative",
            "identity": digest(("representative", representative)),
            "permutation": list(representative),
        })
        edges.append({"from": "lineage:parent_filtered_result", "to": "witness:representative"})
        for index, perm in enumerate(stabilizer_elements):
            node_id = f"witness:stabilizer:{index:06d}"
            nodes.append({
                "id": node_id,
                "kind": "parent_stabilizer_element",
                "identity": digest(("stabilizer_element", perm)),
                "permutation": list(perm),
            })
            edges.append({"from": "witness:representative", "to": node_id})
    nodes.sort(key=lambda item: item["id"])
    edges.sort(key=lambda item: (item["from"], item["to"]))
    dag = {
        "schema_version": 1,
        "kind": "parent_filtered_result_proof_dag_integrity_v1",
        "source_status": source_status,
        "result_identity": lineage["parent_filtered_result"],
        "action_degree": 3,
        "candidate_count": candidate_count,
        "accepted_count": accepted_count,
        "work_bound": 64,
        "nodes": nodes,
        "edges": edges,
    }
    proof = {
        "schema_version": 1, "status": PROOF_STATUS, "certified": True, "exact": True, "complete": True,
        "source_status": source_status, "result_identity": lineage["parent_filtered_result"], "action_degree": 3,
        "candidate_count": candidate_count, "accepted_count": accepted_count, "node_count": len(nodes), "edge_count": len(edges),
        "proof_dag": dag, "proof_dag_identity": digest(dag), "reason": "fixture",
    }
    account_payload = {
        "schema_version": 1, "status": ACCOUNTING_STATUS, "outcome_kind": outcome,
        "reduction_identity": lineage["reduction"], "semantic_binding_identity": lineage["semantic_binding"],
        "child_instance_identity": lineage["child_instance"], "child_result_identity": lineage["child_result"],
        "parent_result_identity": lineage["parent_filtered_result"], "handoff_digest": sid("handoff"),
        "parent_action_degree": 6, "child_ground_size": 3, "candidate_count": candidate_count,
        "accepted_count": accepted_count, "parent_filter_work_bound": 64, "charged_log2_reduction_cost": 5.0,
    }
    accounting = {**account_payload, "certified": True, "exact": True, "complete": True, "coherence_identity": digest(account_payload), "reason": "fixture"}
    return proof, accounting


class DictSubclass(dict):
    pass


class StringSubclass(str):
    pass


class Rev2800ProofAccountingCoherenceTests(unittest.TestCase):
    def certify(self, proof, accounting, **kwargs):
        return certify_parent_filtered_proof_accounting_coherence(
            proof, accounting,
            proof_replay_verified=kwargs.get("proof_replay_verified", True),
            accounting_replay_verified=kwargs.get("accounting_replay_verified", True),
        )

    def test_nonempty_success_and_replay(self):
        proof, accounting = make_pair()
        cert = self.certify(proof, accounting)
        self.assertTrue(cert.certified, cert.reason)
        self.assertEqual(cert.outcome_kind, "nonempty")
        self.assertTrue(replay_parent_filtered_proof_accounting_coherence(cert, proof, accounting, proof_replay_verified=True, accounting_replay_verified=True))

    def test_exact_empty_success(self):
        proof, accounting = make_pair(empty=True)
        cert = self.certify(proof, accounting)
        self.assertTrue(cert.certified, cert.reason)
        self.assertEqual(cert.outcome_kind, "exact_empty")
        self.assertEqual(cert.accepted_count, 0)

    def test_replay_gates_are_literal_true(self):
        proof, accounting = make_pair()
        self.assertFalse(self.certify(proof, accounting, proof_replay_verified=1).certified)
        self.assertFalse(self.certify(proof, accounting, accounting_replay_verified=1).certified)
        self.assertFalse(self.certify(proof, accounting, proof_replay_verified=False).certified)

    def test_top_level_dict_subclasses_rejected(self):
        proof, accounting = make_pair()
        self.assertFalse(self.certify(DictSubclass(proof), accounting).certified)
        self.assertFalse(self.certify(proof, DictSubclass(accounting)).certified)

    def test_string_subclass_identity_rejected(self):
        proof, accounting = make_pair()
        accounting["reduction_identity"] = StringSubclass(accounting["reduction_identity"])
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_schema_versions_require_strict_integer(self):
        proof, accounting = make_pair()
        proof["schema_version"] = True
        self.assertFalse(self.certify(proof, accounting).certified)

        proof, accounting = make_pair()
        accounting["schema_version"] = True
        self.assertFalse(self.certify(proof, accounting).certified)

        proof, accounting = make_pair()
        proof["proof_dag"]["schema_version"] = True
        proof["proof_dag_identity"] = digest(proof["proof_dag"])
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_proof_dag_digest_tamper_fails(self):
        proof, accounting = make_pair()
        proof["proof_dag"]["work_bound"] = 65
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_proof_hidden_node_with_rehashed_digest_fails(self):
        proof, accounting = make_pair()
        proof["proof_dag"]["nodes"].append({"id": "hidden:x", "kind": "hidden", "identity": sid("hidden")})
        proof["proof_dag"]["nodes"].sort(key=lambda item: item["id"])
        proof["node_count"] += 1
        proof["proof_dag_identity"] = digest(proof["proof_dag"])
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_proof_edge_drift_with_rehashed_digest_fails(self):
        proof, accounting = make_pair()
        proof["proof_dag"]["edges"][0] = {"from": "lineage:reduction", "to": "lineage:child_instance"}
        proof["proof_dag"]["edges"].sort(key=lambda item: (item["from"], item["to"]))
        proof["proof_dag_identity"] = digest(proof["proof_dag"])
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_witness_identity_rehash_cannot_hide_forgery(self):
        proof, accounting = make_pair()
        representative = next(node for node in proof["proof_dag"]["nodes"] if node["id"] == "witness:representative")
        representative["identity"] = sid("forged-representative")
        proof["proof_dag_identity"] = digest(proof["proof_dag"])
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_non_permutation_witness_rehash_fails(self):
        proof, accounting = make_pair()
        representative = next(node for node in proof["proof_dag"]["nodes"] if node["id"] == "witness:representative")
        representative["permutation"] = [0, 0, 2]
        representative["identity"] = digest(("representative", tuple(representative["permutation"])))
        proof["proof_dag_identity"] = digest(proof["proof_dag"])
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_non_subgroup_stabilizer_rehash_fails(self):
        proof, accounting = make_pair()
        witness = next(node for node in proof["proof_dag"]["nodes"] if node["id"] == "witness:stabilizer:000001")
        witness["permutation"] = [1, 2, 0]
        witness["identity"] = digest(("stabilizer_element", tuple(witness["permutation"])))
        proof["proof_dag_identity"] = digest(proof["proof_dag"])
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_lineage_node_extra_field_rehash_fails(self):
        proof, accounting = make_pair()
        lineage = next(node for node in proof["proof_dag"]["nodes"] if node["id"] == "lineage:reduction")
        lineage["unexpected"] = 1
        proof["proof_dag_identity"] = digest(proof["proof_dag"])
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_accounting_identity_replay_fails_on_tamper(self):
        proof, accounting = make_pair()
        accounting["parent_filter_work_bound"] = 63
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_accounting_identity_rehash_cannot_hide_proof_mismatch(self):
        proof, accounting = make_pair()
        accounting["parent_result_identity"] = sid("forged-parent")
        accounting["coherence_identity"] = digest(accounting_payload(accounting))
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_joint_parent_result_identity_forgery_fails_after_full_rehash(self):
        proof, accounting = make_pair()
        forged = sid("forged-parent")
        proof["result_identity"] = forged
        proof["proof_dag"]["result_identity"] = forged
        parent_node = next(node for node in proof["proof_dag"]["nodes"] if node["id"] == "lineage:parent_filtered_result")
        parent_node["identity"] = forged
        proof["proof_dag_identity"] = digest(proof["proof_dag"])
        accounting["parent_result_identity"] = forged
        accounting["coherence_identity"] = digest(accounting_payload(accounting))
        cert = self.certify(proof, accounting)
        self.assertFalse(cert.certified)
        self.assertIn("source replay", cert.reason)

    def test_joint_empty_parent_result_identity_forgery_fails_after_full_rehash(self):
        proof, accounting = make_pair(empty=True)
        forged = sid("forged-empty-parent")
        proof["result_identity"] = forged
        proof["proof_dag"]["result_identity"] = forged
        parent_node = next(node for node in proof["proof_dag"]["nodes"] if node["id"] == "lineage:parent_filtered_result")
        parent_node["identity"] = forged
        proof["proof_dag_identity"] = digest(proof["proof_dag"])
        accounting["parent_result_identity"] = forged
        accounting["coherence_identity"] = digest(accounting_payload(accounting))
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_lineage_reduction_mismatch_fails_even_with_valid_accounting_digest(self):
        proof, accounting = make_pair()
        accounting["reduction_identity"] = sid("other-reduction")
        accounting["coherence_identity"] = digest(accounting_payload(accounting))
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_outcome_mismatch_fails(self):
        proof, accounting = make_pair(empty=True)
        accounting["outcome_kind"] = "nonempty"
        accounting["accepted_count"] = 1
        accounting["coherence_identity"] = digest(accounting_payload(accounting))
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_child_measure_mismatch_fails(self):
        proof, accounting = make_pair()
        accounting["child_ground_size"] = 2
        accounting["coherence_identity"] = digest(accounting_payload(accounting))
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_candidate_or_accepted_count_mismatch_fails(self):
        proof, accounting = make_pair()
        accounting["candidate_count"] = 4
        accounting["coherence_identity"] = digest(accounting_payload(accounting))
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_nonfinite_negative_and_bool_cost_fail(self):
        for value in (math.inf, math.nan, -1.0, True):
            with self.subTest(value=value):
                proof, accounting = make_pair()
                accounting["charged_log2_reduction_cost"] = value
                self.assertFalse(self.certify(proof, accounting).certified)

    def test_non_strict_parent_to_child_shrink_fails(self):
        proof, accounting = make_pair()
        accounting["parent_action_degree"] = 3
        accounting["coherence_identity"] = digest(accounting_payload(accounting))
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_top_level_schema_smuggling_fails(self):
        proof, accounting = make_pair()
        proof["semantic_exactness_promoted"] = True
        self.assertFalse(self.certify(proof, accounting).certified)

        proof, accounting = make_pair()
        accounting["charged_total_cost"] = 0
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_reason_must_be_literal_string(self):
        proof, accounting = make_pair()
        proof["reason"] = StringSubclass("fixture")
        self.assertFalse(self.certify(proof, accounting).certified)

        proof, accounting = make_pair()
        accounting["reason"] = 1
        self.assertFalse(self.certify(proof, accounting).certified)

    def test_output_mutation_breaks_replay(self):
        proof, accounting = make_pair()
        cert = self.certify(proof, accounting)
        self.assertTrue(cert.certified)
        mutated = cert.__class__(**{**cert.__dict__, "handoff_digest": sid("mutated")})
        self.assertFalse(replay_parent_filtered_proof_accounting_coherence(mutated, proof, accounting, proof_replay_verified=True, accounting_replay_verified=True))


if __name__ == "__main__":
    unittest.main()
