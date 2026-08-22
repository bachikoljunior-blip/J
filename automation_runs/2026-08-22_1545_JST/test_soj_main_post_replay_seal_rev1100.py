from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import pathlib
import unittest
from dataclasses import replace

MODULE = pathlib.Path(__file__).with_name("soj_main_post_replay_seal_v1.py")
spec = importlib.util.spec_from_file_location("rev1100", MODULE)
rev1100 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(rev1100)


def canonical_hash(payload):
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def p(ch):
    return "sha256:" + ch * 64


def b(ch):
    return ch * 64


def rev700_fixture(*, result_status="exact_nonempty", reduction_identity=None):
    payload = {
        "schema_version": 1,
        "status": rev1100.REV700_STATUS,
        "main_commit_sha": "a" * 40,
        "caller_binding_identity": b("b"),
        "envelope_identity": b("c"),
        "main_provenance_identity": b("d"),
        "recursive_provenance_identity": p("e"),
        "result_status": result_status,
        "result_lift_digest": p("f"),
        "accounting_binding_digest": p("1"),
        "reduction_identity": reduction_identity or p("2"),
        "child_result_identity": p("3"),
    }
    return payload | {
        "certified": True,
        "exact_contract_join": True,
        "production_provenance_identity": canonical_hash(payload),
    }


def rev1000_fixture(rev700=None, *, outcome_kind="nonempty", bound=8.0, charge=3.0):
    upstream = rev700 or rev700_fixture()
    return {
        "schema_version": 1,
        "status": rev1100.REV1000_STATUS,
        "certified": True,
        "exact": True,
        "complete": True,
        "outcome_kind": outcome_kind,
        "parent_action_degree": 45,
        "child_ground_size": 10,
        "reduction_identity": upstream["reduction_identity"],
        "production_provenance_identity": upstream["production_provenance_identity"],
        "construction_cost_binding_identity": p("4"),
        "construction_multiplicative_cost_bound": bound,
        "charged_log2_reduction_cost": charge,
        "production_cost_provenance_identity": p("5"),
        "provenance_total_cost_identity": p("6"),
        "envelope_identity": p("7"),
    }


class Rev1100MainPostReplaySealTest(unittest.TestCase):
    def certify(self, r700=None, r1000=None, **kwargs):
        r700 = r700 or rev700_fixture()
        r1000 = r1000 or rev1000_fixture(r700)
        return rev1100.certify_main_post_replay_seal(
            r700,
            r1000,
            production_provenance_replay_verified=kwargs.get("production", True),
            post_replay_envelope_replay_verified=kwargs.get("post", True),
        )

    def test_nonempty_success_and_replay(self):
        r700 = rev700_fixture()
        r1000 = rev1000_fixture(r700)
        seal = self.certify(r700, r1000)
        self.assertTrue(seal.certified)
        self.assertEqual(seal.outcome_kind, "nonempty")
        self.assertEqual(seal.main_commit_sha, "a" * 40)
        self.assertTrue(
            rev1100.replay_main_post_replay_seal(
                seal,
                r700,
                r1000,
                production_provenance_replay_verified=True,
                post_replay_envelope_replay_verified=True,
            )
        )

    def test_exact_empty_success(self):
        r700 = rev700_fixture(result_status="exact_empty")
        r1000 = rev1000_fixture(r700, outcome_kind="exact_empty")
        seal = self.certify(r700, r1000)
        self.assertTrue(seal.certified)
        self.assertEqual(seal.outcome_kind, "exact_empty")

    def test_production_replay_gate_is_strict(self):
        self.assertFalse(self.certify(production=False).certified)
        self.assertFalse(self.certify(production=1).certified)

    def test_post_replay_gate_is_strict(self):
        self.assertFalse(self.certify(post=False).certified)
        self.assertFalse(self.certify(post="yes").certified)

    def test_rev700_identity_tamper_fails(self):
        r700 = rev700_fixture()
        r700["main_commit_sha"] = "9" * 40
        self.assertFalse(self.certify(r700, rev1000_fixture()).certified)

    def test_production_provenance_mismatch_fails(self):
        r700 = rev700_fixture()
        r1000 = rev1000_fixture(r700)
        r1000["production_provenance_identity"] = p("8")
        self.assertFalse(self.certify(r700, r1000).certified)

    def test_reduction_mismatch_fails(self):
        r700 = rev700_fixture()
        r1000 = rev1000_fixture(r700)
        r1000["reduction_identity"] = p("8")
        self.assertFalse(self.certify(r700, r1000).certified)

    def test_outcome_mismatch_fails(self):
        r700 = rev700_fixture(result_status="exact_empty")
        r1000 = rev1000_fixture(r700, outcome_kind="nonempty")
        self.assertFalse(self.certify(r700, r1000).certified)

    def test_strict_positive_shrink(self):
        r700 = rev700_fixture()
        r1000 = rev1000_fixture(r700)
        r1000["child_ground_size"] = 45
        self.assertFalse(self.certify(r700, r1000).certified)
        r1000["child_ground_size"] = True
        self.assertFalse(self.certify(r700, r1000).certified)

    def test_power_of_two_cost_required(self):
        r700 = rev700_fixture()
        self.assertFalse(self.certify(r700, rev1000_fixture(r700, bound=6.0, charge=math.log2(6))).certified)
        self.assertFalse(self.certify(r700, rev1000_fixture(r700, bound=8.5, charge=3.0)).certified)

    def test_exact_log2_charge_required(self):
        r700 = rev700_fixture()
        self.assertFalse(self.certify(r700, rev1000_fixture(r700, bound=8.0, charge=2.999)).certified)

    def test_nonfinite_cost_fails_closed(self):
        r700 = rev700_fixture()
        self.assertFalse(self.certify(r700, rev1000_fixture(r700, bound=float("inf"), charge=3.0)).certified)
        self.assertFalse(self.certify(r700, rev1000_fixture(r700, bound=8.0, charge=float("nan"))).certified)

    def test_digest_formats_are_strict(self):
        r700 = rev700_fixture()
        r1000 = rev1000_fixture(r700)
        r1000["envelope_identity"] = "7" * 64
        self.assertFalse(self.certify(r700, r1000).certified)
        r700 = rev700_fixture()
        r700["caller_binding_identity"] = p("b")
        self.assertFalse(self.certify(r700, rev1000_fixture()).certified)

    def test_tampered_seal_does_not_replay(self):
        r700 = rev700_fixture()
        r1000 = rev1000_fixture(r700)
        seal = self.certify(r700, r1000)
        tampered = replace(seal, child_ground_size=9)
        self.assertFalse(
            rev1100.replay_main_post_replay_seal(
                tampered,
                r700,
                r1000,
                production_provenance_replay_verified=True,
                post_replay_envelope_replay_verified=True,
            )
        )

    def test_seal_identity_is_deterministic(self):
        first = self.certify()
        second = self.certify()
        self.assertTrue(first.certified)
        self.assertEqual(first.seal_identity, second.seal_identity)
        self.assertRegex(first.seal_identity, r"^sha256:[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main(verbosity=2)
