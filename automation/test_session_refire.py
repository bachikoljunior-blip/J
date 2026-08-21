import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from automation.session_refire import (
    JST,
    RefireFormatError,
    decide_refire,
    load_session_claim,
    main,
    parse_activity_timestamp,
)


NOW = datetime.fromisoformat("2026-08-21T22:00:00+09:00")
CLAIM_ID = "chatgpt-session-j-parallel-resilience-test"


def claim_payload(**overrides):
    payload = {
        "schema_version": 2,
        "event_type": "active_session_claim",
        "claim_id": CLAIM_ID,
        "session_id": CLAIM_ID,
        "started_at_jst": "2026-08-21T20:00:00+09:00",
        "heartbeat_at_jst": "2026-08-21T20:30:00+09:00",
        "stale_after_minutes": 55,
        "status": "active",
    }
    payload.update(overrides)
    return payload


class SessionRefireTests(unittest.TestCase):
    def write_claim(self, directory: Path, **overrides) -> Path:
        path = directory / "claim.json"
        path.write_text(
            json.dumps(claim_payload(**overrides)),
            encoding="utf-8",
        )
        return path

    def test_stale_active_claim_refires(self):
        with tempfile.TemporaryDirectory() as raw:
            claim = load_session_claim(self.write_claim(Path(raw)))
            decision = decide_refire(claim, now=NOW)
        self.assertTrue(decision.should_refire)
        self.assertEqual(decision.reason, "session_activity_stale")
        self.assertEqual(
            decision.refire_after,
            datetime.fromisoformat("2026-08-21T21:25:00+09:00"),
        )

    def test_recent_branch_commit_prevents_refire(self):
        with tempfile.TemporaryDirectory() as raw:
            claim = load_session_claim(self.write_claim(Path(raw)))
            branch_at = datetime.fromisoformat("2026-08-21T21:30:00+09:00")
            decision = decide_refire(
                claim,
                now=NOW,
                activity_by_source={"branch_commit": branch_at},
            )
        self.assertFalse(decision.should_refire)
        self.assertEqual(decision.latest_activity_at, branch_at)

    def test_recent_pr_update_prevents_refire_even_when_heartbeat_is_stale(self):
        with tempfile.TemporaryDirectory() as raw:
            claim = load_session_claim(self.write_claim(Path(raw)))
            pr_at = datetime.fromisoformat("2026-08-21T12:20:00+00:00")
            decision = decide_refire(
                claim,
                now=NOW,
                activity_by_source={"pull_request_update": pr_at},
            )
        self.assertFalse(decision.should_refire)
        self.assertEqual(
            decision.latest_activity_at,
            datetime.fromisoformat("2026-08-21T21:20:00+09:00"),
        )

    def test_unrelated_activity_is_not_an_input(self):
        with tempfile.TemporaryDirectory() as raw:
            claim = load_session_claim(self.write_claim(Path(raw)))
            decision = decide_refire(claim, now=NOW)
        self.assertNotIn("other_workflow", decision.activity_by_source)
        self.assertTrue(decision.should_refire)

    def test_closed_claim_never_refires(self):
        with tempfile.TemporaryDirectory() as raw:
            claim = load_session_claim(
                self.write_claim(Path(raw), status="completed_merged")
            )
            decision = decide_refire(claim, now=NOW)
        self.assertFalse(decision.should_refire)
        self.assertEqual(decision.reason, "claim_closed")

    def test_exact_staleness_boundary_is_still_fresh(self):
        with tempfile.TemporaryDirectory() as raw:
            claim = load_session_claim(self.write_claim(Path(raw)))
            boundary = claim.heartbeat_at + timedelta(minutes=55)
            decision = decide_refire(claim, now=boundary)
        self.assertFalse(decision.should_refire)

    def test_z_timestamp_is_normalized_to_jst(self):
        parsed = parse_activity_timestamp("2026-08-21T12:00:00Z", "activity")
        self.assertEqual(parsed, datetime.fromisoformat("2026-08-21T21:00:00+09:00"))
        self.assertEqual(parsed.tzinfo, JST)

    def test_naive_timestamp_is_rejected(self):
        with self.assertRaisesRegex(RefireFormatError, "explicit UTC offset"):
            parse_activity_timestamp("2026-08-21T12:00:00", "activity")

    def test_nonpositive_stale_window_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            path = self.write_claim(Path(raw), stale_after_minutes=0)
            with self.assertRaisesRegex(RefireFormatError, "positive integer"):
                load_session_claim(path)

    def test_claim_id_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            path = self.write_claim(Path(raw))
            with self.assertRaisesRegex(RefireFormatError, "does not match expected"):
                load_session_claim(path, expected_claim_id="different-session")

    def test_cli_emits_machine_readable_fresh_decision(self):
        with tempfile.TemporaryDirectory() as raw:
            path = self.write_claim(Path(raw))
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(
                    [
                        "check",
                        "--claim-file",
                        str(path),
                        "--claim-id",
                        CLAIM_ID,
                        "--now",
                        "2026-08-21T22:00:00+09:00",
                        "--branch-activity-at",
                        "2026-08-21T21:50:00+09:00",
                    ]
                )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertFalse(payload["should_refire"])
        self.assertEqual(payload["reason"], "session_activity_fresh")

    def test_cli_fails_closed_on_invalid_claim(self):
        with tempfile.TemporaryDirectory() as raw:
            path = self.write_claim(Path(raw), heartbeat_at_jst="not-a-time")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                result = main(
                    [
                        "check",
                        "--claim-file",
                        str(path),
                        "--claim-id",
                        CLAIM_ID,
                    ]
                )
        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 3)
        self.assertFalse(payload["should_refire"])
        self.assertEqual(payload["reason"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
