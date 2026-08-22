from __future__ import annotations

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from claim_publication_preflight_v1 import (  # noqa: E402
    audit_published_candidate,
    audit_registry,
    preflight_candidate,
)

NOW = datetime.fromisoformat("2026-08-22T19:00:00+09:00")


def canonical_claim(
    claim_id: str,
    *,
    scope: str,
    target_revision: int | None,
    reserved_paths: list[str],
    started: str = "2026-08-22T18:00:00+09:00",
    heartbeat: str = "2026-08-22T18:55:00+09:00",
    status: str = "active",
    branch: str | None = None,
) -> dict:
    branch_name = branch or f"branch-{claim_id}"
    return {
        "schema_version": 2,
        "event_type": "active_session_claim",
        "claim_id": claim_id,
        "session_id": f"session-{claim_id}",
        "started_at_jst": started,
        "heartbeat_at_jst": heartbeat,
        "stale_after_minutes": 90,
        "starting_main_sha": "a" * 40,
        "starting_agi_gi_rev": 1600,
        "target_revision": target_revision,
        "scope": scope,
        "branch": branch_name,
        "reserved_paths": reserved_paths,
        "status": status,
        "agi_state": "NOT_AGI",
    }


class RegistryFixture:
    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="j-claim-preflight-test-")
        self.root = Path(self._tmp.name)
        self.active = self.root / "agi" / "run-history" / "active"
        self.active.mkdir(parents=True)

    def close(self) -> None:
        self._tmp.cleanup()

    def write(self, payload: dict) -> Path:
        path = self.active / f"{payload['claim_id']}.json"
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return path


class ClaimPublicationPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = RegistryFixture()
        self.candidate = canonical_claim(
            "candidate",
            scope="coordination/candidate",
            target_revision=2601,
            reserved_paths=["candidate/path.txt"],
        )

    def tearDown(self) -> None:
        self.fx.close()

    def test_clean_prepublish_is_admitted(self) -> None:
        result = preflight_candidate(self.candidate, self.fx.root, NOW)
        self.assertTrue(result["admitted"])
        self.assertEqual([], result["conflicts"])
        self.assertEqual([], result["reasons"])

    def test_scope_overlap_blocks(self) -> None:
        self.fx.write(canonical_claim("owner", scope="coordination", target_revision=2700, reserved_paths=["owner/a"]))
        result = preflight_candidate(self.candidate, self.fx.root, NOW)
        self.assertFalse(result["admitted"])
        self.assertIn("scope_overlap", result["conflicts"][0]["reasons"])

    def test_target_revision_collision_blocks(self) -> None:
        self.fx.write(canonical_claim("owner", scope="other/scope", target_revision=2601, reserved_paths=["owner/a"]))
        result = preflight_candidate(self.candidate, self.fx.root, NOW)
        self.assertFalse(result["admitted"])
        self.assertIn("target_revision_collision", result["conflicts"][0]["reasons"])

    def test_reserved_path_collision_blocks(self) -> None:
        self.fx.write(canonical_claim("owner", scope="other/scope", target_revision=2700, reserved_paths=["candidate/path.txt"]))
        result = preflight_candidate(self.candidate, self.fx.root, NOW)
        self.assertFalse(result["admitted"])
        self.assertIn("reserved_path_collision", result["conflicts"][0]["reasons"])

    def test_reserved_parent_path_collision_blocks(self) -> None:
        self.fx.write(canonical_claim("owner", scope="other/scope", target_revision=2700, reserved_paths=["candidate"]))
        result = preflight_candidate(self.candidate, self.fx.root, NOW)
        self.assertFalse(result["admitted"])
        self.assertIn("reserved_path_collision", result["conflicts"][0]["reasons"])

    def test_stale_existing_claim_is_ignored(self) -> None:
        self.fx.write(canonical_claim(
            "owner",
            scope="coordination/candidate",
            target_revision=2601,
            reserved_paths=["candidate/path.txt"],
            started="2026-08-22T15:00:00+09:00",
            heartbeat="2026-08-22T16:00:00+09:00",
        ))
        self.assertTrue(preflight_candidate(self.candidate, self.fx.root, NOW)["admitted"])

    def test_completed_existing_claim_is_ignored(self) -> None:
        owner = canonical_claim("owner", scope="coordination/candidate", target_revision=2601, reserved_paths=["candidate/path.txt"])
        owner["completed_at_jst"] = "2026-08-22T18:56:00+09:00"
        owner["status"] = "completed"
        self.fx.write(owner)
        self.assertTrue(preflight_candidate(self.candidate, self.fx.root, NOW)["admitted"])

    def test_stale_candidate_is_rejected(self) -> None:
        candidate = deepcopy(self.candidate)
        candidate["started_at_jst"] = "2026-08-22T15:00:00+09:00"
        candidate["heartbeat_at_jst"] = "2026-08-22T16:00:00+09:00"
        result = preflight_candidate(candidate, self.fx.root, NOW)
        self.assertFalse(result["admitted"])
        self.assertIn("candidate_not_fresh", result["reasons"])

    def test_closed_candidate_is_rejected(self) -> None:
        candidate = deepcopy(self.candidate)
        candidate["status"] = "completed"
        candidate["completed_at_jst"] = "2026-08-22T18:58:00+09:00"
        result = preflight_candidate(candidate, self.fx.root, NOW)
        self.assertFalse(result["admitted"])
        self.assertIn("candidate_closed", result["reasons"])

    def test_invalid_candidate_schema_fails_closed(self) -> None:
        candidate = deepcopy(self.candidate)
        candidate["agi_state"] = "AGI"
        result = preflight_candidate(candidate, self.fx.root, NOW)
        self.assertFalse(result["admitted"])
        self.assertTrue(result["reasons"][0].startswith("candidate_format_error"))

    def test_malformed_registry_fails_closed(self) -> None:
        (self.fx.active / "broken.json").write_text("{not-json", encoding="utf-8")
        result = preflight_candidate(self.candidate, self.fx.root, NOW)
        self.assertFalse(result["admitted"])
        self.assertTrue(result["reasons"][0].startswith("registry_format_error"))

    def test_same_claim_id_already_published_blocks_prepublish(self) -> None:
        self.fx.write(self.candidate)
        result = preflight_candidate(self.candidate, self.fx.root, NOW)
        self.assertFalse(result["admitted"])
        self.assertIn("candidate_already_published", result["reasons"])

    def test_published_audit_clean_for_unique_owner(self) -> None:
        self.fx.write(self.candidate)
        result = audit_published_candidate(self.candidate, self.fx.root, NOW)
        self.assertTrue(result["admitted"])
        self.assertEqual([], result["conflicts"])

    def test_published_audit_missing_owner_fails(self) -> None:
        result = audit_published_candidate(self.candidate, self.fx.root, NOW)
        self.assertFalse(result["admitted"])
        self.assertIn("published_claim_missing_or_duplicate", result["reasons"])

    def test_published_audit_detects_sibling_collision(self) -> None:
        self.fx.write(self.candidate)
        self.fx.write(canonical_claim("owner", scope="other/scope", target_revision=2601, reserved_paths=["owner/a"]))
        result = audit_published_candidate(self.candidate, self.fx.root, NOW)
        self.assertFalse(result["admitted"])
        self.assertIn("parallel_claim_collision", result["reasons"])

    def test_registry_audit_reports_collision_deterministically(self) -> None:
        left = canonical_claim("z-owner", scope="shared/scope", target_revision=2800, reserved_paths=["z/path"])
        right = canonical_claim("a-owner", scope="shared/scope/child", target_revision=2800, reserved_paths=["z/path/child"])
        self.fx.write(left)
        self.fx.write(right)
        first = audit_registry(self.fx.root, NOW)
        second = audit_registry(self.fx.root, NOW)
        self.assertFalse(first["admitted"])
        self.assertEqual(first["conflicts"], second["conflicts"])
        self.assertEqual("a-owner", first["conflicts"][0]["left"]["claim_id"])
        self.assertEqual("z-owner", first["conflicts"][0]["right"]["claim_id"])

    def test_disjoint_claim_passes(self) -> None:
        self.fx.write(canonical_claim("owner", scope="unrelated/scope", target_revision=2700, reserved_paths=["unrelated/path"]))
        self.assertTrue(preflight_candidate(self.candidate, self.fx.root, NOW)["admitted"])

    def test_null_targets_do_not_collide_by_revision_only(self) -> None:
        candidate = canonical_claim("candidate-null", scope="candidate/null", target_revision=None, reserved_paths=["candidate/null.txt"])
        self.fx.write(canonical_claim("owner-null", scope="owner/null", target_revision=None, reserved_paths=["owner/null.txt"]))
        result = preflight_candidate(candidate, self.fx.root, NOW)
        self.assertTrue(result["admitted"])
        self.assertEqual([], result["conflicts"])


if __name__ == "__main__":
    unittest.main()
