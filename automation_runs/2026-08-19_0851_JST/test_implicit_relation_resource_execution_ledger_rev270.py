from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
import unittest

from implicit_relation_resource_execution_ledger_v1 import (
    EXPECTED_ENVELOPE_STATUS,
    ImplicitRelationResourceExecutionError,
    PHASES,
    abort_implicit_relation_phase,
    commit_implicit_relation_phase,
    finalize_implicit_relation_resource_execution,
    implicit_relation_resource_execution_plan,
    issue_implicit_relation_phase_start,
    snapshot_implicit_relation_resource_execution,
)
from phase_start_ticket_ledger_v1 import PhaseTicketError


BOUNDS = (10, 20, 30, 40, 50, 60)


def _envelope(**overrides):
    values = dict(
        status=EXPECTED_ENVELOPE_STATUS,
        original_root_degree=64,
        domain_degree=8,
        auxiliary_degree=16,
        generator_count=3,
        domain_order_upper_bound=48,
        image_order_upper_bound=24,
        image_order_gate=64,
        phase_work_upper_bounds=tuple(zip(PHASES, BOUNDS)),
        work_upper_bound=sum(BOUNDS),
        max_work=1000,
        root_lift_certified=True,
        order_bounds_compatible=True,
        image_gate_certified=True,
        admitted=True,
        complete=False,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


class ImplicitRelationResourceExecutionLedgerRev270Tests(unittest.TestCase):
    def test_admitted_rev265_shape_builds_complete_six_phase_plan(self):
        plan = implicit_relation_resource_execution_plan(
            _envelope(), ledger_id="rev270-good"
        )
        snapshot = snapshot_implicit_relation_resource_execution(plan)
        self.assertEqual(snapshot.phases, PHASES)
        self.assertEqual(snapshot.phase_work_upper_bounds, BOUNDS)
        self.assertEqual(snapshot.unexecuted_suffix, PHASES)
        self.assertEqual(snapshot.aggregate_work_upper_bound, sum(BOUNDS))
        self.assertTrue(plan.envelope_digest.startswith("sha256:"))

    def test_first_ticket_reserves_complete_suffix_before_execution(self):
        plan = implicit_relation_resource_execution_plan(
            _envelope(), ledger_id="rev270-first-ticket"
        )
        ticket = issue_implicit_relation_phase_start(plan, "induced_action")
        self.assertEqual(ticket.reserved_suffix, PHASES)
        self.assertEqual(ticket.reserved_suffix_work_upper_bound, sum(BOUNDS))
        self.assertEqual(ticket.phase_work_upper_bound, BOUNDS[0])

    def test_commit_advances_once_and_preserves_future_suffix(self):
        plan = implicit_relation_resource_execution_plan(
            _envelope(), ledger_id="rev270-commit"
        )
        ticket = issue_implicit_relation_phase_start(plan, PHASES[0])
        receipt = commit_implicit_relation_phase(plan, ticket, charged_work=7)
        self.assertEqual(receipt.unexecuted_suffix, PHASES[1:])
        self.assertEqual(
            receipt.unexecuted_suffix_work_upper_bound, sum(BOUNDS[1:])
        )
        snapshot = snapshot_implicit_relation_resource_execution(plan)
        self.assertEqual(snapshot.completed_phases, (PHASES[0],))
        self.assertEqual(snapshot.phase_charges, (7,))

    def test_all_six_phases_finalize_resource_certificate(self):
        plan = implicit_relation_resource_execution_plan(
            _envelope(), ledger_id="rev270-complete"
        )
        charges = []
        for phase, bound in zip(PHASES, BOUNDS):
            ticket = issue_implicit_relation_phase_start(plan, phase)
            charge = max(0, bound - 1)
            charges.append(charge)
            commit_implicit_relation_phase(plan, ticket, charged_work=charge)
        certificate = finalize_implicit_relation_resource_execution(plan)
        self.assertTrue(certificate.resource_complete)
        self.assertEqual(certificate.phase_charges, tuple(charges))
        self.assertEqual(certificate.charged_work, sum(charges))
        self.assertTrue(certificate.execution_digest.startswith("sha256:"))
        self.assertNotIn("exact", certificate.__dataclass_fields__)

    def test_out_of_order_phase_is_rejected_before_execution(self):
        plan = implicit_relation_resource_execution_plan(
            _envelope(), ledger_id="rev270-order"
        )
        with self.assertRaises(PhaseTicketError):
            issue_implicit_relation_phase_start(plan, PHASES[1])

    def test_consumed_ticket_cannot_be_replayed(self):
        plan = implicit_relation_resource_execution_plan(
            _envelope(), ledger_id="rev270-replay"
        )
        ticket = issue_implicit_relation_phase_start(plan, PHASES[0])
        commit_implicit_relation_phase(plan, ticket, charged_work=1)
        with self.assertRaises(PhaseTicketError):
            commit_implicit_relation_phase(plan, ticket, charged_work=1)

    def test_cross_instance_ticket_is_rejected(self):
        left = implicit_relation_resource_execution_plan(
            _envelope(), ledger_id="rev270-shared-logical-id"
        )
        right = implicit_relation_resource_execution_plan(
            _envelope(), ledger_id="rev270-shared-logical-id"
        )
        ticket = issue_implicit_relation_phase_start(left, PHASES[0])
        with self.assertRaises(PhaseTicketError):
            commit_implicit_relation_phase(right, ticket, charged_work=1)

    def test_phase_overcharge_is_rejected_without_advancing(self):
        plan = implicit_relation_resource_execution_plan(
            _envelope(), ledger_id="rev270-overcharge"
        )
        ticket = issue_implicit_relation_phase_start(plan, PHASES[0])
        with self.assertRaises(PhaseTicketError):
            commit_implicit_relation_phase(
                plan, ticket, charged_work=BOUNDS[0] + 1
            )
        snapshot = snapshot_implicit_relation_resource_execution(plan)
        self.assertEqual(snapshot.completed_phases, ())
        self.assertIsNotNone(snapshot.active_ticket)

    def test_abort_retires_capability_but_allows_new_generation(self):
        plan = implicit_relation_resource_execution_plan(
            _envelope(), ledger_id="rev270-abort"
        )
        old_ticket = issue_implicit_relation_phase_start(plan, PHASES[0])
        abort_implicit_relation_phase(plan, old_ticket)
        with self.assertRaises(PhaseTicketError):
            commit_implicit_relation_phase(plan, old_ticket, charged_work=1)
        new_ticket = issue_implicit_relation_phase_start(plan, PHASES[0])
        self.assertNotEqual(old_ticket.token, new_ticket.token)
        self.assertGreater(new_ticket.generation, old_ticket.generation)

    def test_rejected_or_wrong_status_envelope_cannot_start(self):
        with self.assertRaises(ImplicitRelationResourceExecutionError):
            implicit_relation_resource_execution_plan(
                _envelope(admitted=False), ledger_id="rev270-rejected"
            )
        with self.assertRaises(ImplicitRelationResourceExecutionError):
            implicit_relation_resource_execution_plan(
                _envelope(status="undetermined_work_cap"),
                ledger_id="rev270-wrong-status",
            )

    def test_reordered_phase_contract_is_rejected(self):
        pairs = list(zip(PHASES, BOUNDS))
        pairs[0], pairs[1] = pairs[1], pairs[0]
        with self.assertRaises(ImplicitRelationResourceExecutionError):
            implicit_relation_resource_execution_plan(
                _envelope(phase_work_upper_bounds=tuple(pairs)),
                ledger_id="rev270-reordered",
            )

    def test_aggregate_and_order_gate_drift_are_rejected(self):
        with self.assertRaises(ImplicitRelationResourceExecutionError):
            implicit_relation_resource_execution_plan(
                _envelope(work_upper_bound=sum(BOUNDS) + 1),
                ledger_id="rev270-aggregate",
            )
        with self.assertRaises(ImplicitRelationResourceExecutionError):
            implicit_relation_resource_execution_plan(
                _envelope(image_order_upper_bound=65),
                ledger_id="rev270-image-gate",
            )

    def test_post_admission_context_drift_is_rejected_before_ticket(self):
        plan = implicit_relation_resource_execution_plan(
            _envelope(), ledger_id="rev270-context"
        )
        corrupted = replace(plan, image_order_gate=plan.image_order_gate + 1)
        with self.assertRaises(ImplicitRelationResourceExecutionError):
            issue_implicit_relation_phase_start(corrupted, PHASES[0])

    def test_incomplete_execution_cannot_finalize(self):
        plan = implicit_relation_resource_execution_plan(
            _envelope(), ledger_id="rev270-incomplete"
        )
        with self.assertRaises(ImplicitRelationResourceExecutionError):
            finalize_implicit_relation_resource_execution(plan)


if __name__ == "__main__":
    unittest.main()
