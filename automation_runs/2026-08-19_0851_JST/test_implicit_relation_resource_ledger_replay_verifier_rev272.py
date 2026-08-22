import copy
from hashlib import sha256
import json
import unittest

from implicit_relation_resource_ledger_replay_verifier_v1 import (
    PHASES,
    ResourceLedgerReplayError,
    verify_implicit_relation_resource_ledger,
)


def digest(payload, prefix=True):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    value = sha256(raw).hexdigest()
    return f"sha256:{value}" if prefix else value


def fixture(completed=2, aborted=0):
    bounds = (11, 13, 17, 19, 23, 29)
    context = {
        "original_root_degree": 10,
        "domain_degree": 6,
        "auxiliary_degree": 20,
        "generator_count": 3,
        "domain_order_upper_bound": 120,
        "image_order_upper_bound": 24,
        "image_order_gate": 100,
        "phase_work_upper_bounds": list(bounds),
        "work_upper_bound": sum(bounds),
        "max_work": 200,
    }
    envelope_payload = {
        "schema_version": 1,
        "status": "certified_implicit_relation_image_work_bound",
        "original_root_degree": 10,
        "domain_degree": 6,
        "auxiliary_degree": 20,
        "generator_count": 3,
        "domain_order_upper_bound": 120,
        "image_order_upper_bound": 24,
        "image_order_gate": 100,
        "phases": PHASES,
        "phase_work_upper_bounds": bounds,
        "work_upper_bound": sum(bounds),
        "max_work": 200,
        "root_lift_certified": True,
        "order_bounds_compatible": True,
        "image_gate_certified": True,
        "admitted": True,
        "complete": False,
    }
    charges = tuple(max(0, bounds[i] - 2) for i in range(completed))
    charged = sum(charges)
    ledger_id = "rev272-test-ledger"
    plan = {
        "ledger_id": ledger_id,
        "phases": PHASES,
        "phase_work_upper_bounds": bounds,
        "aggregate_work_upper_bound": sum(bounds),
        "max_work": 200,
    }
    suffix = PHASES[completed:]
    ledger = {
        "ledger_id": ledger_id,
        "ledger_instance_id": "instance-abc",
        "plan_digest": digest(plan, prefix=False),
        "phases": list(PHASES),
        "phase_work_upper_bounds": list(bounds),
        "aggregate_work_upper_bound": sum(bounds),
        "max_work": 200,
        "completed_phases": list(PHASES[:completed]),
        "phase_charges": list(charges),
        "charged_work": charged,
        "unexecuted_suffix": list(suffix),
        "unexecuted_suffix_work_upper_bound": sum(bounds[completed:]),
        "aggregate_work_remaining": sum(bounds) - charged,
        "max_work_remaining": 200 - charged,
        "generation": completed + aborted,
        "active_ticket": None,
        "consumed_ticket_tokens": [f"consumed-{i}" for i in range(completed)],
        "aborted_ticket_tokens": [f"aborted-{i}" for i in range(aborted)],
        "complete": not suffix,
    }
    return {
        "schema_version": 1,
        "envelope_digest": digest(envelope_payload),
        "context": context,
        "ledger": ledger,
    }


