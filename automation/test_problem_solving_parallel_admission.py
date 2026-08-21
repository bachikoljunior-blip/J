import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from automation.parallel_claims import ClaimFormatError, load_claim
from automation.problem_solving_parallel_admission import (
    admit_problem_phase,
    evidence_payload,
    registry_digest,
    scope_is_within,
    validate_evidence_payload,
)


NOW = datetime.fromisoformat("2026-08-21T21:30:00+09:00")


def _payload(claim_id: str, scope: str, revision: int | None, **overrides):
    payload = {
        "schema_version": 2,
        "event_type": "active_session_claim",
        "claim_id": claim_id,
        "session_id": claim_id,
        "started_at_jst": "2026-08-21T21:00:00+09:00",
        "heartbeat_at_jst": "2026-08-21T21:20:00+09:00",
        "stale_after_minutes": 90,
        "starting_main_sha": "a" * 40,
        "starting_agi_gi_rev": 244,
        "target_revision": revision,
        "scope": scope,
        "branch": f"branch-{claim_id}",
        "status": "active",
        "agi_state": "NOT_AGI",
    }
    payload.update(overrides)
    return payload


class ProblemSolvingParallelAdmissionTest(unittest.TestCase):
    def claim(self, directory: Path, payload: dict):
        path = directory / f"{payload['claim_id']}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return load_claim(path)

    def test_scope_within_is_directional(self):
        self.assertTrue(scope_is_within("CRX2/a/child", "CRX2/a"))
        self.assertFalse(scope_is_within("CRX2", "CRX2/a"))
        self.assertFalse(scope_is_within("CRX2/ab", "CRX2/a"))

    def test_forecast_observes_parallel_claims_without_owning_root(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            own = self.claim(directory, _payload("own", "CRX2/a", 247))
            other = self.claim(directory, _payload("other", "CRX3/b", 248))
            result = admit_problem_phase(
                [own, other],
                claim_id="own",
                phase="forecast",
                scope="root",
                target_revision=None,
                now=NOW,
                registry_source_sha="f" * 40,
            )
            self.assertTrue(result["admitted"])
            self.assertEqual(result["mode"], "observe")
            self.assertEqual(result["parallel_active_claims"][0]["claim_id"], "other")

    def test_exclusive_child_phase_is_admitted(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            own = self.claim(directory, _payload("own", "CRX2/a", 247))
            result = admit_problem_phase(
                [own],
                claim_id="own",
                phase="attempt_solution",
                scope="CRX2/a/child",
                target_revision=247,
                now=NOW,
                registry_source_sha="f" * 40,
            )
            self.assertTrue(result["admitted"])

    def test_exclusive_phase_requires_paths_inside_own_reservation(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            own = self.claim(
                directory,
                _payload("own", "CRX2/a", 247, reserved_paths=["automation/owned"]),
            )
            accepted = admit_problem_phase(
                [own], claim_id="own", phase="attempt_solution",
                scope="CRX2/a", target_revision=247, now=NOW,
                registry_source_sha="f" * 40, paths=["automation/owned/solver.py"],
            )
            rejected = admit_problem_phase(
                [own], claim_id="own", phase="attempt_solution",
                scope="CRX2/a", target_revision=247, now=NOW,
                registry_source_sha="f" * 40, paths=["automation/shared.py"],
            )
            self.assertTrue(accepted["admitted"])
            self.assertFalse(rejected["admitted"])
            self.assertIn("path_outside_own_claim", rejected["reasons"])

    def test_parallel_reserved_path_blocks_sibling_scope(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            own = self.claim(
                directory,
                _payload("own", "CRX2/a", 247, reserved_paths=["automation/shared.py"]),
            )
            other = self.claim(
                directory,
                _payload("other", "CRX3/b", 248, reserved_paths=["automation/shared.py"]),
            )
            result = admit_problem_phase(
                [own, other], claim_id="own", phase="publish",
                scope="CRX2/a", target_revision=247, now=NOW,
                registry_source_sha="f" * 40, paths=["automation/shared.py"],
            )
            self.assertFalse(result["admitted"])
            self.assertEqual(
                result["conflicts"][0]["reasons"], ["reserved_path_collision"]
            )

    def test_parent_mutation_outside_claim_is_blocked(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            own = self.claim(directory, _payload("own", "CRX2/a/child", 247))
            result = admit_problem_phase(
                [own],
                claim_id="own",
                phase="solve_parent",
                scope="CRX2/a",
                target_revision=247,
                now=NOW,
                registry_source_sha="f" * 40,
            )
            self.assertFalse(result["admitted"])
            self.assertIn("scope_outside_own_claim", result["reasons"])

    def test_parallel_descendant_blocks_parent_integration(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            own = self.claim(directory, _payload("own", "CRX2/a", 247))
            other = self.claim(directory, _payload("other", "CRX2/a/right", 248))
            result = admit_problem_phase(
                [own, other],
                claim_id="own",
                phase="integrate_children",
                scope="CRX2/a",
                target_revision=247,
                now=NOW,
                registry_source_sha="f" * 40,
            )
            self.assertFalse(result["admitted"])
            self.assertIn("parallel_claim_collision", result["reasons"])

    def test_same_revision_collision_blocks_sibling_write(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            own = self.claim(directory, _payload("own", "CRX2/a", 247))
            other = self.claim(directory, _payload("other", "CRX3/b", 247))
            result = admit_problem_phase(
                [own, other],
                claim_id="own",
                phase="publish",
                scope="CRX2/a",
                target_revision=247,
                now=NOW,
                registry_source_sha="f" * 40,
            )
            self.assertFalse(result["admitted"])

    def test_wrong_revision_and_stale_owner_fail_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            own = self.claim(
                directory,
                _payload(
                    "own",
                    "CRX2/a",
                    247,
                    started_at_jst="2026-08-21T17:50:00+09:00",
                    heartbeat_at_jst="2026-08-21T18:00:00+09:00",
                ),
            )
            result = admit_problem_phase(
                [own],
                claim_id="own",
                phase="evaluate",
                scope="CRX2/a",
                target_revision=248,
                now=NOW,
                registry_source_sha="f" * 40,
            )
            self.assertFalse(result["admitted"])
            self.assertIn("own_claim_not_fresh", result["reasons"])
            self.assertIn("target_revision_differs_from_own_claim", result["reasons"])

    def test_registry_digest_changes_with_parallel_heartbeat(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            first = self.claim(directory, _payload("own", "CRX2/a", 247))
            second = self.claim(
                directory,
                _payload("other", "CRX3/b", 248, heartbeat_at_jst="2026-08-21T21:21:00+09:00"),
            )
            before = registry_digest([first], NOW)
            after = registry_digest([first, second], NOW)
            self.assertNotEqual(before, after)
            self.assertTrue(after.startswith("sha256:"))

    def test_unknown_phase_is_rejected(self):
        with self.assertRaises(ClaimFormatError):
            admit_problem_phase(
                [],
                claim_id="own",
                phase="invent_result",
                scope="root",
                target_revision=None,
                now=NOW,
                registry_source_sha="f" * 40,
            )

    def test_evidence_payload_validates_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            own = self.claim(directory, _payload("own", "CRX2/a", 247))
            result = admit_problem_phase(
                [own],
                claim_id="own",
                phase="publish",
                scope="CRX2/a",
                target_revision=247,
                now=NOW,
                registry_source_sha="f" * 40,
            )
            evidence = evidence_payload(result, NOW)
            self.assertEqual(validate_evidence_payload(evidence), ())
            evidence["scope"] = "CRX3/stolen"
            self.assertIn(
                "exclusive evidence scope is outside own claim",
                validate_evidence_payload(evidence),
            )

    def test_evidence_rejects_parallel_snapshot_tampering(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            own = self.claim(directory, _payload("own", "CRX2/a", 247))
            result = admit_problem_phase(
                [own],
                claim_id="own",
                phase="publish",
                scope="CRX2/a",
                target_revision=247,
                now=NOW,
                registry_source_sha="f" * 40,
            )
            evidence = evidence_payload(result, NOW)
            evidence["parallel_active_claims"] = [
                {
                    "claim_id": "other",
                    "scope": "CRX2/a/child",
                    "target_revision": 248,
                    "heartbeat_at_jst": NOW.isoformat(),
                    "state": "active",
                    "branch": "other",
                }
            ]
            errors = validate_evidence_payload(evidence)
            self.assertIn("registry_digest does not match embedded active claims", errors)
            self.assertIn("exclusive evidence overlaps a parallel claim", errors)


if __name__ == "__main__":
    unittest.main()
