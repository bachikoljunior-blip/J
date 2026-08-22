from __future__ import annotations

from dataclasses import replace
from itertools import combinations
from types import SimpleNamespace
import unittest

from soj_recursive_child_instance_execution_v1 import (
    CHILD_EMPTY_STATUS,
    CHILD_NONEMPTY_STATUS,
    OUTPUT_STATUS,
    execute_recursive_ground_s1_child_instance,
)
from s1_proof_identity_v1 import S1ProofIdentity


RID = "sha256:" + "4a" * 32


def reduction(**overrides):
    base = dict(
        schema_version=1,
        status="certified_johnson_ground_relational_reduction",
        certified=True,
        canonical=True,
        exact=True,
        progress_certified=True,
        solution_transport_certified=True,
        ambient_membership_transport_certified=True,
        complement_ambiguity_handled=True,
        source_action_degree=6,
        johnson_ground_size=4,
        johnson_subset_size=2,
        child_ground_size=4,
        reduction_identity=RID,
        canonical_vertex_subsets=tuple(combinations(range(4), 2)),
        induced_ground_generators=((0, 1, 2, 3),),
        construction_work_bound=61,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def run(red=None, source=(0, 1, 2, 3), target=(0, 1, 2, 3), **kwargs):
    return execute_recursive_ground_s1_child_instance(
        reduction() if red is None else red,
        reduction_replay_verified=True,
        child_source_values=source,
        child_target_values=target,
        original_root_n=6,
        **kwargs,
    )


class Rev1500RecursiveChildInstanceExecutionTests(unittest.TestCase):
    def test_exact_nonempty_executes_real_s1_and_emits_rev293_shape(self):
        out = run()
        self.assertTrue(out.certified, out.reason)
        self.assertEqual(out.status, OUTPUT_STATUS)
        self.assertTrue(out.exact)
        self.assertTrue(out.complete)
        self.assertFalse(out.parent_child_semantic_transport_certified)
        self.assertEqual(out.action_degree, 4)
        self.assertEqual(out.reduction_identity, RID)
        self.assertIsNotNone(out.child_proof)
        self.assertIsInstance(out.child_proof.proof_identity, S1ProofIdentity)
        self.assertTrue(out.child_proof.proof_identity.replay_stable)
        self.assertIsNotNone(out.child_result)
        self.assertEqual(out.child_result.status, CHILD_NONEMPTY_STATUS)
        self.assertEqual(out.child_result.action_degree, 4)
        self.assertEqual(out.child_result.reduction_identity, RID)
        self.assertTrue(out.child_result.result_identity.startswith("sha256:"))
        self.assertIsNotNone(out.child_result.representative)

    def test_exact_empty_is_preserved(self):
        out = run(source=(0, 1, 2, 3), target=(1, 0, 2, 3))
        self.assertTrue(out.certified, out.reason)
        self.assertIsNotNone(out.child_result)
        self.assertEqual(out.child_result.status, CHILD_EMPTY_STATUS)
        self.assertIsNone(out.child_result.representative)
        self.assertEqual(out.child_result.stabilizer_generators, ())

    def test_deterministic_execution_binding_identity(self):
        a = run()
        b = run()
        self.assertTrue(a.certified and b.certified)
        self.assertEqual(a.child_instance_identity, b.child_instance_identity)
        self.assertEqual(a.child_result.result_identity, b.child_result.result_identity)

    def test_resource_change_changes_instance_identity(self):
        a = run(max_partition_states=64)
        b = run(max_partition_states=65)
        self.assertTrue(a.certified and b.certified)
        self.assertNotEqual(a.child_instance_identity, b.child_instance_identity)
        self.assertNotEqual(a.child_proof.proof_identity, b.child_proof.proof_identity)

    def test_reduction_must_be_independently_replayed(self):
        out = execute_recursive_ground_s1_child_instance(
            reduction(),
            reduction_replay_verified=False,
            child_source_values=(0, 1, 2, 3),
            child_target_values=(0, 1, 2, 3),
            original_root_n=6,
        )
        self.assertFalse(out.certified)
        self.assertIn("independently replay-verified", out.reason)

    def test_reduction_flags_are_literal_true(self):
        out = run(reduction(certified=1))
        self.assertFalse(out.certified)
        self.assertIn("literal true", out.reason)

    def test_complete_johnson_vertex_family_is_required(self):
        out = run(reduction(canonical_vertex_subsets=((0, 1),) * 6))
        self.assertFalse(out.certified)
        self.assertIn("complete J(v,k)", out.reason)

    def test_ground_generator_must_be_a_permutation(self):
        out = run(reduction(induced_ground_generators=((0, 0, 2, 3),)))
        self.assertFalse(out.certified)
        self.assertIn("not a permutation", out.reason)

    def test_strict_parent_to_child_shrink_is_required(self):
        out = run(
            reduction(
                source_action_degree=4,
                johnson_ground_size=4,
                johnson_subset_size=2,
                child_ground_size=4,
            )
        )
        self.assertFalse(out.certified)
        self.assertIn("inconsistent", out.reason)

    def test_child_values_must_cover_exact_ground(self):
        out = run(source=(0, 1, 2))
        self.assertFalse(out.certified)
        self.assertIn("exactly 4", out.reason)

    def test_opaque_child_values_fail_before_execution_identity(self):
        out = run(source=(object(), 1, 2, 3))
        self.assertFalse(out.certified)
        self.assertIn("replay-stable JSON", out.reason)

    def test_original_root_must_dominate_parent_action(self):
        out = execute_recursive_ground_s1_child_instance(
            reduction(),
            reduction_replay_verified=True,
            child_source_values=(0, 1, 2, 3),
            child_target_values=(0, 1, 2, 3),
            original_root_n=5,
        )
        self.assertFalse(out.certified)
        self.assertIn("dominate the parent", out.reason)

    def test_invalid_resource_gate_fails_closed(self):
        out = run(max_partition_states=0)
        self.assertFalse(out.certified)
        self.assertIn("max_partition_states", out.reason)

    def test_reduction_identity_format_is_strict(self):
        out = run(reduction(reduction_identity="not-a-digest"))
        self.assertFalse(out.certified)
        self.assertIn("reduction_identity", out.reason)

    def test_semantic_parent_child_bridge_is_never_fabricated(self):
        out = run()
        self.assertTrue(out.certified)
        self.assertFalse(out.parent_child_semantic_transport_certified)
        self.assertIn("remain deliberately uncertified", out.reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
