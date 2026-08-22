import json
import unittest

from automation.agi_gi_run_start_history_guard import HistoryError, validate_history


def line(**values):
    return json.dumps(values)


class RunStartHistoryGuardTest(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.evidence = "b" * 40
        self.start = {
            "started_at_jst": "2026-08-22T16:41:10+09:00",
            "starting_main_sha": self.sha,
            "starting_agi_gi_rev": 952,
            "automation_run_id": "run-1",
        }
        self.resolver = lambda sha: (952, self.evidence)

    def test_matching_start_is_accepted(self):
        summary = validate_history([line(**self.start)], self.resolver)
        self.assertEqual(summary["starts"], 1)
        self.assertEqual(summary["corrected_starts"], 0)

    def test_mismatch_without_correction_fails_closed(self):
        bad = {
            **self.start,
            "starting_agi_gi_rev": 950,
            "start_rev_source": "canonical_main_ancestry_rev952",
        }
        with self.assertRaisesRegex(HistoryError, "canonical rev952"):
            validate_history([line(**bad)], self.resolver)

    def test_exact_correction_is_accepted(self):
        bad = {**self.start, "starting_agi_gi_rev": 950}
        correction = {
            "event_type": "automation_run_start_correction",
            "correction_of_automation_run_id": "run-1",
            "started_at_jst": bad["started_at_jst"],
            "starting_main_sha": self.sha,
            "supersedes_starting_agi_gi_rev": 950,
            "starting_agi_gi_rev": 952,
            "evidence_commit_sha": self.evidence,
        }
        summary = validate_history([line(**bad), line(**correction)], self.resolver)
        self.assertEqual(summary["corrected_starts"], 1)

    def test_correction_must_bind_sha_old_rev_and_evidence(self):
        bad = {**self.start, "starting_agi_gi_rev": 950}
        correction = {
            "event_type": "automation_run_start_correction",
            "correction_of_automation_run_id": "run-1",
            "started_at_jst": bad["started_at_jst"],
            "starting_main_sha": "c" * 40,
            "supersedes_starting_agi_gi_rev": 950,
            "starting_agi_gi_rev": 952,
            "evidence_commit_sha": self.evidence,
        }
        with self.assertRaisesRegex(HistoryError, "does not bind"):
            validate_history([line(**bad), line(**correction)], self.resolver)

    def test_legacy_correction_is_replayed_without_weakening_evidence(self):
        bad = {**self.start, "starting_agi_gi_rev": 950}
        correction = {
            "event_type": "start_record_correction",
            "corrects_automation_run_id": "run-1",
            "corrected_starting_agi_gi_rev": 952,
            "evidence_commit_sha": self.evidence,
            "evidence_relation": "ancestor_of_starting_main_sha",
            "preserves_original_record": True,
        }
        summary = validate_history([line(**bad), line(**correction)], self.resolver)
        self.assertEqual(summary["corrected_starts"], 1)

    def test_duplicate_and_orphan_events_fail_closed(self):
        with self.assertRaisesRegex(HistoryError, "duplicate start"):
            validate_history([line(**self.start), line(**self.start)], self.resolver)
        orphan = {
            "event_type": "automation_run_start_correction",
            "correction_of_automation_run_id": "missing",
        }
        with self.assertRaisesRegex(HistoryError, "unknown run"):
            validate_history([line(**orphan)], self.resolver)

    def test_non_jst_and_unknown_event_fail_closed(self):
        bad_time = {**self.start, "started_at_jst": "2026-08-22T07:41:10+00:00"}
        with self.assertRaisesRegex(ValueError, r"\+09:00"):
            validate_history([line(**bad_time)], self.resolver)
        with self.assertRaisesRegex(HistoryError, "unsupported event_type"):
            validate_history([line(event_type="invented")], self.resolver)

    def test_explicit_marker_starts_enforcement_and_cannot_disappear(self):
        legacy = {**self.start, "automation_run_id": "legacy"}
        marked = {
            **self.start,
            "automation_run_id": "marked",
            "start_rev_source": "canonical_main_ancestry_rev952",
        }
        summary = validate_history(
            [line(**legacy), line(**marked)],
            self.resolver,
        )
        self.assertEqual(summary["legacy_unverifiable_starts"], 1)
        with self.assertRaisesRegex(HistoryError, "no canonical revision"):
            validate_history(
                [
                    line(**marked),
                    line(
                        **{
                            **self.start,
                            "automation_run_id": "later",
                            "starting_main_sha": "c" * 40,
                        }
                    ),
                ],
                lambda sha: (952, self.evidence) if sha == self.sha else None,
            )

    def test_exact_identity_correction_is_accepted(self):
        unavailable = {**self.start, "starting_main_sha": "c" * 40}
        corrected_sha = "d" * 40
        next_sha = "e" * 40
        correction = {
            "event_type": "automation_run_start_identity_correction",
            "correction_of_automation_run_id": "run-1",
            "started_at_jst": unavailable["started_at_jst"],
            "supersedes_starting_main_sha": unavailable["starting_main_sha"],
            "corrected_starting_main_sha": corrected_sha,
            "next_main_commit_sha": next_sha,
            "starting_agi_gi_rev": 952,
            "preserves_original_record": True,
        }
        summary = validate_history(
            [line(**unavailable), line(**correction)],
            lambda sha: (952, self.evidence) if sha == corrected_sha else None,
            lambda old, corrected, following, timestamp: (
                old == unavailable["starting_main_sha"]
                and corrected == corrected_sha
                and following == next_sha
                and timestamp == unavailable["started_at_jst"]
            ),
        )
        self.assertEqual(summary["identity_corrected_starts"], 1)

    def test_identity_correction_requires_independent_evidence(self):
        unavailable = {**self.start, "starting_main_sha": "c" * 40}
        correction = {
            "event_type": "automation_run_start_identity_correction",
            "correction_of_automation_run_id": "run-1",
            "started_at_jst": unavailable["started_at_jst"],
            "supersedes_starting_main_sha": unavailable["starting_main_sha"],
            "corrected_starting_main_sha": "d" * 40,
            "next_main_commit_sha": "e" * 40,
            "starting_agi_gi_rev": 952,
            "preserves_original_record": True,
        }
        with self.assertRaisesRegex(HistoryError, "identity correction evidence"):
            validate_history(
                [line(**unavailable), line(**correction)],
                lambda sha: (952, self.evidence),
                lambda old, corrected, following, timestamp: False,
            )

    def test_duplicate_and_orphan_identity_corrections_fail_closed(self):
        correction = {
            "event_type": "automation_run_start_identity_correction",
            "correction_of_automation_run_id": "run-1",
        }
        with self.assertRaisesRegex(HistoryError, "duplicate identity correction"):
            validate_history(
                [line(**self.start), line(**correction), line(**correction)],
                self.resolver,
            )
        with self.assertRaisesRegex(HistoryError, "unknown run"):
            validate_history(
                [line(**{**correction, "correction_of_automation_run_id": "missing"})],
                self.resolver,
            )


if __name__ == "__main__":
    unittest.main()
