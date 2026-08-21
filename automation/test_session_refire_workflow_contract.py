import re
import unittest
from pathlib import Path


WORKFLOW = Path(".github/workflows/j-parallel-resilience-session-hourly-refire.yml")
CLAIM_ID = "chatgpt-session-j-parallel-resilience-20260821T215558JST-01ad84ba"
CLAIM_PATH = f"agi/run-history/active/{CLAIM_ID}.json"
BRANCH = "ops-j-parallel-resilience-20260821-215558"
ISSUE_TITLE = "[automation] J parallel resilience session re-fire queue"


class SessionRefireWorkflowContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_hourly_schedule_and_runtime_serialization_are_fixed(self):
        self.assertIn('cron: "56 * * * *"', self.text)
        self.assertIn(
            "group: j-parallel-resilience-session-hourly-refire-runtime",
            self.text,
        )
        self.assertIn("cancel-in-progress: false", self.text)
        self.assertNotIn("${{ github.event_name }}", self.text)

    def test_contract_is_pinned_to_exact_claim_and_branch(self):
        self.assertIn(f"CLAIM_ID: {CLAIM_ID}", self.text)
        self.assertIn(f"CLAIM_PATH: {CLAIM_PATH}", self.text)
        self.assertIn(f"BRANCH: {BRANCH}", self.text)
        self.assertIn(f'title="{ISSUE_TITLE}"', self.text)

    def test_only_exact_session_github_reads_are_present(self):
        api_calls = re.findall(r'gh api "([^"]+)"', self.text)
        self.assertEqual(
            api_calls,
            [
                "repos/${REPOSITORY}/contents/${CLAIM_PATH}?ref=main",
                "repos/${REPOSITORY}/commits/${BRANCH}",
                "repos/${REPOSITORY}/pulls?state=open&head=${owner}:${BRANCH}&per_page=1",
            ],
        )

    def test_no_sibling_or_destructive_workflow_commands_exist(self):
        forbidden = (
            "gh workflow run",
            "gh workflow cancel",
            "gh run rerun",
            "gh run cancel",
            "gh pr merge",
            "gh pr close",
            "git push --force",
        )
        for command in forbidden:
            with self.subTest(command=command):
                self.assertNotIn(command, self.text)
        self.assertIn(
            "Other branches, PRs, claims, and workflows inspected or changed: none",
            self.text,
        )

    def test_invalid_exact_session_input_fails_closed(self):
        self.assertIn('echo "stale=false" >>"${GITHUB_OUTPUT}"', self.text)
        self.assertIn('echo "reason=invalid_input" >>"${GITHUB_OUTPUT}"', self.text)
        self.assertIn("fail closed without re-fire", self.text)


if __name__ == "__main__":
    unittest.main()
