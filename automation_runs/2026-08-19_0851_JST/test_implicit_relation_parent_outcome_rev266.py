from __future__ import annotations

import hashlib
import unittest
from dataclasses import replace
from types import SimpleNamespace

from implicit_relation_parent_outcome_v1 import (
    EXACT_EMPTY_STATUSES,
    ParentOutcomeContractError,
    normalize_parent_exact_outcome,
    transcript_from_exact_empty_promotion,
    transcript_from_nonempty_promotion,
)


def digest(label: str) -> str:
    return f"sha256:{hashlib.sha256(label.encode('utf-8')).hexdigest()}"


SOURCE = digest("source-relation")
TARGET = digest("target-relation")
ARTIFACT = digest("verified-upstream-artifact")
OTHER_SOURCE = digest("other-source-relation")


def nonempty_stub(**overrides):
    payload = {
        "status": "exact_implicit_relation_parent_coset",
        "exact": True,
        "complete": True,
        "domain_degree": 7,
        "auxiliary_degree": 63,
        "coset": object(),
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


def exact_empty_stub(status: str, **overrides):
    payload = {
        "status": status,
        "exact": True,
        "complete": True,
        "domain_degree": 7,
        "auxiliary_degree": (
            63 if status == "exact_empty_parent_feature_inventory_mismatch" else 0
        ),
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


class ParentOutcomeContractRev266Test(unittest.TestCase):
    def normalize(self, transcript):
        return normalize_parent_exact_outcome(
            [transcript],
            expected_source_relation_digest=SOURCE,
            expected_target_relation_digest=TARGET,
            expected_domain_degree=7,
        )

    def test_nonempty_rev261_transcript_is_normalized(self):
        transcript = transcript_from_nonempty_promotion(
            nonempty_stub(),
            source_relation_digest=SOURCE,
            target_relation_digest=TARGET,
            upstream_artifact_digest=ARTIFACT,
        )
        outcome = self.normalize(transcript)
        self.assertTrue(outcome.exact)
        self.assertTrue(outcome.complete)
        self.assertEqual(outcome.status, "exact_parent_outcome_nonempty")
        self.assertEqual(outcome.source_evidence_revision, 261)
        self.assertEqual(outcome.transcript_digest, transcript.transcript_digest)

    def test_all_rev263_exact_empty_statuses_are_normalized(self):
        for status in sorted(EXACT_EMPTY_STATUSES):
            with self.subTest(status=status):
                transcript = transcript_from_exact_empty_promotion(
                    exact_empty_stub(status),
                    source_relation_digest=SOURCE,
                    target_relation_digest=TARGET,
                    upstream_artifact_digest=ARTIFACT,
                )
                outcome = self.normalize(transcript)
                self.assertTrue(outcome.exact)
                self.assertTrue(outcome.complete)
                self.assertEqual(outcome.status, "exact_parent_outcome_empty")
                self.assertEqual(outcome.source_evidence_revision, 263)
                self.assertEqual(outcome.source_evidence_status, status)

    def test_transcript_digest_is_replay_stable(self):
        first = transcript_from_nonempty_promotion(
            nonempty_stub(),
            source_relation_digest=SOURCE,
            target_relation_digest=TARGET,
            upstream_artifact_digest=ARTIFACT,
        )
        second = transcript_from_nonempty_promotion(
            nonempty_stub(),
            source_relation_digest=SOURCE,
            target_relation_digest=TARGET,
            upstream_artifact_digest=ARTIFACT,
        )
        self.assertEqual(first, second)
        self.assertEqual(first.transcript_digest, second.transcript_digest)

    def test_missing_transcript_fails_closed(self):
        outcome = normalize_parent_exact_outcome(
            [],
            expected_source_relation_digest=SOURCE,
            expected_target_relation_digest=TARGET,
            expected_domain_degree=7,
        )
        self.assertFalse(outcome.exact)
        self.assertEqual(outcome.status, "fail_closed_missing_exact_parent_outcome")

    def test_nonempty_and_empty_transcripts_are_not_reconciled_implicitly(self):
        nonempty = transcript_from_nonempty_promotion(
            nonempty_stub(),
            source_relation_digest=SOURCE,
            target_relation_digest=TARGET,
            upstream_artifact_digest=ARTIFACT,
        )
        empty = transcript_from_exact_empty_promotion(
            exact_empty_stub("exact_empty_parent_feature_inventory_mismatch"),
            source_relation_digest=SOURCE,
            target_relation_digest=TARGET,
            upstream_artifact_digest=digest("empty-artifact"),
        )
        outcome = normalize_parent_exact_outcome(
            [nonempty, empty],
            expected_source_relation_digest=SOURCE,
            expected_target_relation_digest=TARGET,
            expected_domain_degree=7,
        )
        self.assertFalse(outcome.exact)
        self.assertEqual(outcome.status, "fail_closed_contradictory_parent_outcomes")

    def test_tampered_transcript_digest_fails_closed(self):
        transcript = transcript_from_nonempty_promotion(
            nonempty_stub(),
            source_relation_digest=SOURCE,
            target_relation_digest=TARGET,
            upstream_artifact_digest=ARTIFACT,
        )
        corrupted = replace(transcript, auxiliary_degree=64)
        outcome = self.normalize(corrupted)
        self.assertFalse(outcome.exact)
        self.assertEqual(outcome.status, "fail_closed_corrupted_parent_outcome_transcript")

    def test_parent_context_mismatch_fails_closed(self):
        transcript = transcript_from_nonempty_promotion(
            nonempty_stub(),
            source_relation_digest=SOURCE,
            target_relation_digest=TARGET,
            upstream_artifact_digest=ARTIFACT,
        )
        outcome = normalize_parent_exact_outcome(
            [transcript],
            expected_source_relation_digest=OTHER_SOURCE,
            expected_target_relation_digest=TARGET,
            expected_domain_degree=7,
        )
        self.assertFalse(outcome.exact)
        self.assertEqual(outcome.status, "fail_closed_parent_outcome_context_mismatch")

    def test_wrong_schema_fails_closed_before_promotion(self):
        transcript = transcript_from_nonempty_promotion(
            nonempty_stub(),
            source_relation_digest=SOURCE,
            target_relation_digest=TARGET,
            upstream_artifact_digest=ARTIFACT,
        )
        outcome = self.normalize(replace(transcript, schema_version=99))
        self.assertFalse(outcome.exact)
        self.assertEqual(outcome.status, "fail_closed_parent_outcome_schema_version")

    def test_nonexact_upstream_evidence_is_rejected_by_adapter(self):
        with self.assertRaisesRegex(ParentOutcomeContractError, "exact complete rev261"):
            transcript_from_nonempty_promotion(
                nonempty_stub(exact=False),
                source_relation_digest=SOURCE,
                target_relation_digest=TARGET,
                upstream_artifact_digest=ARTIFACT,
            )

    def test_nonempty_upstream_must_carry_coset(self):
        with self.assertRaisesRegex(ParentOutcomeContractError, "nonempty right coset"):
            transcript_from_nonempty_promotion(
                nonempty_stub(coset=None),
                source_relation_digest=SOURCE,
                target_relation_digest=TARGET,
                upstream_artifact_digest=ARTIFACT,
            )

    def test_feature_inventory_empty_evidence_requires_auxiliary_degree(self):
        with self.assertRaisesRegex(ParentOutcomeContractError, "positive auxiliary degree"):
            transcript_from_exact_empty_promotion(
                exact_empty_stub(
                    "exact_empty_parent_feature_inventory_mismatch",
                    auxiliary_degree=0,
                ),
                source_relation_digest=SOURCE,
                target_relation_digest=TARGET,
                upstream_artifact_digest=ARTIFACT,
            )

    def test_invalid_digest_is_rejected_at_adapter_boundary(self):
        with self.assertRaisesRegex(ParentOutcomeContractError, "lowercase sha256"):
            transcript_from_exact_empty_promotion(
                exact_empty_stub("exact_empty_parent_domain_size_mismatch"),
                source_relation_digest="not-a-digest",
                target_relation_digest=TARGET,
                upstream_artifact_digest=ARTIFACT,
            )


if __name__ == "__main__":
    unittest.main()
