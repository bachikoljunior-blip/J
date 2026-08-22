import unittest

from automation.agi_gi_run_start_record import (
    build_run_start_record,
    highest_integrated_revision,
)


class RunStartRecordTest(unittest.TestCase):
    def test_numeric_maximum_is_derived_from_starting_main_ancestry(self):
        record = build_run_start_record(
            started_at_jst="2026-08-22T16:41:10+09:00",
            starting_main_sha="f" * 40,
            log_lines=(
                "a" * 40 + "\tAGI-GI rev950: kernel proof DAG",
                "b" * 40 + "\tAGI-GI rev952: relation proof DAG",
                "c" * 40 + "\tcoordination: record green rev1400 head",
            ),
            automation_run_id="run-1",
        )
        self.assertEqual(record["starting_agi_gi_rev"], 952)
        self.assertEqual(record["integrated_revision_commit_sha"], "b" * 40)
        self.assertIn("MAIN.md_not_used", record["start_rev_source"])

    def test_stale_main_cannot_influence_record(self):
        record = build_run_start_record(
            started_at_jst="2026-08-22T16:41:10+09:00",
            starting_main_sha="e" * 40,
            log_lines=("d" * 40 + "\tAGI-GI rev952: integration",),
            automation_run_id="run-stale-main",
        )
        self.assertEqual(record["starting_agi_gi_rev"], 952)
        self.assertNotIn("MAIN.md", record)

    def test_claim_and_exact_head_messages_do_not_advance_revision(self):
        highest = highest_integrated_revision(
            (
                "a" * 40 + "\tcoordination: claim rev1400",
                "b" * 40 + "\tcoordination: record all-green rev1400 exact-head",
                "c" * 40 + "\tAGI-GI rev952: integrated",
            )
        )
        self.assertEqual(highest.revision, 952)

    def test_no_canonical_integration_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "no canonical"):
            highest_integrated_revision(("a" * 40 + "\tcoordination: claim rev1",))

    def test_non_jst_timestamp_fails_closed(self):
        with self.assertRaisesRegex(ValueError, r"\+09:00"):
            build_run_start_record(
                started_at_jst="2026-08-22T07:41:10+00:00",
                starting_main_sha="f" * 40,
                log_lines=("a" * 40 + "\tAGI-GI rev952: integrated",),
                automation_run_id="run-bad-time",
            )

    def test_invalid_sha_and_empty_run_id_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "40 lowercase"):
            build_run_start_record(
                started_at_jst="2026-08-22T16:41:10+09:00",
                starting_main_sha="not-a-sha",
                log_lines=("a" * 40 + "\tAGI-GI rev952: integrated",),
                automation_run_id="run-bad-sha",
            )
        with self.assertRaisesRegex(ValueError, "non-empty"):
            build_run_start_record(
                started_at_jst="2026-08-22T16:41:10+09:00",
                starting_main_sha="f" * 40,
                log_lines=("a" * 40 + "\tAGI-GI rev952: integrated",),
                automation_run_id=" ",
            )


if __name__ == "__main__":
    unittest.main()
