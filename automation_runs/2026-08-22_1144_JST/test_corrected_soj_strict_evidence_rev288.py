from __future__ import annotations

from dataclasses import replace
from math import comb
from types import SimpleNamespace
import unittest

from corrected_soj_strict_evidence_v1 import (
    StrictCorrectedSOJEvidenceError,
    normalize_corrected_soj_johnson_evidence,
    replay_corrected_soj_johnson_evidence,
)


V = 7
K = 2
M = comb(V, K)
ROOT = 64
CURRENT = 32


def transition(**overrides):
    payload = {
        "status": "certified_corrected_soj_explicit_johnson_embedding",
        "transition_kind": "johnson_embedding",
        "theorem_input_gate": True,
        "canonical": True,
        "exact": True,
        "progress_certified": True,
        "multiplicative_cost": 8.0,
        "max_multiplicative_cost": 16.0,
        "johnson_ground_size": V,
        "johnson_subset_size": K,
        "johnson_vertex_count": M,
        "reason": "full Johnson embedding certified upstream",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def terminal(**overrides):
    payload = {
        "status": "exact_primitive_johnson_ground_coset",
        "operation_kind": "primitive_johnson_ground_terminal",
        "root_n": ROOT,
        "domain_size": M,
        "canonical": True,
        "exact": True,
        "local_cost_certified": True,
        "local_log2_cost_bound": 17.25,
        "terminal_certified": True,
        "johnson_ground_size": V,
        "johnson_subset_size": K,
        "ground_permutations_checked": 5040,
        "recognition_search_nodes": 12,
        "proof_identity": "primitive-johnson-fixture-v1",
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


class StrictCorrectedSOJEvidenceTests(unittest.TestCase):
    def assert_rejected(self, t=None, q=None, **kwargs):
        with self.assertRaises(StrictCorrectedSOJEvidenceError):
            normalize_corrected_soj_johnson_evidence(
                t or transition(),
                q or terminal(),
                root_n=kwargs.get("root_n", ROOT),
                current_domain_size=kwargs.get("current_domain_size", CURRENT),
            )

    def test_valid_evidence_normalizes_and_replays(self):
        t = transition()
        q = terminal()
        bundle = normalize_corrected_soj_johnson_evidence(
            t, q, root_n=ROOT, current_domain_size=CURRENT
        )
        self.assertEqual(bundle.full_johnson_vertex_count, M)
        self.assertTrue(bundle.replay_stable_upstream_identity)
        self.assertEqual(len(bundle.evidence_identity), 64)
        self.assertTrue(
            replay_corrected_soj_johnson_evidence(
                bundle, t, q, root_n=ROOT, current_domain_size=CURRENT
            )
        )

    def test_mapping_evidence_is_supported_without_coercion(self):
        t = vars(transition()).copy()
        q = vars(terminal()).copy()
        bundle = normalize_corrected_soj_johnson_evidence(
            t, q, root_n=ROOT, current_domain_size=CURRENT
        )
        self.assertEqual(bundle.transition.johnson_ground_size, V)

    def test_numeric_string_ground_is_rejected(self):
        self.assert_rejected(t=transition(johnson_ground_size=str(V)))

    def test_fractional_integer_field_is_rejected(self):
        self.assert_rejected(t=transition(johnson_subset_size=2.0))

    def test_bool_integer_field_is_rejected(self):
        self.assert_rejected(t=transition(johnson_vertex_count=True))

    def test_string_boolean_is_rejected(self):
        self.assert_rejected(t=transition(exact="false"))

    def test_integer_boolean_is_rejected(self):
        self.assert_rejected(q=terminal(terminal_certified=1))

    def test_nan_transition_cost_is_rejected(self):
        self.assert_rejected(t=transition(multiplicative_cost=float("nan")))

    def test_infinite_transition_bound_is_rejected(self):
        self.assert_rejected(t=transition(max_multiplicative_cost=float("inf")))

    def test_huge_integer_transition_cost_fails_closed(self):
        self.assert_rejected(t=transition(multiplicative_cost=10**10000))

    def test_huge_integer_terminal_cost_fails_closed(self):
        self.assert_rejected(q=terminal(local_log2_cost_bound=10**10000))

    def test_actual_cost_above_bound_is_rejected(self):
        self.assert_rejected(
            t=transition(multiplicative_cost=17.0, max_multiplicative_cost=16.0)
        )

    def test_partial_johnson_vertex_count_is_rejected(self):
        self.assert_rejected(t=transition(johnson_vertex_count=M - 1))

    def test_terminal_root_mismatch_is_rejected(self):
        self.assert_rejected(q=terminal(root_n=ROOT + 1))

    def test_terminal_domain_mismatch_is_rejected(self):
        self.assert_rejected(q=terminal(domain_size=M - 1))

    def test_terminal_fractional_subset_size_is_rejected(self):
        self.assert_rejected(q=terminal(johnson_subset_size=2.0))

    def test_negative_execution_counter_is_rejected(self):
        self.assert_rejected(q=terminal(recognition_search_nodes=-1))

    def test_nonexact_terminal_status_is_rejected(self):
        self.assert_rejected(q=terminal(status="undetermined_johnson_ground_cap"))

    def test_empty_terminal_identity_is_rejected(self):
        self.assert_rejected(q=terminal(proof_identity=""))

    def test_missing_terminal_identity_is_allowed_but_marked_non_replay_stable_upstream(self):
        bundle = normalize_corrected_soj_johnson_evidence(
            transition(), terminal(proof_identity=None), root_n=ROOT, current_domain_size=CURRENT
        )
        self.assertFalse(bundle.replay_stable_upstream_identity)
        self.assertEqual(len(bundle.evidence_identity), 64)

    def test_non_strict_domain_reduction_is_rejected(self):
        self.assert_rejected(current_domain_size=M)

    def test_boolean_root_is_rejected(self):
        self.assert_rejected(root_n=True)

    def test_replay_rejects_tampered_bundle(self):
        t = transition()
        q = terminal()
        bundle = normalize_corrected_soj_johnson_evidence(
            t, q, root_n=ROOT, current_domain_size=CURRENT
        )
        tampered = replace(bundle, evidence_identity="0" * 64)
        self.assertFalse(
            replay_corrected_soj_johnson_evidence(
                tampered, t, q, root_n=ROOT, current_domain_size=CURRENT
            )
        )


if __name__ == "__main__":
    unittest.main()
