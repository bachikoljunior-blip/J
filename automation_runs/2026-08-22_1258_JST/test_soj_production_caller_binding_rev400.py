from __future__ import annotations

import copy
import hashlib
import json
import unittest
from types import MappingProxyType

from soj_production_caller_binding_v1 import CallerBindingError, bind_production_caller


def h(ch: str) -> str:
    return ch * 64


def small(status: str = "exact_nonempty") -> dict:
    return {
        "canonical": True,
        "exact": True,
        "mode": "small_ground_terminal",
        "transition_identity": h("1"),
        "original_instance_identity": h("2"),
        "result_status": status,
        "result_identity": h("3"),
        "small_ground_terminal": {
            "canonical": True,
            "exact": True,
            "transition_identity": h("1"),
            "original_instance_identity": h("2"),
            "result_status": status,
            "result_identity": h("3"),
            "terminal_certificate_identity": h("4"),
            "terminal_accounting_identity": h("5"),
            "accounting_result_identity": h("3"),
            "accounted_work": 7,
        },
        "larger_ground_recursive": None,
    }


def recursive(status: str = "exact_nonempty") -> dict:
    return {
        "canonical": True,
        "exact": True,
        "mode": "larger_ground_recursive",
        "transition_identity": h("6"),
        "original_instance_identity": h("7"),
        "result_status": status,
        "result_identity": h("8"),
        "small_ground_terminal": None,
        "larger_ground_recursive": {
            "canonical": True,
            "exact": True,
            "transition_identity": h("6"),
            "original_instance_identity": h("7"),
            "result_status": status,
            "result_identity": h("8"),
            "recursive_result_identity": h("8"),
            "recursive_accounting_binding_identity": h("9"),
            "accounting_result_identity": h("8"),
            "accounted_work": 11,
        },
    }


class ProductionCallerBindingTests(unittest.TestCase):
    def test_small_ground_nonempty(self) -> None:
        out = bind_production_caller(small())
        self.assertEqual(out["mode"], "small_ground_terminal")
        self.assertEqual(out["result_status"], "exact_nonempty")
        self.assertEqual(out["accounted_work"], 7)
        self.assertEqual(out["branch_certificate_identity"], h("4"))

    def test_small_ground_empty(self) -> None:
        out = bind_production_caller(small("exact_empty"))
        self.assertEqual(out["result_status"], "exact_empty")

    def test_recursive_nonempty(self) -> None:
        out = bind_production_caller(recursive())
        self.assertEqual(out["mode"], "larger_ground_recursive")
        self.assertEqual(out["result_status"], "exact_nonempty")
        self.assertEqual(out["accounted_work"], 11)
        self.assertEqual(out["branch_certificate_identity"], h("8"))

    def test_recursive_empty(self) -> None:
        out = bind_production_caller(recursive("exact_empty"))
        self.assertEqual(out["result_status"], "exact_empty")

    def test_replay_identity_is_deterministic_and_canonical(self) -> None:
        first = bind_production_caller(recursive())
        second = bind_production_caller(copy.deepcopy(recursive()))
        self.assertEqual(first, second)
        payload = dict(first)
        claimed = payload.pop("caller_binding_identity")
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
        self.assertEqual(claimed, hashlib.sha256(canonical).hexdigest())

    def test_rejects_both_or_neither_branch(self) -> None:
        both = small()
        both["larger_ground_recursive"] = recursive()["larger_ground_recursive"]
        with self.assertRaises(CallerBindingError):
            bind_production_caller(both)
        neither = small()
        neither["small_ground_terminal"] = None
        with self.assertRaises(CallerBindingError):
            bind_production_caller(neither)

    def test_rejects_mode_mismatch(self) -> None:
        value = small()
        value["mode"] = "larger_ground_recursive"
        with self.assertRaises(CallerBindingError):
            bind_production_caller(value)

    def test_rejects_transition_identity_drift(self) -> None:
        value = recursive()
        value["larger_ground_recursive"]["transition_identity"] = h("a")
        with self.assertRaises(CallerBindingError):
            bind_production_caller(value)

    def test_rejects_original_instance_identity_drift(self) -> None:
        value = small()
        value["small_ground_terminal"]["original_instance_identity"] = h("b")
        with self.assertRaises(CallerBindingError):
            bind_production_caller(value)

    def test_rejects_result_or_accounting_drift(self) -> None:
        value = recursive()
        value["larger_ground_recursive"]["recursive_result_identity"] = h("c")
        with self.assertRaises(CallerBindingError):
            bind_production_caller(value)
        value = recursive()
        value["larger_ground_recursive"]["accounting_result_identity"] = h("d")
        with self.assertRaises(CallerBindingError):
            bind_production_caller(value)

    def test_rejects_nonliteral_boolean_evidence_flags(self) -> None:
        for bad in (1, "true", None):
            value = small()
            value["canonical"] = bad
            with self.assertRaises(CallerBindingError):
                bind_production_caller(value)
            value = recursive()
            value["larger_ground_recursive"]["exact"] = bad
            with self.assertRaises(CallerBindingError):
                bind_production_caller(value)

    def test_rejects_noninteger_or_negative_accounting(self) -> None:
        for bad in (True, 1.0, -1, "1"):
            value = recursive()
            value["larger_ground_recursive"]["accounted_work"] = bad
            with self.assertRaises(CallerBindingError):
                bind_production_caller(value)

    def test_rejects_malformed_or_nonlowercase_sha(self) -> None:
        for bad in ("0" * 63, "G" * 64, "A" * 64, 123):
            value = small()
            value["transition_identity"] = bad
            with self.assertRaises(CallerBindingError):
                bind_production_caller(value)

    def test_rejects_unrecognized_result_status(self) -> None:
        value = recursive()
        value["result_status"] = "unresolved"
        value["larger_ground_recursive"]["result_status"] = "unresolved"
        with self.assertRaises(CallerBindingError):
            bind_production_caller(value)

    def test_rejects_nonstring_result_status_fail_closed(self) -> None:
        for bad in ([], {}, 1, True, None):
            value = recursive()
            value["result_status"] = bad
            with self.assertRaises(CallerBindingError):
                bind_production_caller(value)
            value = recursive()
            value["larger_ground_recursive"]["result_status"] = bad
            with self.assertRaises(CallerBindingError):
                bind_production_caller(value)

    def test_tampering_changes_binding_identity(self) -> None:
        one = bind_production_caller(recursive())
        value = recursive()
        value["larger_ground_recursive"]["accounted_work"] = 12
        two = bind_production_caller(value)
        self.assertNotEqual(
            one["caller_binding_identity"], two["caller_binding_identity"]
        )

    def test_rejects_unsupported_root_fields(self) -> None:
        value = small()
        value["result_identity_override"] = h("f")
        with self.assertRaises(CallerBindingError):
            bind_production_caller(value)

    def test_rejects_unsupported_selected_branch_fields(self) -> None:
        value = recursive()
        value["larger_ground_recursive"]["accounted_work_override"] = 0
        with self.assertRaises(CallerBindingError):
            bind_production_caller(value)

    def test_rejects_nonliteral_mapping_snapshots(self) -> None:
        with self.assertRaises(CallerBindingError):
            bind_production_caller(MappingProxyType(small()))

        value = recursive()
        value["larger_ground_recursive"] = MappingProxyType(
            dict(value["larger_ground_recursive"])
        )
        with self.assertRaises(CallerBindingError):
            bind_production_caller(value)


if __name__ == "__main__":
    unittest.main()
