import unittest
from pathlib import Path

from automation.problem_solving_phase_evidence_guard import (
    is_problem_state_path,
    path_is_covered,
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
        self.assertNotIn("github.event.pull_request.base.sha", workflow)


if __name__ == "__main__":
    unittest.main()
