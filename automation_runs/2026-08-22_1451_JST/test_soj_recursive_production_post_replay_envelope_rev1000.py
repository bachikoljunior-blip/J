from __future__ import annotations

import dataclasses
import importlib.util
from pathlib import Path
import sys
import unittest

MODULE_PATH = Path(__file__).with_name(
    "soj_recursive_production_post_replay_envelope_v1.py"
)
_spec = importlib.util.spec_from_file_location("rev1000", MODULE_PATH)
assert _spec and _spec.loader
m = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = m
_spec.loader.exec_module(m)

D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
D3 = "sha256:" + "3" * 64
D4 = "sha256:" + "4" * 64
D5 = "sha256:" + "5" * 64


def make_view(kind: str, upstream: str, **overrides):
    args = dict(
        kind=kind,
        replay_verified=True,
        exact=True,
        complete=True,
        outcome_kind="nonempty",
        parent_action_degree=16,
        child_ground_size=8,
        reduction_identity=D1,
        production_provenance_identity=D2,
        construction_cost_binding_identity=D3,
        construction_multiplicative_cost_bound=8.0,
        charged_log2_reduction_cost=3.0,
        upstream_identity=upstream,
    )
    args.update(overrides)
    return m.certify_post_replay_view(**args)


class Rev1000Tests(unittest.TestCase):
    def test_success_and_replay(self):
        a = make_view("production_cost_provenance", D4)
        b = make_view("provenance_total_cost", D5)
        self.assertTrue(a.replay_verified)
        self.assertTrue(b.replay_verified)
        cert = m.certify_recursive_production_post_replay_envelope(a, b)
        self.assertTrue(cert.certified)
        self.assertTrue(cert.exact)
        self.assertTrue(cert.complete)
        self.assertEqual(cert.outcome_kind, "nonempty")
        self.assertEqual(cert.production_cost_provenance_identity, D4)
        self.assertEqual(cert.provenance_total_cost_identity, D5)
        self.assertTrue(m.replay_recursive_production_post_replay_envelope(cert, a, b))

    def test_exact_empty_preserved(self):
        a = make_view("production_cost_provenance", D4, outcome_kind="exact_empty")
        b = make_view("provenance_total_cost", D5, outcome_kind="exact_empty")
        cert = m.certify_recursive_production_post_replay_envelope(a, b)
        self.assertTrue(cert.certified)
        self.assertEqual(cert.outcome_kind, "exact_empty")

    def test_replay_gate_must_be_strict_true(self):
        a = make_view("production_cost_provenance", D4, replay_verified=False)
        self.assertFalse(a.replay_verified)
        self.assertIn("independently replay-verified", a.reason)
        bad_type = make_view("production_cost_provenance", D4, replay_verified=1)
        self.assertFalse(bad_type.replay_verified)
        self.assertIn("strict boolean", bad_type.reason)

    def test_exact_and_complete_must_be_strict_true(self):
        self.assertFalse(
            make_view("production_cost_provenance", D4, exact=False).replay_verified
        )
        self.assertFalse(
            make_view("production_cost_provenance", D4, complete=False).replay_verified
        )
        self.assertFalse(
            make_view("production_cost_provenance", D4, exact=1).replay_verified
        )

    def test_role_is_closed(self):
        v = make_view("unknown", D4)
        self.assertFalse(v.replay_verified)
        self.assertIn("compatibility role", v.reason)

    def test_outcome_is_closed(self):
        v = make_view("production_cost_provenance", D4, outcome_kind="unknown")
        self.assertFalse(v.replay_verified)
        self.assertIn("exact_empty versus nonempty", v.reason)

    def test_strict_shrink_required(self):
        equal = make_view(
            "production_cost_provenance", D4, parent_action_degree=8, child_ground_size=8
        )
        self.assertFalse(equal.replay_verified)
        larger = make_view(
            "production_cost_provenance", D4, parent_action_degree=8, child_ground_size=9
        )
        self.assertFalse(larger.replay_verified)
        bool_degree = make_view(
            "production_cost_provenance", D4, parent_action_degree=True
        )
        self.assertFalse(bool_degree.replay_verified)

    def test_digests_are_canonical(self):
        for field in (
            "reduction_identity",
            "production_provenance_identity",
            "construction_cost_binding_identity",
            "upstream_identity",
        ):
            with self.subTest(field=field):
                v = make_view("production_cost_provenance", D4, **{field: "not-a-digest"})
                self.assertFalse(v.replay_verified)
                self.assertIn("canonical sha256", v.reason)

    def test_cost_bound_power_of_two(self):
        nonintegral = make_view(
            "production_cost_provenance",
            D4,
            construction_multiplicative_cost_bound=8.5,
            charged_log2_reduction_cost=3.0,
        )
        self.assertFalse(nonintegral.replay_verified)
        nonpower = make_view(
            "production_cost_provenance",
            D4,
            construction_multiplicative_cost_bound=6.0,
            charged_log2_reduction_cost=2.0,
        )
        self.assertFalse(nonpower.replay_verified)
        boolean = make_view(
            "production_cost_provenance",
            D4,
            construction_multiplicative_cost_bound=True,
            charged_log2_reduction_cost=0.0,
        )
        self.assertFalse(boolean.replay_verified)

    def test_charge_must_be_exact_log2(self):
        v = make_view(
            "production_cost_provenance", D4, charged_log2_reduction_cost=2.999999999
        )
        self.assertFalse(v.replay_verified)
        self.assertIn("exactly log2", v.reason)

    def test_nan_and_inf_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                v = make_view(
                    "production_cost_provenance",
                    D4,
                    construction_multiplicative_cost_bound=value,
                )
                self.assertFalse(v.replay_verified)

    def test_view_identity_detects_mutation(self):
        a = make_view("production_cost_provenance", D4)
        tampered = dataclasses.replace(a, child_ground_size=7)
        self.assertFalse(m.replay_post_replay_view(tampered))

    def test_roles_cannot_be_swapped(self):
        a = make_view("provenance_total_cost", D4)
        b = make_view("production_cost_provenance", D5)
        cert = m.certify_recursive_production_post_replay_envelope(a, b)
        self.assertFalse(cert.certified)
        self.assertIn("first view", cert.reason)

    def test_shared_field_mismatch_fail_closed(self):
        fields_and_values = {
            "outcome_kind": "exact_empty",
            "parent_action_degree": 32,
            "child_ground_size": 4,
            "reduction_identity": "sha256:" + "6" * 64,
            "production_provenance_identity": "sha256:" + "7" * 64,
            "construction_cost_binding_identity": "sha256:" + "8" * 64,
            "construction_multiplicative_cost_bound": 16.0,
            "charged_log2_reduction_cost": 4.0,
        }
        a = make_view("production_cost_provenance", D4)
        for field, value in fields_and_values.items():
            with self.subTest(field=field):
                kwargs = {field: value}
                if field == "construction_multiplicative_cost_bound":
                    kwargs["charged_log2_reduction_cost"] = 4.0
                if field == "charged_log2_reduction_cost":
                    kwargs["construction_multiplicative_cost_bound"] = 16.0
                b = make_view("provenance_total_cost", D5, **kwargs)
                cert = m.certify_recursive_production_post_replay_envelope(a, b)
                self.assertFalse(cert.certified)

    def test_upstream_identities_may_differ(self):
        a = make_view("production_cost_provenance", D4)
        b = make_view("provenance_total_cost", D5)
        cert = m.certify_recursive_production_post_replay_envelope(a, b)
        self.assertTrue(cert.certified)
        self.assertNotEqual(
            cert.production_cost_provenance_identity, cert.provenance_total_cost_identity
        )

    def test_envelope_identity_detects_mutation(self):
        a = make_view("production_cost_provenance", D4)
        b = make_view("provenance_total_cost", D5)
        cert = m.certify_recursive_production_post_replay_envelope(a, b)
        tampered = dataclasses.replace(cert, charged_log2_reduction_cost=2.0)
        self.assertFalse(
            m.replay_recursive_production_post_replay_envelope(tampered, a, b)
        )


if __name__ == "__main__":
    unittest.main()
