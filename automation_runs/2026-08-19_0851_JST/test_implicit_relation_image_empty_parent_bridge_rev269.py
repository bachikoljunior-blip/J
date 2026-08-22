import dataclasses
import types
import unittest

from bounded_arity_relation_image_solver import BoundedArityRelationImage, RelationSpec
from implicit_relation_image_action_v1 import prepare_implicit_relation_image_action
from implicit_relation_image_empty_parent_bridge_v1 import (
    SOURCE_REVISION,
    SOURCE_STATUS,
    certify_exact_empty_image_parent_outcome,
)
from implicit_relation_parent_outcome_v1 import ParentExactOutcomeContract


SOURCE_DIGEST = "sha256:" + "1" * 64
TARGET_DIGEST = "sha256:" + "2" * 64
IMAGE_DIGEST = "sha256:" + "3" * 64
PREIMAGE_DIGEST = "sha256:" + "4" * 64


def relation(unary=(0,), binary=((0, 1),)):
    return BoundedArityRelationImage(
        (0, 1, 2),
        (
            RelationSpec("U", 1, tuple((x,) for x in unary)),
            RelationSpec("R", 2, binary),
        ),
    )


def exact_action():
    return prepare_implicit_relation_image_action(
        relation(),
        relation(unary=(0, 1)),
        ((1, 2, 0), (1, 0, 2)),
    )


def image_empty(action, status="exact_empty_feature_inventory_mismatch", **overrides):
    payload = dict(
        status=status,
        exact=True,
        complete=True,
        auxiliary_degree=action.auxiliary_degree,
        coset=None,
    )
    payload.update(overrides)
    return types.SimpleNamespace(**payload)


def preimage_empty(action, **overrides):
    payload = dict(
        status="exact_empty_original_domain_relation_coset",
        exact=True,
        complete=True,
        domain_degree=action.domain_degree,
        auxiliary_degree=action.auxiliary_degree,
        representative=None,
        subgroup=None,
        coset=None,
    )
    payload.update(overrides)
    return types.SimpleNamespace(**payload)


def certify(action=None, image=None, preimage=None, **kwargs):
    action = exact_action() if action is None else action
    image = image_empty(action) if image is None else image
    preimage = preimage_empty(action) if preimage is None else preimage
    params = dict(
        source_relation_digest=SOURCE_DIGEST,
        target_relation_digest=TARGET_DIGEST,
        image_artifact_digest=IMAGE_DIGEST,
        preimage_artifact_digest=PREIMAGE_DIGEST,
    )
    params.update(kwargs)
    return certify_exact_empty_image_parent_outcome(action, image, preimage, **params)


class ImplicitRelationImageEmptyParentBridgeTests(unittest.TestCase):
    def test_feature_inventory_exact_empty_promotes_to_parent_empty(self):
        action = exact_action()
        result = certify(action, image_empty(action), preimage_empty(action))
        self.assertIsInstance(result, ParentExactOutcomeContract)
        self.assertEqual(result.status, "exact_parent_outcome_empty")
        self.assertTrue(result.exact)
        self.assertTrue(result.complete)
        self.assertEqual(result.outcome_kind, "exact_empty")
        self.assertEqual(result.source_evidence_revision, SOURCE_REVISION)
        self.assertEqual(result.source_evidence_status, SOURCE_STATUS)
        self.assertEqual(result.domain_degree, action.domain_degree)
        self.assertEqual(result.auxiliary_degree, action.auxiliary_degree)
        self.assertRegex(result.upstream_artifact_digest, r"^sha256:[0-9a-f]{64}$")
        self.assertRegex(result.transcript_digest, r"^sha256:[0-9a-f]{64}$")

    def test_no_image_group_transporter_exact_empty_is_also_accepted(self):
        action = exact_action()
        result = certify(
            action,
            image_empty(action, status="exact_empty_implicit_image_value_coset"),
            preimage_empty(action),
        )
        self.assertEqual(result.status, "exact_parent_outcome_empty")
        self.assertTrue(result.exact)

    def test_nonexact_or_nonempty_image_evidence_fails_closed(self):
        action = exact_action()
        incomplete = image_empty(action, exact=False, complete=False)
        result = certify(action, incomplete, preimage_empty(action))
        self.assertEqual(result.status, "fail_closed_rev262_exact_empty_image_contract")
        self.assertFalse(result.exact)

        nonempty = image_empty(
            action,
            status="exact_implicit_relation_image_value_coset",
            coset=object(),
        )
        result = certify(action, nonempty, preimage_empty(action))
        self.assertEqual(result.status, "fail_closed_rev262_exact_empty_image_contract")

    def test_exact_empty_image_must_not_carry_a_coset(self):
        action = exact_action()
        result = certify(
            action,
            image_empty(action, coset=object()),
            preimage_empty(action),
        )
        self.assertEqual(result.status, "fail_closed_rev262_exact_empty_image_contract")

    def test_preimage_must_independently_confirm_same_empty_result(self):
        action = exact_action()
        wrong = preimage_empty(
            action,
            status="exact_original_domain_relation_preimage_coset",
            representative=(0, 1, 2),
            subgroup=object(),
            coset=object(),
        )
        result = certify(action, image_empty(action), wrong)
        self.assertEqual(result.status, "fail_closed_rev267_exact_empty_preimage_contract")
        self.assertFalse(result.complete)

    def test_preimage_degree_mismatch_fails_closed(self):
        action = exact_action()
        wrong = preimage_empty(action, domain_degree=action.domain_degree + 1)
        result = certify(action, image_empty(action), wrong)
        self.assertEqual(result.status, "fail_closed_rev267_exact_empty_preimage_contract")

    def test_faithful_rev257_invariants_are_rechecked(self):
        action = exact_action()
        bad_kernel = types.SimpleNamespace(order=2)
        corrupted = dataclasses.replace(action, kernel=bad_kernel)
        result = certify(
            corrupted,
            image_empty(corrupted),
            preimage_empty(corrupted),
        )
        self.assertEqual(result.status, "fail_closed_rev257_faithful_action_contract")
        self.assertFalse(result.exact)

    def test_wrong_rev257_status_fails_closed_before_empty_promotion(self):
        action = dataclasses.replace(exact_action(), status="undetermined_action")
        result = certify(action, image_empty(action), preimage_empty(action))
        self.assertEqual(result.status, "fail_closed_rev257_action_not_exact")

    def test_digest_binding_is_deterministic_and_sensitive_to_upstream_identity(self):
        first = certify()
        second = certify()
        changed = certify(preimage_artifact_digest="sha256:" + "5" * 64)
        self.assertEqual(first.upstream_artifact_digest, second.upstream_artifact_digest)
        self.assertEqual(first.transcript_digest, second.transcript_digest)
        self.assertNotEqual(first.upstream_artifact_digest, changed.upstream_artifact_digest)
        self.assertNotEqual(first.transcript_digest, changed.transcript_digest)

    def test_relation_context_is_preserved_exactly(self):
        result = certify()
        self.assertEqual(result.source_relation_digest, SOURCE_DIGEST)
        self.assertEqual(result.target_relation_digest, TARGET_DIGEST)
        with self.assertRaisesRegex(ValueError, "source_relation_digest"):
            certify(source_relation_digest="not-a-digest")


if __name__ == "__main__":
    unittest.main()
