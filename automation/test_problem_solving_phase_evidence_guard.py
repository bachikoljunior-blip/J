import json
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from automation.parallel_claims import JST, load_registry
from automation.problem_solving_parallel_admission import (
    admit_problem_phase,
    evidence_payload,
)
from automation.problem_solving_phase_evidence_guard import (
    _current_registry_observation_time,
    is_problem_state_path,
    path_is_covered,
    replay_evidence,
)


class ProblemSolvingPhaseEvidenceGuardTest(unittest.TestCase):
    def test_problem_state_paths_require_evidence(self):
        for path in (
            "MAIN.md",
            "automation/solver.py",
            "automation_runs/run/rev250.py",
            "agi/core/runtime.py",
            ".github/workflows/rev250-smoke.yml",
            ".github/workflows/agi-gi-validation.yml",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_problem_state_path(path))

    def test_coordination_records_do_not_recursively_require_evidence(self):
        for path in (
            "agi/run-history/STARTS.jsonl",
            "agi/run-history/active/claim.json",
            "agi/run-history/phase-admissions/evidence.json",
        ):
            with self.subTest(path=path):
                self.assertFalse(is_problem_state_path(path))

    def test_unrelated_repository_files_do_not_require_evidence(self):
        self.assertFalse(is_problem_state_path("README.md"))
        self.assertFalse(is_problem_state_path("docs/notes.md"))

    def test_admitted_directory_covers_descendant_but_not_prefix_sibling(self):
        self.assertTrue(path_is_covered("automation/core.py", ["automation"]))
        self.assertFalse(path_is_covered("automation_runs/core.py", ["automation"]))

    def test_invalid_admitted_path_fails_closed(self):
        self.assertFalse(path_is_covered("MAIN.md", ["../MAIN.md"]))

    def test_workflow_diffs_against_fresh_current_main(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/problem-solving-parallel-admission.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("git fetch --no-tags origin main", workflow)
        self.assertIn("git merge-base origin/main HEAD", workflow)
        self.assertIn("--current-registry-ref origin/main", workflow)
        self.assertNotIn("github.event.pull_request.base.sha", workflow)

    def test_current_registry_observation_time_includes_later_claim_events(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            claim_dir = root / "agi/run-history/active"
            claim_dir.mkdir(parents=True)
            self._write_claim(
                claim_dir / "owner.json",
                claim_id="owner",
                started="2026-08-22T21:00:00+09:00",
                heartbeat="2026-08-22T21:01:00+09:00",
                scope="scope/owner",
                paths=["MAIN.md"],
            )
            claims, errors = load_registry(root)
            self.assertEqual(errors, [])
            recorded = datetime(2026, 8, 22, 20, 59, tzinfo=JST)
            self.assertEqual(
                _current_registry_observation_time(claims, recorded).isoformat(),
                "2026-08-22T21:01:00+09:00",
            )

    def test_current_registry_replay_rejects_new_path_collision(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=root,
                check=True,
            )
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            claim_dir = root / "agi/run-history/active"
            claim_dir.mkdir(parents=True)
            self._write_claim(
                claim_dir / "owner.json",
                claim_id="owner",
                started="2026-08-22T21:00:00+09:00",
                heartbeat="2026-08-22T21:00:00+09:00",
                scope="scope/owner",
                paths=["MAIN.md"],
            )
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "source"], cwd=root, check=True)
            source = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            claims, errors = load_registry(root)
            self.assertEqual(errors, [])
            recorded = datetime(2026, 8, 22, 21, 0, tzinfo=JST)
            persisted = evidence_payload(
                admit_problem_phase(
                    claims,
                    claim_id="owner",
                    phase="update_problem_tree",
                    scope="scope/owner",
                    target_revision=None,
                    now=recorded,
                    registry_source_sha=source,
                    paths=["MAIN.md"],
                ),
                recorded,
            )
            evidence = root / "evidence.json"
            evidence.write_text(json.dumps(persisted), encoding="utf-8")
            self._write_claim(
                claim_dir / "collision.json",
                claim_id="collision",
                started="2026-08-22T21:01:00+09:00",
                heartbeat="2026-08-22T21:01:00+09:00",
                scope="other/scope",
                paths=["MAIN.md"],
            )
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "current"], cwd=root, check=True)
            current = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()

            self.assertEqual(replay_evidence(root, evidence, current), ())
            hardened = replay_evidence(root, evidence, current, current)
            self.assertTrue(any("parallel_claim_collision" in item for item in hardened))

            self._write_claim(
                claim_dir / "collision.json",
                claim_id="collision",
                started="2026-08-22T21:01:00+09:00",
                heartbeat="2026-08-22T21:02:00+09:00",
                scope="unrelated/scope",
                paths=["README.md"],
            )
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "unrelated"], cwd=root, check=True)
            unrelated = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            self.assertEqual(replay_evidence(root, evidence, unrelated, unrelated), ())

            tree = subprocess.check_output(
                ["git", "show", "-s", "--format=%T", unrelated],
                cwd=root,
                text=True,
            ).strip()
            disjoint = subprocess.check_output(
                ["git", "commit-tree", tree],
                cwd=root,
                input="disjoint registry history\n",
                text=True,
            ).strip()
            ancestry_errors = replay_evidence(root, evidence, unrelated, disjoint)
            self.assertTrue(
                any("does not descend" in item for item in ancestry_errors)
            )

    @staticmethod
    def _write_claim(path, *, claim_id, started, heartbeat, scope, paths):
        payload = {
            "schema_version": 2,
            "event_type": "active_session_claim",
            "claim_id": claim_id,
            "session_id": f"session-{claim_id}",
            "started_at_jst": started,
            "heartbeat_at_jst": heartbeat,
            "stale_after_minutes": 90,
            "starting_main_sha": "a" * 40,
            "starting_agi_gi_rev": 3300,
            "target_revision": None,
            "scope": scope,
            "branch": f"branch-{claim_id}",
            "reserved_paths": paths,
            "status": "active",
            "agi_state": "NOT_AGI",
        }
        path.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
