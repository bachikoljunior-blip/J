from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace
import unittest

from phase_start_ticket_ledger_v1 import (
    PhaseTicketError,
    abort_phase_start_ticket,
    assert_phase_ticket_ledger_matches_envelope,
    commit_phase_start_ticket,
    commit_phase_start_ticket_from_envelope,
    issue_phase_start_ticket,
    phase_start_ticket_ledger,
    phase_start_ticket_ledger_from_envelope,
)


PHASES = ("twl", "materialization", "transport", "children", "union")
BOUNDS = (11, 13, 17, 19, 23)
TOTAL = sum(BOUNDS)


def new_ledger(*, logical_id: str = "design-root-7"):
    return phase_start_ticket_ledger(
        logical_id,
        PHASES,
        BOUNDS,
        aggregate_work_upper_bound=TOTAL,
        max_work=TOTAL + 31,
    )


def envelope_after(
    completed_phases=(),
    phase_charges=(),
    *,
    admitted=True,
    bounds=BOUNDS,
    total=TOTAL,
    cap=TOTAL + 31,
):
    completed = tuple(completed_phases)
    charges = tuple(phase_charges)
    return SimpleNamespace(
        admitted=admitted,
        phase_work_upper_bounds=tuple(bounds),
        work_upper_bound=total,
        max_work=cap,
        completed_phases=completed,
        phase_charges=charges,
        charged_work=sum(charges),
        unexecuted_suffix=PHASES[len(completed) :],
        complete=len(completed) == len(PHASES),
    )