class ReplayVerifierTests(unittest.TestCase):
    def test_valid_incomplete_prefix_preserves_suffix(self):
        result = verify_implicit_relation_resource_ledger(fixture(2))
        self.assertTrue(result.verified)
        self.assertFalse(result.resource_complete)
        self.assertFalse(result.semantic_exactness_certified)
        self.assertEqual(result.completed_phases, PHASES[:2])
        self.assertEqual(result.unexecuted_suffix, PHASES[2:])

    def test_complete_six_phase_ledger(self):
        result = verify_implicit_relation_resource_ledger(fixture(6))
        self.assertTrue(result.resource_complete)
        self.assertEqual(result.status, "verified_complete_resource_ledger")
        self.assertEqual(result.unexecuted_suffix, ())

    def test_valid_abort_history_is_accounted_in_generation(self):
        result = verify_implicit_relation_resource_ledger(fixture(1, aborted=2))
        self.assertEqual(result.generation, 3)

    def test_envelope_digest_tamper_fails(self):
        data = fixture()
        data["context"]["generator_count"] = 4
        with self.assertRaisesRegex(ResourceLedgerReplayError, "envelope digest"):
            verify_implicit_relation_resource_ledger(data)

    def test_plan_digest_tamper_fails(self):
        data = fixture()
        data["ledger"]["plan_digest"] = "0" * 64
        with self.assertRaisesRegex(ResourceLedgerReplayError, "plan_digest"):
            verify_implicit_relation_resource_ledger(data)

    def test_out_of_order_completed_phase_fails(self):
        data = fixture(2)
        data["ledger"]["completed_phases"] = [PHASES[0], PHASES[2]]
        with self.assertRaisesRegex(ResourceLedgerReplayError, "canonical prefix"):
            verify_implicit_relation_resource_ledger(data)

    def test_duplicate_completed_phase_fails(self):
        data = fixture(2)
        data["ledger"]["completed_phases"] = [PHASES[0], PHASES[0]]
        with self.assertRaisesRegex(ResourceLedgerReplayError, "canonical prefix"):
            verify_implicit_relation_resource_ledger(data)

    def test_phase_overcharge_fails(self):
        data = fixture(1)
        data["ledger"]["phase_charges"] = [12]
        data["ledger"]["charged_work"] = 12
        data["ledger"]["aggregate_work_remaining"] = sum(data["context"]["phase_work_upper_bounds"]) - 12
        data["ledger"]["max_work_remaining"] = 188
        with self.assertRaisesRegex(ResourceLedgerReplayError, "exceeds"):
            verify_implicit_relation_resource_ledger(data)

    def test_charged_work_mismatch_fails(self):
        data = fixture(2)
        data["ledger"]["charged_work"] += 1
        with self.assertRaisesRegex(ResourceLedgerReplayError, "charged_work"):
            verify_implicit_relation_resource_ledger(data)

    def test_suffix_name_mismatch_fails(self):
        data = fixture(2)
        data["ledger"]["unexecuted_suffix"] = list(PHASES[3:])
        with self.assertRaisesRegex(ResourceLedgerReplayError, "canonical tail"):
            verify_implicit_relation_resource_ledger(data)

    def test_suffix_bound_mismatch_fails(self):
        data = fixture(2)
        data["ledger"]["unexecuted_suffix_work_upper_bound"] -= 1
        with self.assertRaisesRegex(ResourceLedgerReplayError, "suffix work bound"):
            verify_implicit_relation_resource_ledger(data)

    def test_remaining_account_mismatch_fails(self):
        data = fixture(2)
        data["ledger"]["aggregate_work_remaining"] -= 1
        with self.assertRaisesRegex(ResourceLedgerReplayError, "aggregate_work_remaining"):
            verify_implicit_relation_resource_ledger(data)

    def test_active_ticket_fails_closed(self):
        data = fixture(2)
        data["ledger"]["active_ticket"] = {"phase": PHASES[2]}
        with self.assertRaisesRegex(ResourceLedgerReplayError, "active phase ticket"):
            verify_implicit_relation_resource_ledger(data)

    def test_duplicate_ticket_token_fails(self):
        data = fixture(2)
        data["ledger"]["consumed_ticket_tokens"] = ["same", "same"]
        with self.assertRaisesRegex(ResourceLedgerReplayError, "duplicates"):
            verify_implicit_relation_resource_ledger(data)

    def test_consumed_and_aborted_token_overlap_fails(self):
        data = fixture(1, aborted=1)
        data["ledger"]["aborted_ticket_tokens"] = [data["ledger"]["consumed_ticket_tokens"][0]]
        with self.assertRaisesRegex(ResourceLedgerReplayError, "both consumed and aborted"):
            verify_implicit_relation_resource_ledger(data)

    def test_generation_mismatch_fails(self):
        data = fixture(2)
        data["ledger"]["generation"] = 99
        with self.assertRaisesRegex(ResourceLedgerReplayError, "generation"):
            verify_implicit_relation_resource_ledger(data)

    def test_bool_is_not_accepted_as_integer(self):
        data = fixture(0)
        data["context"]["generator_count"] = True
        with self.assertRaisesRegex(ResourceLedgerReplayError, "not bool"):
            verify_implicit_relation_resource_ledger(data)

    def test_incomplete_claim_cannot_set_complete_true(self):
        data = fixture(3)
        data["ledger"]["complete"] = True
        with self.assertRaisesRegex(ResourceLedgerReplayError, "complete flag"):
            verify_implicit_relation_resource_ledger(data)

    def test_context_phase_total_must_match_aggregate(self):
        data = fixture(0)
        data["context"]["work_upper_bound"] += 1
        with self.assertRaisesRegex(ResourceLedgerReplayError, "aggregate"):
            verify_implicit_relation_resource_ledger(data)


if __name__ == "__main__":
    unittest.main()
