from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
import types
import unittest

MODULE_PATH = pathlib.Path(__file__).with_name("soj_recursive_caller_provenance_v1.py")
spec = importlib.util.spec_from_file_location("rev650_impl", MODULE_PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def pref(ch: str) -> str:
    return "sha256:" + ch * 64


def bare(ch: str) -> str:
    return ch * 64


def caller_digest(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()


def make_lift(empty: bool = False) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        schema_version=1,
        status=("certified_exact_empty_parent_johnson_result" if empty else "certified_exact_parent_johnson_coset_lift"),
        certified=True,
        exact=True,
        complete=True,
        parent_action_degree=6,
        child_ground_size=4,
        reduction_identity=pref("a"),
        child_result_identity=pref("b"),
        parent_representative=None if empty else (0, 1, 2, 3, 4, 5),
        parent_stabilizer_generators=() if empty else ((0, 1, 2, 3, 4, 5),),
        transcript_digest=pref("c"),
    )


def make_accounting(empty: bool = False) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        schema_version=1,
        status="certified_johnson_recursive_result_accounting_binding",
        certified=True,
        exact=True,
        complete=True,
        outcome_kind="exact_empty" if empty else "nonempty",
        parent_action_degree=6,
        child_ground_size=4,
        reduction_identity=pref("a"),
        handoff_digest=pref("d"),
        child_result_identity=pref("b"),
        result_lift_digest=pref("c"),
        charged_log2_reduction_cost=3.5,
        binding_digest=pref("e"),
    )


def make_caller(empty: bool = False) -> dict:
    payload = {
        "schema": "corrected-soj-production-caller-binding-v1",
        "canonical": True,
        "exact": True,
        "mode": "larger_ground_recursive",
        "original_instance_identity": bare("1"),
        "transition_identity": bare("2"),
        "result_status": "exact_empty" if empty else "exact_nonempty",
        "result_identity": bare("c"),
        "accounted_work": 17,
        "branch_certificate_identity": bare("c"),
        "branch_accounting_identity": bare("e"),
    }
    payload["caller_binding_identity"] = caller_digest(payload)
    return payload


class Rev650Tests(unittest.TestCase):
    def certify(self, caller=None, lift=None, accounting=None):
        return mod.certify_recursive_caller_provenance(
            make_caller() if caller is None else caller,
            make_lift() if lift is None else lift,
            make_accounting() if accounting is None else accounting,
            result_lift_replay_verified=True,
            accounting_binding_replay_verified=True,
        )

    def test_nonempty_success_and_replay(self):
        caller, lift, accounting = make_caller(), make_lift(), make_accounting()
        cert = self.certify(caller, lift, accounting)
        self.assertTrue(cert.certified)
        self.assertEqual(cert.result_status, "exact_nonempty")
        self.assertEqual(cert.result_lift_digest, pref("c"))
        self.assertEqual(cert.accounting_binding_digest, pref("e"))
        self.assertTrue(mod.replay_recursive_caller_provenance(
            cert, caller, lift, accounting,
            result_lift_replay_verified=True,
            accounting_binding_replay_verified=True,
        ))

    def test_exact_empty_success(self):
        cert = mod.certify_recursive_caller_provenance(
            make_caller(True), make_lift(True), make_accounting(True),
            result_lift_replay_verified=True,
            accounting_binding_replay_verified=True,
        )
        self.assertTrue(cert.certified)
        self.assertEqual(cert.result_status, "exact_empty")

    def test_requires_replayed_result_lift(self):
        cert = mod.certify_recursive_caller_provenance(
            make_caller(), make_lift(), make_accounting(),
            result_lift_replay_verified=False,
            accounting_binding_replay_verified=True,
        )
        self.assertFalse(cert.certified)
        self.assertIn("result_lift", cert.reason)

    def test_requires_replayed_accounting(self):
        cert = mod.certify_recursive_caller_provenance(
            make_caller(), make_lift(), make_accounting(),
            result_lift_replay_verified=True,
            accounting_binding_replay_verified=False,
        )
        self.assertFalse(cert.certified)
        self.assertIn("accounting_binding", cert.reason)

    def test_rejects_wrong_mode(self):
        caller = make_caller(); caller["mode"] = "small_ground_terminal"
        self.assertFalse(self.certify(caller=caller).certified)

    def test_rejects_caller_digest_drift(self):
        caller = make_caller(); caller["accounted_work"] = 18
        cert = self.certify(caller=caller)
        self.assertFalse(cert.certified)
        self.assertIn("does not replay", cert.reason)

    def test_rejects_result_status_mismatch(self):
        caller = make_caller(); caller["result_status"] = "exact_empty"
        unsigned = dict(caller); unsigned.pop("caller_binding_identity")
        caller["caller_binding_identity"] = caller_digest(unsigned)
        cert = self.certify(caller=caller)
        self.assertFalse(cert.certified)
        self.assertIn("result_status", cert.reason)

    def test_rejects_lift_digest_not_caller_result(self):
        lift = make_lift(); lift.transcript_digest = pref("f")
        accounting = make_accounting(); accounting.result_lift_digest = pref("f")
        cert = self.certify(lift=lift, accounting=accounting)
        self.assertFalse(cert.certified)
        self.assertIn("result identity", cert.reason)

    def test_rejects_accounting_digest_not_caller_accounting(self):
        accounting = make_accounting(); accounting.binding_digest = pref("f")
        cert = self.certify(accounting=accounting)
        self.assertFalse(cert.certified)
        self.assertIn("accounting identity", cert.reason)

    def test_rejects_accounting_not_bound_to_lift(self):
        accounting = make_accounting(); accounting.result_lift_digest = pref("f")
        cert = self.certify(accounting=accounting)
        self.assertFalse(cert.certified)
        self.assertIn("result_lift", cert.reason)

    def test_rejects_reduction_identity_mismatch(self):
        accounting = make_accounting(); accounting.reduction_identity = pref("f")
        cert = self.certify(accounting=accounting)
        self.assertFalse(cert.certified)
        self.assertIn("reduction identity", cert.reason)

    def test_rejects_child_result_identity_mismatch(self):
        accounting = make_accounting(); accounting.child_result_identity = pref("f")
        cert = self.certify(accounting=accounting)
        self.assertFalse(cert.certified)
        self.assertIn("child result identity", cert.reason)

    def test_rejects_nonliteral_exact_flag(self):
        lift = make_lift(); lift.exact = 1
        self.assertFalse(self.certify(lift=lift).certified)

    def test_rejects_malformed_sha(self):
        accounting = make_accounting(); accounting.binding_digest = "sha256:" + "E" * 64
        self.assertFalse(self.certify(accounting=accounting).certified)

    def test_rejects_noncanonical_generators(self):
        lift = make_lift(); lift.parent_stabilizer_generators = ((1, 0, 2, 3, 4, 5), (0, 1, 2, 3, 4, 5))
        self.assertFalse(self.certify(lift=lift).certified)

    def test_deterministic_and_tamper_sensitive(self):
        a = self.certify(); b = self.certify()
        self.assertEqual(a.provenance_identity, b.provenance_identity)
        caller = make_caller(); caller["accounted_work"] = 18
        unsigned = dict(caller); unsigned.pop("caller_binding_identity")
        caller["caller_binding_identity"] = caller_digest(unsigned)
        c = self.certify(caller=caller)
        self.assertTrue(c.certified)
        self.assertNotEqual(a.provenance_identity, c.provenance_identity)


if __name__ == "__main__":
    unittest.main()