class PhaseStartTicketLedgerTests(unittest.TestCase):
    def test_ticket_reserves_the_complete_unexecuted_suffix_before_start(self):
        ledger = new_ledger()
        ticket = issue_phase_start_ticket(ledger, "twl")

        self.assertEqual(ticket.reserved_suffix, PHASES)
        self.assertEqual(ticket.reserved_suffix_work_upper_bound, TOTAL)
        self.assertEqual(ticket.post_phase_suffix, PHASES[1:])
        self.assertEqual(ticket.post_phase_suffix_work_upper_bound, sum(BOUNDS[1:]))
        self.assertEqual(ticket.charged_work_before, 0)
        self.assertEqual(ledger.active_ticket, ticket)

    def test_wrong_order_and_second_active_ticket_fail_closed(self):
        ledger = new_ledger()
        with self.assertRaisesRegex(PhaseTicketError, "next phase"):
            issue_phase_start_ticket(ledger, "materialization")

        issue_phase_start_ticket(ledger, "twl")
        with self.assertRaisesRegex(PhaseTicketError, "already active"):
            issue_phase_start_ticket(ledger, "twl")

    def test_commit_preserves_future_suffix_and_replay_is_rejected(self):
        ledger = new_ledger()
        ticket = issue_phase_start_ticket(ledger, "twl")
        receipt = commit_phase_start_ticket(ledger, ticket, charged_work=7)

        self.assertEqual(receipt.unexecuted_suffix, PHASES[1:])
        self.assertEqual(
            receipt.unexecuted_suffix_work_upper_bound,
            sum(BOUNDS[1:]),
        )
        self.assertGreaterEqual(
            receipt.aggregate_work_remaining,
            receipt.unexecuted_suffix_work_upper_bound,
        )
        self.assertEqual(ledger.completed_phases, ("twl",))
        self.assertEqual(ledger.phase_charges, (7,))
        with self.assertRaisesRegex(PhaseTicketError, "already been consumed"):
            commit_phase_start_ticket(ledger, ticket, charged_work=7)

    def test_overcharge_does_not_consume_the_active_ticket(self):
        ledger = new_ledger()
        ticket = issue_phase_start_ticket(ledger, "twl")
        with self.assertRaisesRegex(PhaseTicketError, "exceeds"):
            commit_phase_start_ticket(
                ledger,
                ticket,
                charged_work=ticket.phase_work_upper_bound + 1,
            )
        self.assertEqual(ledger.active_ticket, ticket)
        receipt = commit_phase_start_ticket(
            ledger,
            ticket,
            charged_work=ticket.phase_work_upper_bound,
        )
        self.assertEqual(receipt.charged_work, BOUNDS[0])

    def test_forged_ticket_payload_cannot_reuse_the_active_token(self):
        ledger = phase_start_ticket_ledger(
            "slack-ledger",
            ("first", "later"),
            (3, 5),
            aggregate_work_upper_bound=100,
            max_work=100,
        )
        ticket = issue_phase_start_ticket(ledger, "first")
        forged = replace(ticket, phase_work_upper_bound=90)
        with self.assertRaisesRegex(PhaseTicketError, "payload does not match"):
            commit_phase_start_ticket(ledger, forged, charged_work=50)

        self.assertEqual(ledger.active_ticket, ticket)
        receipt = commit_phase_start_ticket(ledger, ticket, charged_work=3)
        self.assertEqual(receipt.charged_work, 3)

    def test_abort_invalidates_old_capability_and_reissue_is_fresh(self):
        ledger = new_ledger()
        old = issue_phase_start_ticket(ledger, "twl")
        abort = abort_phase_start_ticket(ledger, old)
        self.assertEqual(abort.generation, 1)
        with self.assertRaisesRegex(PhaseTicketError, "consumed or aborted"):
            commit_phase_start_ticket(ledger, old, charged_work=0)

        fresh = issue_phase_start_ticket(ledger, "twl")
        self.assertNotEqual(old.token, fresh.token)
        self.assertEqual(fresh.generation, 1)

    def test_cross_instance_ticket_is_rejected_even_for_same_logical_id(self):
        left = new_ledger(logical_id="same-logical-id")
        right = new_ledger(logical_id="same-logical-id")
        ticket = issue_phase_start_ticket(left, "twl")
        issue_phase_start_ticket(right, "twl")
        with self.assertRaisesRegex(PhaseTicketError, "different ledger instance"):
            commit_phase_start_ticket(right, ticket, charged_work=1)

    def test_envelope_adapter_resumes_an_existing_canonical_prefix(self):
        source = envelope_after(("twl", "materialization"), (5, 9))
        ledger = phase_start_ticket_ledger_from_envelope(
            source,
            ledger_id="resume-design",
            expected_phases=PHASES,
        )
        snapshot = ledger.snapshot()
        self.assertEqual(snapshot.completed_phases, PHASES[:2])
        self.assertEqual(snapshot.phase_charges, (5, 9))
        self.assertEqual(snapshot.unexecuted_suffix, PHASES[2:])
        self.assertGreaterEqual(
            snapshot.aggregate_work_remaining,
            snapshot.unexecuted_suffix_work_upper_bound,
        )

    def test_envelope_commit_is_checked_before_ledger_mutation(self):
        ledger = new_ledger()
        ticket = issue_phase_start_ticket(ledger, "twl")
        malformed = envelope_after(("materialization",), (3,))
        with self.assertRaisesRegex(PhaseTicketError, "ticketed phase"):
            commit_phase_start_ticket_from_envelope(ledger, ticket, malformed)
        self.assertEqual(ledger.completed_phases, ())
        self.assertEqual(ledger.active_ticket, ticket)

        recorded = envelope_after(("twl",), (3,))
        receipt = commit_phase_start_ticket_from_envelope(ledger, ticket, recorded)
        self.assertEqual(receipt.charged_work, 3)
        assert_phase_ticket_ledger_matches_envelope(
            ledger,
            recorded,
            expected_phases=PHASES,
        )

    def test_rejected_or_inconsistent_envelopes_fail_closed(self):
        with self.assertRaisesRegex(PhaseTicketError, "rejected"):
            phase_start_ticket_ledger_from_envelope(
                envelope_after(admitted=False),
                ledger_id="rejected",
                expected_phases=PHASES,
            )

        inconsistent = envelope_after(("twl",), (2,))
        inconsistent.charged_work = 1
        with self.assertRaisesRegex(PhaseTicketError, "disagrees"):
            phase_start_ticket_ledger_from_envelope(
                inconsistent,
                ledger_id="inconsistent",
                expected_phases=PHASES,
            )

    def test_concurrent_double_commit_has_exactly_one_winner(self):
        ledger = new_ledger()
        ticket = issue_phase_start_ticket(ledger, "twl")

        def attempt_commit():
            try:
                commit_phase_start_ticket(ledger, ticket, charged_work=4)
                return "committed"
            except PhaseTicketError:
                return "rejected"

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = sorted(executor.map(lambda _: attempt_commit(), range(2)))
        self.assertEqual(results, ["committed", "rejected"])
        self.assertEqual(ledger.phase_charges, (4,))
        self.assertEqual(len(ledger.snapshot().consumed_ticket_tokens), 1)

    def test_arbitrary_precision_bounds_and_zero_actual_charge(self):
        huge = 10**120
        ledger = phase_start_ticket_ledger(
            "huge-ledger",
            ("a", "b"),
            (huge, huge + 1),
            aggregate_work_upper_bound=2 * huge + 1,
            max_work=2 * huge + 9,
        )
        first = issue_phase_start_ticket(ledger, "a")
        receipt = commit_phase_start_ticket(ledger, first, charged_work=0)
        self.assertEqual(receipt.unexecuted_suffix_work_upper_bound, huge + 1)
        self.assertGreaterEqual(
            receipt.aggregate_work_remaining,
            receipt.unexecuted_suffix_work_upper_bound,
        )

    def test_completion_rejects_any_additional_phase_start(self):
        ledger = phase_start_ticket_ledger(
            "short",
            ("only",),
            (3,),
            aggregate_work_upper_bound=3,
            max_work=3,
        )
        ticket = issue_phase_start_ticket(ledger, "only")
        receipt = commit_phase_start_ticket(ledger, ticket, charged_work=2)
        self.assertTrue(receipt.complete)
        self.assertTrue(ledger.complete)
        with self.assertRaisesRegex(PhaseTicketError, "already complete"):
            issue_phase_start_ticket(ledger, "only")


if __name__ == "__main__":
    unittest.main()
