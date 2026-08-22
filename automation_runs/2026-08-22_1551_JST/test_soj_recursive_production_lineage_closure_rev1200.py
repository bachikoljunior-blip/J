from __future__ import annotations

import copy
import hashlib
import json
import unittest
from dataclasses import replace

from soj_recursive_production_lineage_closure_v1 import (
    REV1100_STATUS,
    REV900_STATUS,
    certify_recursive_production_lineage_closure,
    replay_recursive_production_lineage_closure,
)


def _hash(payload: dict) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _p(ch: str) -> str:
    return "sha256:" + ch * 64


def _b(ch: str) -> str:
    return ch * 64


def _rev900(*, empty: bool = False) -> dict:
    payload = {
        "schema_version": 1,
        "status": REV900_STATUS,
        "main_commit_sha": "1" * 40,
        "caller_binding_identity": _b("2"),
        "envelope_identity": _b("3"),
        "main_provenance_identity": _b("4"),
        "recursive_provenance_identity": _p("5"),
        "production_provenance_identity": _p("6"),
        "result_status": "exact_empty" if empty else "exact_nonempty",
        "result_lift_digest": _p("7"),
        "accounting_binding_digest": _p("8"),
        "reduction_identity": _p("9"),
        "child_result_identity": _p("a"),
        "coherence_identity": _p("b"),
        "parent_action_degree": 120,
        "child_ground_size": 12,
        "construction_cost_binding_identity": _p("c"),
        "construction_multiplicative_cost_bound": 16.0,
        "charged_log2_reduction_cost": 4.0,
    }
    return payload | {
        "certified": True,
        "exact_contract_binding": True,
        "total_cost_binding_identity": _hash(payload),
        "reason": "fixture",
    }


def _rev1100(total: dict, *, empty: bool | None = None) -> dict:
    is_empty = total["result_status"] == "exact_empty" if empty is None else empty
    payload = {
        "schema_version": 1,
        "status": REV1100_STATUS,
        "main_commit_sha": total["main_commit_sha"],
        "main_provenance_identity": total["main_provenance_identity"],
        "caller_binding_identity": total["caller_binding_identity"],
        "caller_replay_envelope_identity": total["envelope_identity"],
        "outcome_kind": "exact_empty" if is_empty else "nonempty",
        "parent_action_degree": total["parent_action_degree"],
        "child_ground_size": total["child_ground_size"],
        "reduction_identity": total["reduction_identity"],
        "production_provenance_identity": total["production_provenance_identity"],
        "construction_cost_binding_identity": total[
            "construction_cost_binding_identity"
        ],
        "construction_multiplicative_cost_bound": total[
            "construction_multiplicative_cost_bound"
        ],
        "charged_log2_reduction_cost": total["charged_log2_reduction_cost"],
        "post_replay_envelope_identity": _p("d"),
    }
    return payload | {
        "certified": True,
        "exact": True,
        "complete": True,
        "seal_identity": _hash(payload),
        "reason": "fixture",
    }


def _rehash900(total: dict) -> None:
    payload = {
        key: total[key]
        for key in (
            "schema_version",
            "status",
            "main_commit_sha",
            "caller_binding_identity",
            "envelope_identity",
            "main_provenance_identity",
            "recursive_provenance_identity",
            "production_provenance_identity",
            "result_status",
            "result_lift_digest",
            "accounting_binding_digest",
            "reduction_identity",
            "child_result_identity",
            "coherence_identity",
            "parent_action_degree",
            "child_ground_size",
            "construction_cost_binding_identity",
            "construction_multiplicative_cost_bound",
            "charged_log2_reduction_cost",
        )
    }
    total["total_cost_binding_identity"] = _hash(payload)


def _rehash1100(seal: dict) -> None:
    payload = {
        key: seal[key]
        for key in (
            "schema_version",
            "status",
            "main_commit_sha",
            "main_provenance_identity",
            "caller_binding_identity",
            "caller_replay_envelope_identity",
            "outcome_kind",
            "parent_action_degree",
            "child_ground_size",
            "reduction_identity",
            "production_provenance_identity",
            "construction_cost_binding_identity",
            "construction_multiplicative_cost_bound",
            "charged_log2_reduction_cost",
            "post_replay_envelope_identity",
        )
    }
    seal["seal_identity"] = _hash(payload)


