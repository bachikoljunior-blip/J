from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from soj_main_provenance_gate_v1 import (  # noqa: E402
    MainProvenanceError,
    replay_main_integrated_provenance,
    seal_public_replay_envelope,
    verify_main_integrated_provenance,
)


def canonical_digest(value: dict) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


class Rev600MainProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="rev600-prov-"))
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "rev600@example.invalid")
        self.git("config", "user.name", "rev600-test")

        self.ids = {
            "original_instance_identity": "1" * 64,
            "transition_identity": "2" * 64,
            "result_identity": "3" * 64,
            "branch_certificate_identity": "4" * 64,
            "branch_accounting_identity": "5" * 64,
        }
        evidence = self.repo / "evidence"
        evidence.mkdir()
        self.paths: dict[str, str] = {}
        self.hashes: dict[str, str] = {}
        for field, identity in self.ids.items():
            path = f"evidence/{field}.json"
            blob = json.dumps(
                {field: identity, "kind": "rev600-test-evidence"},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8") + b"\n"
            (self.repo / path).write_bytes(blob)
            self.paths[field] = path
            self.hashes[field] = hashlib.sha256(blob).hexdigest()

        wrong = json.dumps(
            {
                "original_instance_identity": "9" * 64,
                "kind": "wrong-evidence",
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        (evidence / "wrong.json").write_bytes(wrong)
        self.wrong_hash = hashlib.sha256(wrong).hexdigest()
        (evidence / "not-json.txt").write_text("not-json\n", encoding="utf-8")
        self.bad_json_hash = hashlib.sha256(b"not-json\n").hexdigest()

        self.git("add", "evidence")
        self.git("commit", "-q", "-m", "evidence")
        self.source_commit = self.git("rev-parse", "HEAD").strip()

        (self.repo / "README.md").write_text("tip\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-q", "-m", "tip")
        self.main_commit = self.git("rev-parse", "HEAD").strip()

        payload = {
            "schema": "corrected-soj-production-caller-binding-v1",
            "canonical": True,
            "exact": True,
            "mode": "larger_ground_recursive",
            "original_instance_identity": self.ids["original_instance_identity"],
            "transition_identity": self.ids["transition_identity"],
            "result_status": "exact_nonempty",
            "result_identity": self.ids["result_identity"],
            "accounted_work": 17,
            "branch_certificate_identity": self.ids["branch_certificate_identity"],
            "branch_accounting_identity": self.ids["branch_accounting_identity"],
        }
        self.binding = payload | {
            "caller_binding_identity": canonical_digest(payload)
        }
        self.envelope = seal_public_replay_envelope(
            self.binding,
            replay_verified=True,
            max_accounted_work=21,
            current_domain_size=8,
            original_root_n=13,
        )
        self.requirements = {
            field: {
                "schema": "corrected-soj-main-provenance-requirement-v1",
                "source_commit_sha": self.source_commit,
                "source_path": self.paths[field],
                "artifact_sha256": self.hashes[field],
                "identity_key": field,
            }
            for field in self.ids
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def git(self, *args: str) -> str:
        cp = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return cp.stdout

    def verify(self):
        return verify_main_integrated_provenance(
            self.repo,
            main_ref="HEAD",
            binding=self.binding,
            envelope=self.envelope,
            artifact_requirements=self.requirements,
        )

    def test_valid_bundle_binds_exact_main_commit(self) -> None:
        result = self.verify()
        self.assertEqual(result.main_commit_sha, self.main_commit)
        self.assertEqual(result.envelope_identity, self.envelope["envelope_identity"])
        self.assertEqual(len(result.verified_artifacts), 5)

    def test_replay_is_deterministic(self) -> None:
        first = self.verify()
        replayed = replay_main_integrated_provenance(
            first.as_dict(),
            self.repo,
            main_ref="HEAD",
            binding=self.binding,
            envelope=self.envelope,
            artifact_requirements=self.requirements,
        )
        self.assertEqual(replayed, first)

    def test_replay_rejects_tampered_provenance_identity(self) -> None:
        raw = self.verify().as_dict()
        raw["provenance_identity"] = "f" * 64
        with self.assertRaises(MainProvenanceError):
            replay_main_integrated_provenance(
                raw,
                self.repo,
                main_ref="HEAD",
                binding=self.binding,
                envelope=self.envelope,
                artifact_requirements=self.requirements,
            )

    def test_missing_requirement_fails_closed(self) -> None:
        req = dict(self.requirements)
        req.pop("result_identity")
        with self.assertRaises(MainProvenanceError):
            verify_main_integrated_provenance(
                self.repo,
                main_ref="HEAD",
                binding=self.binding,
                envelope=self.envelope,
                artifact_requirements=req,
            )

    def test_extra_requirement_fails_closed(self) -> None:
        req = dict(self.requirements)
        req["extra_identity"] = dict(next(iter(req.values())))
        with self.assertRaises(MainProvenanceError):
            verify_main_integrated_provenance(
                self.repo,
                main_ref="HEAD",
                binding=self.binding,
                envelope=self.envelope,
                artifact_requirements=req,
            )

    def test_unreachable_or_unknown_source_commit_fails_closed(self) -> None:
        req = {k: dict(v) for k, v in self.requirements.items()}
        req["result_identity"]["source_commit_sha"] = "f" * 40
        with self.assertRaises(MainProvenanceError):
            verify_main_integrated_provenance(
                self.repo,
                main_ref="HEAD",
                binding=self.binding,
                envelope=self.envelope,
                artifact_requirements=req,
            )

    def test_artifact_content_hash_mismatch_fails_closed(self) -> None:
        req = {k: dict(v) for k, v in self.requirements.items()}
        req["transition_identity"]["artifact_sha256"] = "0" * 64
        with self.assertRaises(MainProvenanceError):
            verify_main_integrated_provenance(
                self.repo,
                main_ref="HEAD",
                binding=self.binding,
                envelope=self.envelope,
                artifact_requirements=req,
            )

    def test_main_path_drift_after_source_commit_fails_closed(self) -> None:
        target = self.repo / self.paths["result_identity"]
        data = json.loads(target.read_text(encoding="utf-8"))
        data["later_note"] = True
        target.write_text(
            json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        self.git("add", self.paths["result_identity"])
        self.git("commit", "-q", "-m", "drift")
        with self.assertRaises(MainProvenanceError):
            self.verify()

    def test_json_identity_mismatch_fails_closed(self) -> None:
        req = {k: dict(v) for k, v in self.requirements.items()}
        req["original_instance_identity"] = {
            "schema": "corrected-soj-main-provenance-requirement-v1",
            "source_commit_sha": self.source_commit,
            "source_path": "evidence/wrong.json",
            "artifact_sha256": self.wrong_hash,
            "identity_key": "original_instance_identity",
        }
        with self.assertRaises(MainProvenanceError):
            verify_main_integrated_provenance(
                self.repo,
                main_ref="HEAD",
                binding=self.binding,
                envelope=self.envelope,
                artifact_requirements=req,
            )

    def test_non_json_evidence_fails_closed(self) -> None:
        req = {k: dict(v) for k, v in self.requirements.items()}
        req["original_instance_identity"] = {
            "schema": "corrected-soj-main-provenance-requirement-v1",
            "source_commit_sha": self.source_commit,
            "source_path": "evidence/not-json.txt",
            "artifact_sha256": self.bad_json_hash,
            "identity_key": "original_instance_identity",
        }
        with self.assertRaises(MainProvenanceError):
            verify_main_integrated_provenance(
                self.repo,
                main_ref="HEAD",
                binding=self.binding,
                envelope=self.envelope,
                artifact_requirements=req,
            )

    def test_path_traversal_is_rejected(self) -> None:
        req = {k: dict(v) for k, v in self.requirements.items()}
        req["result_identity"]["source_path"] = "../evidence/result_identity.json"
        with self.assertRaises(MainProvenanceError):
            verify_main_integrated_provenance(
                self.repo,
                main_ref="HEAD",
                binding=self.binding,
                envelope=self.envelope,
                artifact_requirements=req,
            )

    def test_path_colon_is_rejected(self) -> None:
        req = {k: dict(v) for k, v in self.requirements.items()}
        req["result_identity"]["source_path"] = "evidence:result_identity.json"
        with self.assertRaises(MainProvenanceError):
            verify_main_integrated_provenance(
                self.repo,
                main_ref="HEAD",
                binding=self.binding,
                envelope=self.envelope,
                artifact_requirements=req,
            )

    def test_identity_key_cannot_be_redirected(self) -> None:
        req = {k: dict(v) for k, v in self.requirements.items()}
        req["result_identity"]["identity_key"] = "transition_identity"
        with self.assertRaises(MainProvenanceError):
            verify_main_integrated_provenance(
                self.repo,
                main_ref="HEAD",
                binding=self.binding,
                envelope=self.envelope,
                artifact_requirements=req,
            )

    def test_nonliteral_binding_boolean_fails_closed(self) -> None:
        binding = dict(self.binding)
        binding["canonical"] = 1
        with self.assertRaises(MainProvenanceError):
            verify_main_integrated_provenance(
                self.repo,
                main_ref="HEAD",
                binding=binding,
                envelope=self.envelope,
                artifact_requirements=self.requirements,
            )

    def test_envelope_identity_tamper_fails_closed(self) -> None:
        envelope = dict(self.envelope)
        envelope["envelope_identity"] = "a" * 64
        with self.assertRaises(MainProvenanceError):
            verify_main_integrated_provenance(
                self.repo,
                main_ref="HEAD",
                binding=self.binding,
                envelope=envelope,
                artifact_requirements=self.requirements,
            )

    def test_envelope_domain_drift_fails_closed(self) -> None:
        envelope = dict(self.envelope)
        envelope["current_domain_size"] = 14
        with self.assertRaises(MainProvenanceError):
            verify_main_integrated_provenance(
                self.repo,
                main_ref="HEAD",
                binding=self.binding,
                envelope=envelope,
                artifact_requirements=self.requirements,
            )

    def test_envelope_work_cap_drift_fails_closed(self) -> None:
        envelope = dict(self.envelope)
        envelope["max_accounted_work"] = 16
        with self.assertRaises(MainProvenanceError):
            verify_main_integrated_provenance(
                self.repo,
                main_ref="HEAD",
                binding=self.binding,
                envelope=envelope,
                artifact_requirements=self.requirements,
            )


if __name__ == "__main__":
    unittest.main()
