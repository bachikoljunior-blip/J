from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import combinations
import unittest

from corrected_soj_johnson_recursive_result_lift_v1 import (
    RecursiveGroundExactResultEvidence,
    certify_johnson_recursive_child_result_lift,
    child_result_identity,
    replay_johnson_recursive_child_result_lift,
)


@dataclass(frozen=True)
class ReductionFixture:
    status: str
    certified: bool
    canonical: bool
    exact: bool
    progress_certified: bool
    solution_transport_certified: bool
    ambient_membership_transport_certified: bool
    complement_ambiguity_handled: bool
    source_action_degree: int
    johnson_ground_size: int
    johnson_subset_size: int
    child_ground_size: int
    reduction_identity: str
    canonical_vertex_subsets: tuple[tuple[int, ...], ...]


def reduction_fixture(v: int = 5, k: int = 2) -> ReductionFixture:
    subsets = tuple(combinations(range(v), k))
    return ReductionFixture(
        "certified_johnson_ground_relational_reduction",
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        len(subsets),
        v,
        k,
        v,
        "sha256:" + "1" * 64,
        subsets,
    )


def ground_perm_swap01(v: int = 5) -> tuple[int, ...]:
    return (1, 0, *range(2, v))


def lift(perm: tuple[int, ...], subsets: tuple[tuple[int, ...], ...]) -> tuple[int, ...]:
    lookup = {subset: i for i, subset in enumerate(subsets)}
    return tuple(lookup[tuple(sorted(perm[p] for p in subset))] for subset in subsets)


def child_nonempty(reduction: ReductionFixture, *, representative=None, generators=()) -> RecursiveGroundExactResultEvidence:
    representative = representative or tuple(range(reduction.johnson_ground_size))
    draft = RecursiveGroundExactResultEvidence(
        1,
        "exact_recursive_ground_coset",
        True,
        True,
        True,
        True,
        reduction.johnson_ground_size,
        reduction.reduction_identity,
        tuple(representative),
        tuple(generators),
        "sha256:" + "0" * 64,
    )
    return replace(draft, result_identity=child_result_identity(draft))


def child_empty(reduction: ReductionFixture) -> RecursiveGroundExactResultEvidence:
    draft = RecursiveGroundExactResultEvidence(
        1,
        "exact_empty_recursive_ground_coset",
        True,
        True,
        True,
        True,
        reduction.johnson_ground_size,
        reduction.reduction_identity,
        None,
        (),
        "sha256:" + "0" * 64,
    )
    return replace(draft, result_identity=child_result_identity(draft))


