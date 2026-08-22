from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
import types
import unittest

MODULE_PATH = pathlib.Path(__file__).with_name("soj_recursive_production_provenance_join_v1.py")
spec = importlib.util.spec_from_file_location("rev700_impl", MODULE_PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def digest(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    return hashlib.sha256(blob).hexdigest()


def bare(ch: str) -> str:
    return ch * 64


def pref(ch: str) -> str:
    return "sha256:" + bare(ch)


def gitsha(ch: str) -> str:
    return ch * 40


def make_envelope(empty: bool = False) -> dict:
    payload = {
        "schema": "corrected-soj-production-caller-replay-envelope-v1",
        "caller_binding_identity": bare("1"),
        "mode": "larger_ground_recursive",
        "result_status": "exact_empty" if empty else "exact_nonempty",
        "original_instance_identity": bare("2"),
        "transition_identity": bare("3"),
        "result_identity": bare("c"),
        "accounted_work": 17,
        "max_accounted_work": 20,
        "current_domain_size": 10,
        "original_root_n": 12,
        "replay_verified": True,
    }
    payload["envelope_identity"] = digest(payload)
    return payload


def make_main(envelope: dict | None = None) -> dict:
    envelope = make_envelope() if envelope is None else envelope
    identities = {
        "branch_accounting_identity": bare("e"),
        "branch_certificate_identity": bare("c"),
        "original_instance_identity": envelope["original_instance_identity"],
        "result_identity": envelope["result_identity"],
        "transition_identity": envelope["transition_identity"],
    }
    artifacts = []
    for i, field in enumerate(sorted(identities)):
        artifacts.append(
            {
                "identity_field": field,
                "identity": identities[field],
                "source_commit_sha": gitsha(str((i + 1) % 10)),
                "source_path": f"evidence/{field}.json",
                "artifact_sha256": bare(chr(ord("a") + i)),
            }
        )
    payload = {
        "schema": "corrected-soj-production-main-provenance-v1",
        "main_commit_sha": gitsha("f"),
        "caller_binding_identity": envelope["caller_binding_identity"],
        "envelope_identity": envelope["envelope_identity"],
        "verified_artifacts": artifacts,
    }
    payload["provenance_identity"] = digest(payload)
    return payload


def make_recursive(empty: bool = False) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        schema_version=1,
        status="certified_corrected_soj_recursive_caller_provenance_binding",
        certified=True,
        exact_contract_binding=True,
        caller_binding_identity=bare("1"),
        result_status="exact_empty" if empty else "exact_nonempty",
        result_lift_digest=pref("c"),
        accounting_binding_digest=pref("e"),
        reduction_identity=pref("a"),
        child_result_identity=pref("b"),
        provenance_identity=pref("9"),
        reason="fixture",
    )


def redigest_envelope(envelope: dict) -> None:
    payload = dict(envelope)
    payload.pop("envelope_identity", None)
    envelope["envelope_identity"] = digest(payload)


def redigest_main(main: dict) -> None:
    payload = dict(main)
    payload.pop("provenance_identity", None)
    main["provenance_identity"] = digest(payload)


class Rev700Tests(unittest.TestCase):
    def certify(self, envelope=None, main=None, recursive=None, *, main_replay=True, recursive_replay=True):
        envelope = make_envelope() if envelope is None else envelope
        main = make_main(envelope) if main is None else main
        recursive = make_recursive() if recursive is None else recursive
        return mod.certify_recursive_production_provenance_join(
            envelope,
            main,
            recursive,
            main_provenance_replay_verified=main_replay,
            recursive_provenance_replay_verified=recursive_replay,
        )

    def test_nonempty_success_and_replay(self):
        envelope = make_envelope()
        main = make_main(envelope)
        recursive = make_recursive()
        cert = self.certify(envelope, main, recursive)
        self.assertTrue(cert.certified)
        self.assertEqual(cert.result_status, "exact_nonempty")
        self.assertEqual(cert.result_lift_digest, pref("c"))
        self.assertTrue(mod.replay_recursive_production_provenance_join(
            cert, envelope, main, recursive,
            main_provenance_replay_verified=True,
            recursive_provenance_replay_verified=True,
        ))

    def test_exact_empty_success(self):
        envelope = make_envelope(True)
        main = make_main(envelope)
        recursive = make_recursive(True)
        cert = self.certify(envelope, main, recursive)
        self.assertTrue(cert.certified)
        self.assertEqual(cert.result_status, "exact_empty")

    def test_requires_main_replay(self):
        cert = self.certify(main_replay=False)
        self.assertFalse(cert.certified)
        self.assertIn("main_provenance_replay_verified", cert.reason)

    def test_requires_recursive_replay(self):
        cert = self.certify(recursive_replay=False)
        self.assertFalse(cert.certified)
        self.assertIn("recursive_provenance_replay_verified", cert.reason)

    def test_rejects_small_ground_mode(self):
        envelope = make_envelope(); envelope["mode"] = "small_ground_terminal"; redigest_envelope(envelope)
        main = make_main(envelope)
        cert = self.certify(envelope, main)
        self.assertFalse(cert.certified)
        self.assertIn("larger_ground_recursive", cert.reason)

    def test_rejects_bad_envelope_digest(self):
        envelope = make_envelope(); envelope["accounted_work"] = 18
        cert = self.certify(envelope, make_main(envelope))
        self.assertFalse(cert.certified)
        self.assertIn("envelope_identity", cert.reason)

    def test_rejects_bad_main_digest(self):
        envelope = make_envelope(); main = make_main(envelope); main["main_commit_sha"] = gitsha("e")
        cert = self.certify(envelope, main)
        self.assertFalse(cert.certified)
        self.assertIn("main provenance identity", cert.reason)

    def test_rejects_caller_identity_mismatch(self):
        recursive = make_recursive(); recursive.caller_binding_identity = bare("8")
        cert = self.certify(recursive=recursive)
        self.assertFalse(cert.certified)
        self.assertIn("caller binding identity", cert.reason)

    def test_rejects_envelope_identity_not_main_authenticated(self):
        envelope = make_envelope(); main = make_main(envelope); main["envelope_identity"] = bare("8"); redigest_main(main)
        cert = self.certify(envelope, main)
        self.assertFalse(cert.certified)
        self.assertIn("envelope identity", cert.reason)

    def test_rejects_result_status_mismatch(self):
        recursive = make_recursive(True)
        cert = self.certify(recursive=recursive)
        self.assertFalse(cert.certified)
        self.assertIn("result status", cert.reason)

    def test_rejects_result_identity_not_result_lift(self):
        recursive = make_recursive(); recursive.result_lift_digest = pref("8")
        cert = self.certify(recursive=recursive)
        self.assertFalse(cert.certified)
        self.assertIn("result-lift digest", cert.reason)

    def test_rejects_branch_certificate_artifact_mismatch(self):
        envelope = make_envelope(); main = make_main(envelope)
        main["verified_artifacts"][1]["identity"] = bare("8"); redigest_main(main)
        cert = self.certify(envelope, main)
        self.assertFalse(cert.certified)
        self.assertIn("branch certificate", cert.reason)

    def test_rejects_branch_accounting_artifact_mismatch(self):
        envelope = make_envelope(); main = make_main(envelope)
        main["verified_artifacts"][0]["identity"] = bare("8"); redigest_main(main)
        cert = self.certify(envelope, main)
        self.assertFalse(cert.certified)
        self.assertIn("branch accounting", cert.reason)

    def test_rejects_original_instance_artifact_mismatch(self):
        envelope = make_envelope(); main = make_main(envelope)
        main["verified_artifacts"][2]["identity"] = bare("8"); redigest_main(main)
        cert = self.certify(envelope, main)
        self.assertFalse(cert.certified)
        self.assertIn("original instance", cert.reason)

    def test_rejects_transition_artifact_mismatch(self):
        envelope = make_envelope(); main = make_main(envelope)
        main["verified_artifacts"][4]["identity"] = bare("8"); redigest_main(main)
        cert = self.certify(envelope, main)
        self.assertFalse(cert.certified)
        self.assertIn("transition identity", cert.reason)

    def test_rejects_noncanonical_artifact_order(self):
        envelope = make_envelope(); main = make_main(envelope)
        main["verified_artifacts"][0], main["verified_artifacts"][1] = main["verified_artifacts"][1], main["verified_artifacts"][0]
        redigest_main(main)
        cert = self.certify(envelope, main)
        self.assertFalse(cert.certified)
        self.assertIn("canonical rev600 order", cert.reason)

    def test_rejects_noncanonical_artifact_field_set(self):
        envelope = make_envelope(); main = make_main(envelope)
        main["verified_artifacts"][0]["extra"] = True; redigest_main(main)
        cert = self.certify(envelope, main)
        self.assertFalse(cert.certified)
        self.assertIn("noncanonical field set", cert.reason)

    def test_rejects_unsafe_source_path(self):
        envelope = make_envelope(); main = make_main(envelope)
        main["verified_artifacts"][0]["source_path"] = "../outside.json"; redigest_main(main)
        cert = self.certify(envelope, main)
        self.assertFalse(cert.certified)
        self.assertIn("canonical relative POSIX", cert.reason)

    def test_rejects_work_over_envelope_cap(self):
        envelope = make_envelope(); envelope["accounted_work"] = 21; redigest_envelope(envelope)
        main = make_main(envelope)
        cert = self.certify(envelope, main)
        self.assertFalse(cert.certified)
        self.assertIn("exceeds max_accounted_work", cert.reason)

    def test_rejects_domain_over_original_root(self):
        envelope = make_envelope(); envelope["current_domain_size"] = 13; redigest_envelope(envelope)
        main = make_main(envelope)
        cert = self.certify(envelope, main)
        self.assertFalse(cert.certified)
        self.assertIn("exceeds original_root_n", cert.reason)

    def test_rejects_nonliteral_recursive_certified_flag(self):
        recursive = make_recursive(); recursive.certified = 1
        self.assertFalse(self.certify(recursive=recursive).certified)

    def test_deterministic_and_tamper_sensitive(self):
        a = self.certify(); b = self.certify()
        self.assertEqual(a.production_provenance_identity, b.production_provenance_identity)
        envelope = make_envelope(); envelope["max_accounted_work"] = 21; redigest_envelope(envelope)
        main = make_main(envelope)
        c = self.certify(envelope, main)
        self.assertTrue(c.certified)
        self.assertNotEqual(a.production_provenance_identity, c.production_provenance_identity)


if __name__ == "__main__":
    unittest.main()
