from __future__ import annotations

from itertools import combinations
from types import SimpleNamespace
import unittest

import soj_parent_filtered_child_result_v1 as m


RID = "sha256:" + "42" * 32
V = 4
K = 2
VERTICES = tuple(combinations(range(V), K))
GENS = ((1, 0, 2, 3), (1, 2, 3, 0))
RESOURCES = {
    "polylog_power": 2,
    "max_explicit_degree": 8,
    "group_order_poly_power": 2,
    "max_group_order": 4096,
    "max_partition_states": 4096,
    "max_recognition_nodes": 500000,
    "max_depth": 64,
}


def semantic_binding(source, target):
    n = len(VERTICES)
    frozen_source = tuple(m._freeze_value(x) for x in source)
    frozen_target = tuple(m._freeze_value(x) for x in target)
    stars = m._ground_stars(VERTICES, V)
    child_source = tuple(m._profile(frozen_source, star) for star in stars)
    child_target = tuple(m._profile(frozen_target, star) for star in stars)
    semantic_work_bound = 137
    payload = {
        "schema_version": 1,
        "status": m.SEMANTIC_STATUS,
        "profile_kind": m.PROFILE_KIND,
        "source_action_degree": n,
        "child_ground_size": V,
        "johnson_subset_size": K,
        "reduction_identity": RID,
        "parent_source_digest": m._sha256(("parent_string_v1", frozen_source)),
        "parent_target_digest": m._sha256(("parent_string_v1", frozen_target)),
        "child_source_digest": m._sha256((m.PROFILE_KIND, child_source)),
        "child_target_digest": m._sha256((m.PROFILE_KIND, child_target)),
        "child_source_values": child_source,
        "child_target_values": child_target,
        "semantic_work_bound": semantic_work_bound,
        "parent_to_child_transport_certified": True,
        "child_to_parent_transport_certified": False,
        "parent_solution_equivalence_certified": False,
    }
    return SimpleNamespace(
        **payload,
        certified=True,
        canonical=True,
        replay_stable=True,
        binding_identity=m._sha256(payload),
    )


def child_execution(binding):
    ambient = m._enumerate_group(GENS, degree=V, cap=100, name="fixture")
    source = tuple(m._normalize_json(x) for x in binding.child_source_values)
    target = tuple(m._normalize_json(x) for x in binding.child_target_values)
    solutions = tuple(sorted(g for g in ambient if m._transport(source, g) == target))
    if not solutions:
        status = m.CHILD_EMPTY_STATUS
        representative = None
        stabilizer_generators = ()
    else:
        status = m.CHILD_NONEMPTY_STATUS
        representative = min(solutions)
        offsets = tuple(sorted({m._compose(m._inverse(representative), p) for p in solutions}))
        generated = m._enumerate_group(offsets or (m._identity(V),), degree=V, cap=100, name="fixture_offsets")
        assert generated == offsets
        stabilizer_generators = tuple(x for x in offsets if x != m._identity(V))
    result_payload = {
        "schema_version": 1,
        "status": status,
        "exact": True,
        "complete": True,
        "canonical": True,
        "ambient_membership_certified": True,
        "action_degree": V,
        "reduction_identity": RID,
        "representative": representative,
        "stabilizer_generators": stabilizer_generators,
    }
    result = SimpleNamespace(**result_payload, result_identity=m._sha256(result_payload))
    context = {
        "source_action_degree": len(VERTICES),
        "subset_size": K,
        "induced_ground_generators": GENS,
        "child_source_values": binding.child_source_values,
        "child_target_values": binding.child_target_values,
        "original_root_n": len(VERTICES),
        "resources": dict(RESOURCES),
    }
    instance_payload = {
        "schema_version": 1,
        "scope": "corrected-soj-recursive-ground-s1-child-instance-v1",
        "reduction_identity": RID,
        "source_action_degree": len(VERTICES),
        "ground_size": V,
        "subset_size": K,
        "induced_ground_generators": GENS,
        "child_source_values": source,
        "child_target_values": target,
        "original_root_n": len(VERTICES),
        "resources": dict(RESOURCES),
        "child_result_identity": result.result_identity,
    }
    execution = SimpleNamespace(
        schema_version=1,
        status=m.EXECUTION_STATUS,
        certified=True,
        exact=True,
        complete=True,
        action_degree=V,
        reduction_identity=RID,
        child_instance_identity=m._sha256(instance_payload),
        parent_child_semantic_transport_certified=False,
        child_result=result,
    )
    return execution, context, solutions


