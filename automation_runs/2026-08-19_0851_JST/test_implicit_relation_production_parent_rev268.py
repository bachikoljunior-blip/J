from __future__ import annotations

import unittest
from dataclasses import dataclass

from implicit_relation_production_parent_v1 import (
    exact_implicit_relation_production_parent,
)


SOURCE = "sha256:" + "1" * 64
TARGET = "sha256:" + "2" * 64


@dataclass
class Resource:
    status: str = "certified_implicit_relation_image_work_bound"
    admitted: bool = True
    complete: bool = False
    root_lift_certified: bool = True
    order_bounds_compatible: bool = True
    image_gate_certified: bool = True
    original_root_degree: int = 20
    domain_degree: int = 6
    auxiliary_degree: int = 12
    work_upper_bound: int = 21
    max_work: int = 30

    @property
    def phase_work_upper_bounds(self):
        return (
            ("induced_action", 1),
            ("domain_schreier", 2),
            ("image_schreier", 3),
            ("value_coset_intersection", 4),
            ("paired_preimage", 5),
            ("verification", 6),
        )


@dataclass
class Artifact:
    status: str
    exact: bool = True
    complete: bool = True
    domain_degree: int = 6
    auxiliary_degree: int = 12
    coset: object | None = None
    outcome_kind: str | None = None
    source_evidence_revision: int | None = None
    source_relation_digest: str | None = None
    target_relation_digest: str | None = None