class Rev1200LineageClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.total = _rev900()
        self.seal = _rev1100(self.total)

    def assert_rejected(self, total: dict | None = None, seal: dict | None = None) -> None:
        result = certify_recursive_production_lineage_closure(
            self.total if total is None else total,
            self.seal if seal is None else seal,
        )
        self.assertFalse(result.certified, result)

    def test_accepts_nonempty_and_replays(self) -> None:
        result = certify_recursive_production_lineage_closure(self.total, self.seal)
        self.assertTrue(result.certified)
        self.assertEqual(result.outcome_kind, "nonempty")
        self.assertEqual(result.accounting_binding_digest, self.total["accounting_binding_digest"])
        self.assertEqual(result.child_result_identity, self.total["child_result_identity"])
        self.assertTrue(replay_recursive_production_lineage_closure(result, self.total, self.seal))

    def test_accepts_exact_empty_without_collapsing_outcome(self) -> None:
        total = _rev900(empty=True)
        seal = _rev1100(total)
        result = certify_recursive_production_lineage_closure(total, seal)
        self.assertTrue(result.certified)
        self.assertEqual(result.outcome_kind, "exact_empty")

    def test_rejects_rev900_identity_drift(self) -> None:
        total = copy.deepcopy(self.total)
        total["total_cost_binding_identity"] = _p("e")
        self.assert_rejected(total=total)

    def test_rejects_rev1100_identity_drift(self) -> None:
        seal = copy.deepcopy(self.seal)
        seal["seal_identity"] = _p("e")
        self.assert_rejected(seal=seal)

    def test_rejects_main_commit_mismatch_even_when_each_identity_rehashes(self) -> None:
        seal = copy.deepcopy(self.seal)
        seal["main_commit_sha"] = "f" * 40
        _rehash1100(seal)
        self.assert_rejected(seal=seal)

    def test_rejects_main_provenance_mismatch(self) -> None:
        seal = copy.deepcopy(self.seal)
        seal["main_provenance_identity"] = _b("e")
        _rehash1100(seal)
        self.assert_rejected(seal=seal)

    def test_rejects_caller_binding_mismatch(self) -> None:
        seal = copy.deepcopy(self.seal)
        seal["caller_binding_identity"] = _b("e")
        _rehash1100(seal)
        self.assert_rejected(seal=seal)

    def test_rejects_caller_envelope_mismatch(self) -> None:
        seal = copy.deepcopy(self.seal)
        seal["caller_replay_envelope_identity"] = _b("e")
        _rehash1100(seal)
        self.assert_rejected(seal=seal)

    def test_rejects_exact_empty_nonempty_mismatch(self) -> None:
        seal = copy.deepcopy(self.seal)
        seal["outcome_kind"] = "exact_empty"
        _rehash1100(seal)
        self.assert_rejected(seal=seal)

    def test_rejects_parent_measure_mismatch(self) -> None:
        seal = copy.deepcopy(self.seal)
        seal["parent_action_degree"] = 121
        _rehash1100(seal)
        self.assert_rejected(seal=seal)

    def test_rejects_child_measure_mismatch(self) -> None:
        seal = copy.deepcopy(self.seal)
        seal["child_ground_size"] = 13
        _rehash1100(seal)
        self.assert_rejected(seal=seal)

    def test_rejects_reduction_identity_mismatch(self) -> None:
        seal = copy.deepcopy(self.seal)
        seal["reduction_identity"] = _p("e")
        _rehash1100(seal)
        self.assert_rejected(seal=seal)

    def test_rejects_production_provenance_identity_mismatch(self) -> None:
        seal = copy.deepcopy(self.seal)
        seal["production_provenance_identity"] = _p("e")
        _rehash1100(seal)
        self.assert_rejected(seal=seal)

    def test_rejects_construction_identity_mismatch(self) -> None:
        seal = copy.deepcopy(self.seal)
        seal["construction_cost_binding_identity"] = _p("e")
        _rehash1100(seal)
        self.assert_rejected(seal=seal)

    def test_rejects_construction_bound_mismatch(self) -> None:
        seal = copy.deepcopy(self.seal)
        seal["construction_multiplicative_cost_bound"] = 8.0
        seal["charged_log2_reduction_cost"] = 3.0
        _rehash1100(seal)
        self.assert_rejected(seal=seal)

    def test_rejects_charge_mismatch(self) -> None:
        seal = copy.deepcopy(self.seal)
        seal["charged_log2_reduction_cost"] = 3.0
        _rehash1100(seal)
        self.assert_rejected(seal=seal)

    def test_rejects_non_power_of_two_even_with_rehashed_rev900(self) -> None:
        total = copy.deepcopy(self.total)
        total["construction_multiplicative_cost_bound"] = 12.0
        _rehash900(total)
        self.assert_rejected(total=total)

    def test_rejects_non_strict_shrink_even_with_rehashed_rev900(self) -> None:
        total = copy.deepcopy(self.total)
        total["child_ground_size"] = total["parent_action_degree"]
        _rehash900(total)
        self.assert_rejected(total=total)

    def test_rejects_boolean_coercion(self) -> None:
        total = copy.deepcopy(self.total)
        total["certified"] = 1
        self.assert_rejected(total=total)

    def test_rejects_malformed_digest(self) -> None:
        seal = copy.deepcopy(self.seal)
        seal["post_replay_envelope_identity"] = "d" * 64
        self.assert_rejected(seal=seal)

    def test_replay_rejects_closure_mutation(self) -> None:
        result = certify_recursive_production_lineage_closure(self.total, self.seal)
        self.assertTrue(result.certified)
        mutated = replace(result, reason="mutated")
        self.assertFalse(
            replay_recursive_production_lineage_closure(mutated, self.total, self.seal)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