class Rev293JohnsonRecursiveResultLiftTest(unittest.TestCase):
    def setUp(self):
        self.reduction = reduction_fixture()
        self.subsets = self.reduction.canonical_vertex_subsets
        self.source = tuple(range(len(self.subsets)))

    def call(self, child, source=None, target=None, **kwargs):
        source = self.source if source is None else source
        target = source if target is None else target
        return certify_johnson_recursive_child_result_lift(
            self.reduction,
            child,
            reduction_replay_verified=kwargs.pop("reduction_replay_verified", True),
            parent_source_values=source,
            parent_target_values=target,
            **kwargs,
        )

    def test_identity_child_lifts_exact_parent_coset(self):
        result = self.call(child_nonempty(self.reduction))
        self.assertTrue(result.certified)
        self.assertEqual(result.status, "certified_exact_parent_johnson_coset_lift")
        self.assertEqual(result.parent_representative, tuple(range(len(self.subsets))))
        self.assertTrue(result.exact and result.complete)

    def test_nontrivial_ground_representative_transports_parent_string(self):
        p = ground_perm_swap01()
        parent_p = lift(p, self.subsets)
        target = [None] * len(self.source)
        for i, image in enumerate(parent_p):
            target[image] = self.source[i]
        result = self.call(child_nonempty(self.reduction, representative=p), target=tuple(target))
        self.assertTrue(result.certified)
        self.assertEqual(result.parent_representative, parent_p)

    def test_nontrivial_target_stabilizer_is_verified_after_lift(self):
        p = ground_perm_swap01()
        source = tuple(0 for _ in self.subsets)
        result = self.call(child_nonempty(self.reduction, generators=(p,)), source=source, target=source)
        self.assertTrue(result.certified)
        self.assertEqual(result.parent_stabilizer_generators, (lift(p, self.subsets),))

    def test_exact_empty_child_promotes_parent_empty(self):
        result = self.call(child_empty(self.reduction))
        self.assertTrue(result.certified)
        self.assertEqual(result.status, "certified_exact_empty_parent_johnson_result")
        self.assertIsNone(result.parent_representative)

    def test_reduction_must_be_independently_replayed(self):
        result = self.call(child_nonempty(self.reduction), reduction_replay_verified=False)
        self.assertFalse(result.certified)
        self.assertIn("replay-verified", result.reason)

    def test_reduction_transport_gate_is_fail_closed(self):
        self.reduction = replace(self.reduction, solution_transport_certified=False)
        result = self.call(child_nonempty(self.reduction))
        self.assertFalse(result.certified)
        self.assertIn("solution_transport_certified", result.reason)

    def test_incomplete_johnson_vertex_family_is_rejected(self):
        self.reduction = replace(self.reduction, canonical_vertex_subsets=self.subsets[:-1])
        result = self.call(child_nonempty(self.reduction))
        self.assertFalse(result.certified)
        self.assertIn("length", result.reason)

    def test_child_must_bind_same_reduction_identity(self):
        child = child_nonempty(self.reduction)
        child = replace(child, reduction_identity="sha256:" + "2" * 64)
        child = replace(child, result_identity=child_result_identity(child))
        result = self.call(child)
        self.assertFalse(result.certified)
        self.assertIn("same reduction identity", result.reason)

    def test_tampered_child_identity_is_rejected(self):
        child = replace(child_nonempty(self.reduction), result_identity="sha256:" + "f" * 64)
        result = self.call(child)
        self.assertFalse(result.certified)
        self.assertIn("does not replay", result.reason)

    def test_noncanonical_generator_order_is_rejected(self):
        ident = tuple(range(5))
        swap = ground_perm_swap01()
        child = child_nonempty(self.reduction, generators=(swap, ident))
        result = self.call(child, source=tuple(0 for _ in self.subsets), target=tuple(0 for _ in self.subsets))
        self.assertFalse(result.certified)
        self.assertIn("lexicographically canonical", result.reason)

    def test_lifted_representative_must_transport_original_parent_values(self):
        p = ground_perm_swap01()
        result = self.call(child_nonempty(self.reduction, representative=p))
        self.assertFalse(result.certified)
        self.assertIn("does not transport", result.reason)

    def test_lifted_generator_must_stabilize_original_parent_target(self):
        p = ground_perm_swap01()
        child = child_nonempty(self.reduction, generators=(p,))
        result = self.call(child)
        self.assertFalse(result.certified)
        self.assertIn("does not stabilize", result.reason)

    def test_opaque_parent_values_fail_closed(self):
        opaque = tuple(object() for _ in self.subsets)
        result = self.call(child_nonempty(self.reduction), source=opaque, target=opaque)
        self.assertFalse(result.certified)
        self.assertIn("replay-stable JSON", result.reason)

    def test_nonfinite_parent_values_fail_closed(self):
        values = list(self.source)
        values[0] = float("nan")
        result = self.call(child_nonempty(self.reduction), source=tuple(values), target=tuple(values))
        self.assertFalse(result.certified)
        self.assertIn("finite", result.reason)

    def test_replay_detects_certificate_tampering(self):
        child = child_nonempty(self.reduction)
        result = self.call(child)
        self.assertTrue(
            replay_johnson_recursive_child_result_lift(
                result,
                self.reduction,
                child,
                reduction_replay_verified=True,
                parent_source_values=self.source,
                parent_target_values=self.source,
            )
        )
        tampered = replace(result, parent_action_degree=result.parent_action_degree + 1)
        self.assertFalse(
            replay_johnson_recursive_child_result_lift(
                tampered,
                self.reduction,
                child,
                reduction_replay_verified=True,
                parent_source_values=self.source,
                parent_target_values=self.source,
            )
        )


if __name__ == "__main__":
    unittest.main()