class Rev268ProductionParentTests(unittest.TestCase):
    def test_nonempty_route_is_ordered_and_returns_parent_coset(self):
        calls = []
        image_coset = object()
        preimage_coset = object()
        parent_coset = object()

        def image():
            calls.append("image")
            return Artifact("exact_implicit_relation_image_value_coset", coset=image_coset)

        def preimage(value):
            calls.append("preimage")
            self.assertIs(value.coset, image_coset)
            return Artifact("exact_original_domain_relation_preimage_coset", coset=preimage_coset)

        def verify(value):
            calls.append("verify")
            self.assertIs(value.coset, preimage_coset)
            return Artifact("exact_implicit_relation_parent_coset", coset=parent_coset)

        def normalize(value):
            calls.append("normalize")
            self.assertIs(value.coset, parent_coset)
            return Artifact(
                "exact_parent_outcome_nonempty",
                outcome_kind="nonempty",
                source_evidence_revision=261,
                source_relation_digest=SOURCE,
                target_relation_digest=TARGET,
            )

        result = exact_implicit_relation_production_parent(
            Resource(),
            expected_source_relation_digest=SOURCE,
            expected_target_relation_digest=TARGET,
            image_solver=image,
            preimage_solver=preimage,
            nonempty_parent_verifier=verify,
            exact_empty_parent_verifier=lambda value: self.fail("empty verifier ran"),
            parent_outcome_normalizer=normalize,
        )
        self.assertEqual(result.status, "exact_implicit_relation_production_parent_coset")
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertEqual(result.outcome_kind, "nonempty")
        self.assertIs(result.parent_coset, parent_coset)
        self.assertEqual(calls, ["image", "preimage", "verify", "normalize"])
        self.assertEqual(
            result.executed_steps,
            (
                "value_coset_intersection",
                "paired_preimage",
                "nonempty_parent_verification",
                "parent_outcome_normalization",
            ),
        )

    def test_exact_empty_route_skips_preimage_and_nonempty_verifier(self):
        calls = []

        def image():
            calls.append("image")
            return Artifact("exact_empty_feature_inventory_mismatch", coset=None)

        def empty_verify(value):
            calls.append("empty_verify")
            self.assertTrue(value.status.startswith("exact_empty_"))
            return Artifact("exact_empty_parent_feature_inventory_mismatch", coset=None)

        def normalize(value):
            calls.append("normalize")
            self.assertEqual(value.status, "exact_empty_parent_feature_inventory_mismatch")
            return Artifact(
                "exact_parent_outcome_empty",
                outcome_kind="exact_empty",
                source_evidence_revision=263,
                source_relation_digest=SOURCE,
                target_relation_digest=TARGET,
                coset=None,
            )

        result = exact_implicit_relation_production_parent(
            Resource(),
            expected_source_relation_digest=SOURCE,
            expected_target_relation_digest=TARGET,
            image_solver=image,
            preimage_solver=lambda value: self.fail("preimage ran"),
            nonempty_parent_verifier=lambda value: self.fail("nonempty verifier ran"),
            exact_empty_parent_verifier=empty_verify,
            parent_outcome_normalizer=normalize,
        )
        self.assertEqual(result.status, "exact_implicit_relation_production_parent_empty")
        self.assertTrue(result.exact)
        self.assertIsNone(result.parent_coset)
        self.assertEqual(calls, ["image", "empty_verify", "normalize"])

    def test_unadmitted_resource_stops_before_semantic_execution(self):
        resource = Resource(admitted=False, status="implicit_relation_image_work_cap_exceeded")
        touched = []
        result = exact_implicit_relation_production_parent(
            resource,
            expected_source_relation_digest=SOURCE,
            expected_target_relation_digest=TARGET,
            image_solver=lambda: touched.append("image"),
            preimage_solver=lambda value: touched.append("preimage"),
            nonempty_parent_verifier=lambda value: touched.append("verify"),
            exact_empty_parent_verifier=lambda value: touched.append("empty"),
            parent_outcome_normalizer=lambda value: touched.append("normalize"),
        )
        self.assertFalse(result.exact)
        self.assertEqual(result.status, "fail_closed_unadmitted_original_root_resource_envelope")
        self.assertEqual(touched, [])
        self.assertEqual(result.executed_steps, ())

    def test_phase_split_must_reconstruct_reserved_work(self):
        resource = Resource(work_upper_bound=20)
        result = exact_implicit_relation_production_parent(
            resource,
            expected_source_relation_digest=SOURCE,
            expected_target_relation_digest=TARGET,
            image_solver=lambda: self.fail("image ran"),
            preimage_solver=lambda value: value,
            nonempty_parent_verifier=lambda value: value,
            exact_empty_parent_verifier=lambda value: value,
            parent_outcome_normalizer=lambda value: value,
        )
        self.assertEqual(result.status, "fail_closed_unadmitted_original_root_resource_envelope")
        self.assertIn("reconstruct", result.reason)

    def test_nonexact_image_result_fails_closed(self):
        result = exact_implicit_relation_production_parent(
            Resource(),
            expected_source_relation_digest=SOURCE,
            expected_target_relation_digest=TARGET,
            image_solver=lambda: Artifact(
                "undetermined_image_partition_work_cap", exact=False, complete=False
            ),
            preimage_solver=lambda value: self.fail("preimage ran"),
            nonempty_parent_verifier=lambda value: self.fail("verify ran"),
            exact_empty_parent_verifier=lambda value: self.fail("empty ran"),
            parent_outcome_normalizer=lambda value: self.fail("normalize ran"),
        )
        self.assertEqual(result.status, "fail_closed_image_result_not_exact_complete")
        self.assertEqual(result.executed_steps, ("value_coset_intersection",))

    def test_normalized_relation_identity_mismatch_is_not_promoted(self):
        image_coset = object()
        parent_coset = object()
        result = exact_implicit_relation_production_parent(
            Resource(),
            expected_source_relation_digest=SOURCE,
            expected_target_relation_digest=TARGET,
            image_solver=lambda: Artifact(
                "exact_implicit_relation_image_value_coset", coset=image_coset
            ),
            preimage_solver=lambda value: Artifact(
                "exact_original_domain_relation_preimage_coset", coset=object()
            ),
            nonempty_parent_verifier=lambda value: Artifact(
                "exact_implicit_relation_parent_coset", coset=parent_coset
            ),
            exact_empty_parent_verifier=lambda value: self.fail("empty ran"),
            parent_outcome_normalizer=lambda value: Artifact(
                "exact_parent_outcome_nonempty",
                outcome_kind="nonempty",
                source_evidence_revision=261,
                source_relation_digest="sha256:" + "3" * 64,
                target_relation_digest=TARGET,
            ),
        )
        self.assertFalse(result.exact)
        self.assertEqual(result.status, "fail_closed_normalized_nonempty_contract")
        self.assertIsNone(result.parent_coset)

    def test_callback_exception_is_contained_fail_closed(self):
        def explode():
            raise RuntimeError("synthetic")

        result = exact_implicit_relation_production_parent(
            Resource(),
            expected_source_relation_digest=SOURCE,
            expected_target_relation_digest=TARGET,
            image_solver=explode,
            preimage_solver=lambda value: value,
            nonempty_parent_verifier=lambda value: value,
            exact_empty_parent_verifier=lambda value: value,
            parent_outcome_normalizer=lambda value: value,
        )
        self.assertEqual(result.status, "fail_closed_image_solver_exception")
        self.assertIn("RuntimeError", result.reason)


if __name__ == "__main__":
    unittest.main()
