from __future__ import annotations

import hashlib
import json
import unittest
from dataclasses import dataclass, replace

from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from soj_recursive_production_execution_proof_dag_v1 import (
    certify_recursive_production_execution_proof_dag,
    replay_recursive_production_execution_proof_dag,
)


def _hash(payload, *, ascii_only: bool) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=ascii_only,
        allow_nan=False,
    ).encode("ascii" if ascii_only else "utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _psha(ch: str) -> str:
    return "sha256:" + ch * 64


@dataclass(frozen=True)
class StableChildIdentity:
    token: str
    replay_stable: bool = True


class Rev1400ExecutionProofDAGTests(unittest.TestCase):
    def _case(
        self,
        *,
        outcome: str = "nonempty",
        parent_degree: int = 6,
        child_degree: int = 4,
        source=None,
        target=None,
        parent_generators=None,
    ):
        root_n = parent_degree
        child_rep = identity(child_degree)
        child_gens = (identity(child_degree),)
        child_payload = {
            "schema_version": 1,
            "status": "exact_recursive_ground_coset" if outcome == "nonempty" else "exact_empty_recursive_ground_coset",
            "exact": True,
            "complete": True,
            "canonical": True,
            "ambient_membership_certified": True,
            "action_degree": child_degree,
            "reduction_identity": _psha("1"),
            "representative": child_rep if outcome == "nonempty" else None,
            "stabilizer_generators": child_gens if outcome == "nonempty" else (),
        }
        child_result_identity = _hash(child_payload, ascii_only=False)
        child_evidence = child_payload | {"result_identity": child_result_identity}

        source = tuple([0] * parent_degree) if source is None else tuple(source)
        target = tuple(source) if target is None else tuple(target)
        parent_rep = identity(parent_degree)
        if parent_generators is None:
            parent_generators = (identity(parent_degree),)
        parent_values_digest = _hash({"source": source, "target": target}, ascii_only=False)
        lift_payload = {
            "schema_version": 1,
            "status": "certified_exact_parent_johnson_coset_lift" if outcome == "nonempty" else "certified_exact_empty_parent_johnson_result",
            "reduction_identity": _psha("1"),
            "child_result_identity": child_result_identity,
            "parent_values_digest": parent_values_digest,
            "parent_action_degree": parent_degree,
            "child_ground_size": child_degree,
        }
        if outcome == "nonempty":
            lift_payload |= {
                "parent_representative": parent_rep,
                "parent_stabilizer_generators": tuple(parent_generators),
            }
        result_lift_digest = _hash(lift_payload, ascii_only=False)
        lift = {
            "schema_version": 1,
            "status": lift_payload["status"],
            "certified": True,
            "exact": True,
            "complete": True,
            "parent_action_degree": parent_degree,
            "child_ground_size": child_degree,
            "reduction_identity": _psha("1"),
            "child_result_identity": child_result_identity,
            "parent_representative": parent_rep if outcome == "nonempty" else None,
            "parent_stabilizer_generators": tuple(parent_generators) if outcome == "nonempty" else (),
            "transcript_digest": result_lift_digest,
        }

        closure_payload = {
            "schema_version": 1,
            "status": "certified_corrected_soj_recursive_production_lineage_closure",
            "main_commit_sha": "a" * 40,
            "main_provenance_identity": "b" * 64,
            "caller_binding_identity": "c" * 64,
            "caller_replay_envelope_identity": "d" * 64,
            "outcome_kind": outcome,
            "parent_action_degree": parent_degree,
            "child_ground_size": child_degree,
            "reduction_identity": _psha("1"),
            "production_provenance_identity": _psha("2"),
            "recursive_provenance_identity": _psha("3"),
            "result_lift_digest": result_lift_digest,
            "accounting_binding_digest": _psha("4"),
            "child_result_identity": child_result_identity,
            "coherence_identity": _psha("5"),
            "construction_cost_binding_identity": _psha("6"),
            "construction_multiplicative_cost_bound": 2.0,
            "charged_log2_reduction_cost": 1.0,
            "total_cost_binding_identity": _psha("7"),
            "post_replay_envelope_identity": _psha("8"),
            "main_post_replay_seal_identity": _psha("9"),
        }
        closure = closure_payload | {
            "certified": True,
            "exact": True,
            "complete": True,
            "closure_identity": _hash(closure_payload, ascii_only=True),
            "reason": "fixture",
        }

        child_accounting = RecurrenceAccountingNode(
            n=root_n,
            m=child_degree,
            operation_kind="fixture_exact_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=0.0,
            children=(),
            terminal_certified=True,
            reason="fixture exact terminal",
        )
        if outcome == "nonempty":
            child_group = schreier_stabilizer_chain(child_gens)
            child_coset = RightCoset(child_group, child_rep)
        else:
            child_coset = None
        child_proof = ProofCarryingCoset(
            "fixture_exact_child",
            child_coset,
            "fixture_exact_terminal",
            root_n,
            child_degree,
            True,
            True,
            True,
            0.0,
            True,
            (),
            child_accounting,
            0,
            "fixture exact child",
            StableChildIdentity("child"),
        )
        kwargs = dict(
            parent_source_values=source,
            parent_target_values=target,
            original_root_n=root_n,
        )
        return closure, child_evidence, lift, child_proof, kwargs

    def _certify(self, *case, **extra):
        closure, child, lift, proof, kwargs = case
        kwargs = kwargs | extra
        return certify_recursive_production_execution_proof_dag(
            closure, child, lift, proof, **kwargs
        )

    def test_nonempty_execution_composes_and_replays(self):
        case = self._case()
        result = self._certify(*case)
        self.assertTrue(result.certified, result.reason)
        self.assertEqual(result.status, "certified_recursive_production_execution_parent_coset")
        self.assertTrue(result.validation.certified)
        self.assertEqual(result.validation.execution_occurrences, 2)
        self.assertTrue(
            replay_recursive_production_execution_proof_dag(result, case[0], case[1], case[2], case[3], **case[4])
        )

    def test_exact_empty_execution_composes(self):
        result = self._certify(*self._case(outcome="exact_empty"))
        self.assertTrue(result.certified, result.reason)
        self.assertEqual(result.status, "certified_recursive_production_execution_parent_empty")
        self.assertIsNone(result.proof.coset)

    def test_closure_identity_tamper_fails_closed(self):
        closure, child, lift, proof, kwargs = self._case()
        closure = closure | {"closure_identity": _psha("0")}
        result = certify_recursive_production_execution_proof_dag(closure, child, lift, proof, **kwargs)
        self.assertFalse(result.certified)
        self.assertIn("closure_identity", result.reason)

    def test_child_result_identity_tamper_fails_closed(self):
        closure, child, lift, proof, kwargs = self._case()
        child = child | {"result_identity": _psha("0")}
        result = certify_recursive_production_execution_proof_dag(closure, child, lift, proof, **kwargs)
        self.assertFalse(result.certified)
        self.assertIn("child result_identity", result.reason)

    def test_result_lift_digest_tamper_fails_closed(self):
        closure, child, lift, proof, kwargs = self._case()
        lift = lift | {"transcript_digest": _psha("0")}
        result = certify_recursive_production_execution_proof_dag(closure, child, lift, proof, **kwargs)
        self.assertFalse(result.certified)
        self.assertIn("transcript", result.reason)

    def test_unstable_child_proof_identity_fails_closed(self):
        closure, child, lift, proof, kwargs = self._case()
        proof = replace(proof, proof_identity=object())
        result = certify_recursive_production_execution_proof_dag(closure, child, lift, proof, **kwargs)
        self.assertFalse(result.certified)
        self.assertIn("replay-stable", result.reason)

    def test_concrete_child_coset_mismatch_fails_closed(self):
        closure, child, lift, proof, kwargs = self._case()
        swap = (1, 0, 2, 3)
        subgroup = schreier_stabilizer_chain((identity(4),))
        proof = replace(proof, coset=RightCoset(subgroup, swap))
        result = certify_recursive_production_execution_proof_dag(closure, child, lift, proof, **kwargs)
        self.assertFalse(result.certified)
        self.assertIn("child proof coset differs", result.reason)

    def test_aux_shrink_threshold_is_enforced(self):
        result = self._certify(*self._case(parent_degree=11, child_degree=10))
        self.assertFalse(result.certified)
        self.assertIn("aux_shrink", result.reason)

    def test_parent_transport_is_rechecked_not_just_hashed(self):
        source = (0, 1, 2, 3, 4, 5)
        target = (1, 0, 2, 3, 4, 5)
        result = self._certify(*self._case(source=source, target=target))
        self.assertFalse(result.certified)
        self.assertIn("does not transport", result.reason)

    def test_parent_stabilizer_is_rechecked_not_just_hashed(self):
        values = (0, 1, 2, 3, 4, 5)
        swap = (1, 0, 2, 3, 4, 5)
        result = self._certify(*self._case(source=values, target=values, parent_generators=(swap,)))
        self.assertFalse(result.certified)
        self.assertIn("does not stabilize", result.reason)

    def test_child_accounting_measure_mismatch_fails_closed(self):
        closure, child, lift, proof, kwargs = self._case()
        bad_accounting = replace(proof.accounting, m=3)
        proof = replace(proof, accounting=bad_accounting)
        result = certify_recursive_production_execution_proof_dag(closure, child, lift, proof, **kwargs)
        self.assertFalse(result.certified)
        self.assertIn("accounting measures", result.reason)

    def test_external_cost_can_make_shared_envelope_fail(self):
        result = self._certify(*self._case(), external_log2_cost_bound=10**12)
        self.assertFalse(result.certified)
        self.assertIsNotNone(result.validation)
        self.assertEqual(result.validation.status, "proof_dag_quasipolynomial_envelope_exceeded")

    def test_original_root_must_dominate_parent(self):
        closure, child, lift, proof, kwargs = self._case()
        kwargs = kwargs | {"original_root_n": 5}
        proof = replace(proof, root_n=5, accounting=replace(proof.accounting, n=5))
        result = certify_recursive_production_execution_proof_dag(closure, child, lift, proof, **kwargs)
        self.assertFalse(result.certified)
        self.assertIn("dominate", result.reason)


if __name__ == "__main__":
    unittest.main()