def certify(source, target, *, cap=100):
    binding = semantic_binding(source, target)
    execution, context, solutions = child_execution(binding)
    out = m.certify_parent_filtered_child_result(
        binding,
        execution,
        execution_context=context,
        canonical_vertex_subsets=VERTICES,
        parent_source_values=source,
        parent_target_values=target,
        max_group_elements=cap,
    )
    return out, binding, execution, context, solutions


class Rev2200ParentFilteredChildResultTests(unittest.TestCase):
    def test_exact_nonempty_parent_filter_returns_reconstructable_right_coset(self):
        source = (0, 1, 2, 3, 4, 5)
        g = (1, 0, 2, 3)
        target = m._transport(source, m._vertex_permutation(VERTICES, g))
        out, _, _, _, child_solutions = certify(source, target)
        self.assertTrue(out.certified, out.reason)
        self.assertEqual(out.status, m.OUTPUT_NONEMPTY_STATUS)
        self.assertGreaterEqual(len(child_solutions), out.accepted_count)
        reconstructed = tuple(sorted(m._compose(out.representative, h) for h in out.parent_stabilizer_elements))
        self.assertEqual(len(reconstructed), out.accepted_count)
        self.assertTrue(out.result_identity.startswith("sha256:"))

    def test_projection_false_positives_are_exactly_filtered(self):
        source = (0, 0, 1, 1, 0, 0)
        target = (0, 1, 0, 0, 1, 0)
        out, _, _, _, child_solutions = certify(source, target)
        self.assertTrue(out.certified, out.reason)
        self.assertEqual(len(child_solutions), 24)
        self.assertEqual(out.candidate_count, 24)
        self.assertEqual(out.accepted_count, 8)
        self.assertLess(out.accepted_count, out.candidate_count)

    def test_exact_empty_child_result_is_preserved(self):
        source = (0, 1, 2, 3, 4, 5)
        target = (0, 1, 2, 3, 4, 99)
        out, _, _, _, child_solutions = certify(source, target)
        self.assertEqual(child_solutions, ())
        self.assertTrue(out.certified, out.reason)
        self.assertEqual(out.status, m.OUTPUT_EMPTY_STATUS)
        self.assertEqual(out.candidate_count, 0)
        self.assertEqual(out.accepted_count, 0)
        self.assertIsNone(out.representative)

    def test_semantic_binding_identity_tamper_fails_closed(self):
        source = (0, 1, 2, 3, 4, 5)
        target = source
        _, binding, execution, context, _ = certify(source, target)
        tampered = SimpleNamespace(**{**vars(binding), "binding_identity": "sha256:" + "00" * 32})
        out = m.certify_parent_filtered_child_result(
            tampered, execution,
            execution_context=context,
            canonical_vertex_subsets=VERTICES,
            parent_source_values=source,
            parent_target_values=target,
            max_group_elements=100,
        )
        self.assertFalse(out.certified)
        self.assertIn("semantic binding identity", out.reason)

    def test_semantic_profile_not_derived_from_parent_fails_closed(self):
        source = (0, 1, 2, 3, 4, 5)
        target = source
        _, binding, execution, context, _ = certify(source, target)
        bad_values = list(binding.child_source_values)
        bad_values[0] = (("tampered", 1),)
        tampered = SimpleNamespace(**{**vars(binding), "child_source_values": tuple(bad_values)})
        out = m.certify_parent_filtered_child_result(
            tampered, execution,
            execution_context=context,
            canonical_vertex_subsets=VERTICES,
            parent_source_values=source,
            parent_target_values=target,
            max_group_elements=100,
        )
        self.assertFalse(out.certified)
        self.assertIn("exact incident-color profile", out.reason)

    def test_child_instance_identity_tamper_fails_closed(self):
        source = (0, 1, 2, 3, 4, 5)
        target = source
        _, binding, execution, context, _ = certify(source, target)
        tampered = SimpleNamespace(**{**vars(execution), "child_instance_identity": "sha256:" + "11" * 32})
        out = m.certify_parent_filtered_child_result(
            binding, tampered,
            execution_context=context,
            canonical_vertex_subsets=VERTICES,
            parent_source_values=source,
            parent_target_values=target,
            max_group_elements=100,
        )
        self.assertFalse(out.certified)
        self.assertIn("child instance identity", out.reason)

    def test_false_exact_child_snapshot_is_rejected(self):
        source = (0, 0, 1, 1, 0, 0)
        target = (0, 1, 0, 0, 1, 0)
        _, binding, execution, context, solutions = certify(source, target)
        self.assertEqual(len(solutions), 24)
        fake_payload = {
            "schema_version": 1,
            "status": m.CHILD_NONEMPTY_STATUS,
            "exact": True,
            "complete": True,
            "canonical": True,
            "ambient_membership_certified": True,
            "action_degree": V,
            "reduction_identity": RID,
            "representative": m._identity(V),
            "stabilizer_generators": (),
        }
        fake_result = SimpleNamespace(**fake_payload, result_identity=m._sha256(fake_payload))
        source_ctx = tuple(m._normalize_json(x) for x in binding.child_source_values)
        target_ctx = tuple(m._normalize_json(x) for x in binding.child_target_values)
        instance_payload = {
            "schema_version": 1,
            "scope": "corrected-soj-recursive-ground-s1-child-instance-v1",
            "reduction_identity": RID,
            "source_action_degree": len(VERTICES),
            "ground_size": V,
            "subset_size": K,
            "induced_ground_generators": GENS,
            "child_source_values": source_ctx,
            "child_target_values": target_ctx,
            "original_root_n": len(VERTICES),
            "resources": dict(RESOURCES),
            "child_result_identity": fake_result.result_identity,
        }
        fake_execution = SimpleNamespace(**{
            **vars(execution),
            "child_result": fake_result,
            "child_instance_identity": m._sha256(instance_payload),
        })
        out = m.certify_parent_filtered_child_result(
            binding, fake_execution,
            execution_context=context,
            canonical_vertex_subsets=VERTICES,
            parent_source_values=source,
            parent_target_values=target,
            max_group_elements=100,
        )
        self.assertFalse(out.certified)
        self.assertIn("not the exact child transporter set", out.reason)

    def test_group_cap_fails_closed_before_unbounded_enumeration(self):
        source = (0, 1, 2, 3, 4, 5)
        target = source
        out, binding, execution, context, _ = certify(source, target)
        self.assertTrue(out.certified)
        capped = m.certify_parent_filtered_child_result(
            binding, execution,
            execution_context=context,
            canonical_vertex_subsets=VERTICES,
            parent_source_values=source,
            parent_target_values=target,
            max_group_elements=5,
        )
        self.assertFalse(capped.certified)
        self.assertIn("exceeds explicit cap", capped.reason)

    def test_noncanonical_vertex_family_fails_closed(self):
        source = (0, 1, 2, 3, 4, 5)
        target = source
        _, binding, execution, context, _ = certify(source, target)
        bad_vertices = tuple(reversed(VERTICES))
        out = m.certify_parent_filtered_child_result(
            binding, execution,
            execution_context=context,
            canonical_vertex_subsets=bad_vertices,
            parent_source_values=source,
            parent_target_values=target,
            max_group_elements=100,
        )
        self.assertFalse(out.certified)
        self.assertIn("complete canonical", out.reason)


if __name__ == "__main__":
    unittest.main()
