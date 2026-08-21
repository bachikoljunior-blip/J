import unittest

from automation.agi_gi_main_revision_guard import (
    audit_revision_state,
    parse_integrated_revisions,
    parse_main_continuation,
)


def _main(revision: int) -> str:
    return (
        "# J main line\n\n## 現在の継続点\n\n"
        f"現在の統合済み継続点は **AGI-GI rev{revision}**。details\n"
    )


class MainRevisionGuardTest(unittest.TestCase):
    def test_parallel_out_of_order_merges_use_numeric_maximum(self) -> None:
        lines = (
            "c" * 40 + "\tAGI-GI rev243: later wall-clock merge",
            "a" * 40 + "\tAGI-GI rev244: earlier wall-clock merge",
            "b" * 40 + "\tAGI-GI rev242: shared ledger",
        )
        audit = audit_revision_state(lines, _main(244))
        self.assertTrue(audit.valid)
        self.assertEqual(audit.latest_integrated_revision, 244)
        self.assertEqual(audit.latest_integrated_commit, "a" * 40)

    def test_claim_and_branch_commits_cannot_advance_revision(self) -> None:
        lines = (
            "a" * 40 + "\tchore: claim rev246 primitive integration",
            "b" * 40 + "\trev245: integrate candidate branch",
            "c" * 40 + "\tAGI-GI rev244: canonical integration",
        )
        parsed = parse_integrated_revisions(lines)
        self.assertEqual([item.revision for item in parsed], [244])

    def test_stale_main_fails_closed_with_evidence(self) -> None:
        sha = "d" * 40
        audit = audit_revision_state(
            (sha + "\tAGI-GI rev244: canonical integration",), _main(241)
        )
        self.assertFalse(audit.valid)
        self.assertIn("declares rev241", audit.errors[0])
        self.assertIn(sha, audit.errors[0])

    def test_future_main_declaration_also_fails_closed(self) -> None:
        audit = audit_revision_state(
            ("a" * 40 + "\tAGI-GI rev244: canonical integration",), _main(245)
        )
        self.assertFalse(audit.valid)

    def test_missing_integration_commit_fails_closed(self) -> None:
        audit = audit_revision_state(
            ("a" * 40 + "\trev244: branch implementation",), _main(244)
        )
        self.assertFalse(audit.valid)
        self.assertIn("no canonical", audit.errors[0])

    def test_missing_main_declaration_fails_closed(self) -> None:
        audit = audit_revision_state(
            ("a" * 40 + "\tAGI-GI rev244: canonical integration",), "# J\n"
        )
        self.assertFalse(audit.valid)
        self.assertIn("no canonical", audit.errors[0])

    def test_main_parser_requires_exact_canonical_sentence(self) -> None:
        self.assertEqual(parse_main_continuation(_main(244)), 244)
        self.assertIsNone(parse_main_continuation("pending AGI-GI rev245"))


if __name__ == "__main__":
    unittest.main()
