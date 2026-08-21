import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from automation.parallel_claims import (
    ClaimFormatError,
    JST,
    find_conflicts,
    find_registry_collisions,
    load_claim,
    load_registry,
    normalize_scope,
    scopes_overlap,
)


NOW = datetime.fromisoformat("2026-08-21T21:10:00+09:00")


def canonical_claim(**overrides):
    result = {
        "schema_version": 2,
        "event_type": "active_session_claim",
        "claim_id": "session-a",
        "session_id": "session-a",
        "started_at_jst": "2026-08-21T21:00:00+09:00",
        "heartbeat_at_jst": "2026-08-21T21:05:00+09:00",
        "stale_after_minutes": 90,
        "starting_main_sha": "a" * 40,
        "starting_agi_gi_rev": 245,
        "target_revision": 246,
        "scope": "CRX2/c2b2/child-a",
        "branch": "agi-gi-rev246-child-a",
        "status": "active",
        "agi_state": "NOT_AGI",
    }
    result.update(overrides)
    return result


class ParallelClaimTests(unittest.TestCase):
    def write_claim(self, directory: Path, payload: dict) -> Path:
        path = directory / f"{payload.get('claim_id', 'legacy')}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_scope_overlap_is_hierarchical_not_string_prefix(self):
        self.assertTrue(scopes_overlap("CRX2/c2", "crx2/c2/child"))
        self.assertTrue(scopes_overlap("CRX2/c2/child", "CRX2/c2"))
        self.assertFalse(scopes_overlap("CRX2/c2", "CRX2/c20"))
        self.assertFalse(scopes_overlap("CRX2/c2/a", "CRX2/c2/b"))

    def test_legacy_scope_description_normalizes_to_path(self):
        self.assertEqual(
            normalize_scope("CRX2/c2b2a2iii nested primitive preflight"),
            "crx2/c2b2a2iii",
        )

    def test_fresh_parent_scope_conflicts_with_child(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            claim = load_claim(self.write_claim(directory, canonical_claim()))
            conflicts = find_conflicts(
                [claim],
                scope="CRX2/c2b2/child-a/subleaf",
                target_revision=247,
                now=NOW,
            )
            self.assertEqual(len(conflicts), 1)
            self.assertEqual(conflicts[0][1], ["scope_overlap"])

    def test_same_revision_conflicts_even_for_sibling_scope(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            claim = load_claim(self.write_claim(directory, canonical_claim()))
            conflicts = find_conflicts(
                [claim],
                scope="CRX2/c2b2/child-b",
                target_revision=246,
                now=NOW,
            )
            self.assertEqual(conflicts[0][1], ["target_revision_collision"])

    def test_fresh_sibling_with_different_revision_is_available(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            claim = load_claim(self.write_claim(directory, canonical_claim()))
            self.assertEqual(
                find_conflicts(
                    [claim],
                    scope="CRX2/c2b2/child-b",
                    target_revision=247,
                    now=NOW,
                ),
                [],
            )

    def test_stale_and_closed_claims_do_not_block(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            stale = canonical_claim(
                claim_id="stale",
                session_id="stale",
                started_at_jst="2026-08-21T17:55:00+09:00",
                heartbeat_at_jst="2026-08-21T18:00:00+09:00",
            )
            closed = canonical_claim(
                claim_id="closed",
                session_id="closed",
                status="closed",
            )
            claims = [
                load_claim(self.write_claim(directory, stale)),
                load_claim(self.write_claim(directory, closed)),
            ]
            self.assertEqual(
                find_conflicts(
                    claims,
                    scope="CRX2/c2b2/child-a",
                    target_revision=246,
                    now=NOW,
                ),
                [],
            )

    def test_excluding_own_claim_supports_post_commit_race_check(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            claim = load_claim(self.write_claim(directory, canonical_claim()))
            self.assertEqual(
                find_conflicts(
                    [claim],
                    scope=claim.scope,
                    target_revision=claim.target_revision,
                    now=NOW,
                    exclude_claim_ids={claim.claim_id},
                ),
                [],
            )

    def test_registry_audit_detects_two_simultaneous_claims(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            left = load_claim(self.write_claim(directory, canonical_claim()))
            right = load_claim(
                self.write_claim(
                    directory,
                    canonical_claim(
                        claim_id="session-b",
                        session_id="session-b",
                        branch="agi-gi-rev246-child-b",
                        scope="CRX2/c2b2/child-b",
                    ),
                )
            )
            collisions = find_registry_collisions([left, right], now=NOW)
            self.assertEqual(len(collisions), 1)
            self.assertEqual(collisions[0][2], ["target_revision_collision"])

    def test_v2_requires_jst_offset(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = self.write_claim(
                directory,
                canonical_claim(started_at_jst="2026-08-21T12:00:00+00:00"),
            )
            with self.assertRaisesRegex(ClaimFormatError, r"\+09:00"):
                load_claim(path)

    def test_v2_requires_normalized_hierarchical_scope(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = self.write_claim(
                directory,
                canonical_claim(scope="CRX2/c2b2/child-a descriptive prose"),
            )
            with self.assertRaisesRegex(ClaimFormatError, "slash path without whitespace"):
                load_claim(path)

    def test_completed_legacy_parallel_record_is_accepted(self):
        legacy = {
            "event_type": "parallel_execution_claim",
            "started_at_jst": "2026-08-21T19:31:55+09:00",
            "completed_at_jst": "2026-08-21T20:32:21+09:00",
            "delegated_leaf": "CRX2/c2b2a2i3b_shared_pipeline_admission",
            "completed_branch": "agi-gi-rev244",
            "coordination_state": "COMPLETED_MERGED",
        }
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            claim = load_claim(self.write_claim(directory, legacy))
            self.assertTrue(claim.legacy)
            self.assertEqual(claim.state_at(NOW), "closed")

    def test_singleton_scope_list_is_blocking_interoperability_claim(self):
        variant = canonical_claim(
            claim_id="variant",
            session_id="variant",
            scope=["CRX1/image-si/resource-admission"],
        )
        variant.pop("starting_main_sha")
        variant.pop("starting_agi_gi_rev")
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            claim = load_claim(self.write_claim(directory, variant))
            self.assertTrue(claim.legacy)
            self.assertEqual(claim.scope, "crx1/image-si/resource-admission")
            self.assertTrue(claim.is_fresh(NOW))

    def test_multi_scope_variant_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            path = self.write_claim(
                directory,
                canonical_claim(scope=["CRX1/a", "CRX2/b"]),
            )
            with self.assertRaisesRegex(ClaimFormatError, "exactly one string"):
                load_claim(path)

    def test_repository_registry_accepts_current_legacy_files(self):
        root = Path(__file__).resolve().parents[1]
        claims, errors = load_registry(root)
        self.assertFalse(errors)
        self.assertGreaterEqual(len(claims), 3)
        self.assertTrue(any(claim.session_id.startswith("chatgpt-session-j-ops") for claim in claims))


if __name__ == "__main__":
    unittest.main()
