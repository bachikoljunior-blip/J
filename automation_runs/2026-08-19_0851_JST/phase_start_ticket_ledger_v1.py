from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
import json
from operator import index as integer_index
import secrets
from threading import RLock
from typing import Any, Iterable


class PhaseTicketError(ValueError):
    """Raised when a phase ticket or its ledger violates the reservation contract."""


@dataclass(frozen=True, slots=True)
class PhaseStartTicket:
    ledger_id: str
    ledger_instance_id: str
    plan_digest: str
    token: str
    generation: int
    phase: str
    phase_index: int
    phase_work_upper_bound: int
    charged_work_before: int
    aggregate_work_upper_bound: int
    max_work: int
    reserved_suffix: tuple[str, ...]
    reserved_suffix_work_upper_bound: int
    post_phase_suffix: tuple[str, ...]
    post_phase_suffix_work_upper_bound: int


@dataclass(frozen=True, slots=True)
class PhaseCommitReceipt:
    ledger_id: str
    ledger_instance_id: str
    ticket_token: str
    phase: str
    phase_index: int
    charged_work: int
    cumulative_charged_work: int
    unexecuted_suffix: tuple[str, ...]
    unexecuted_suffix_work_upper_bound: int
    aggregate_work_remaining: int
    max_work_remaining: int
    generation: int
    complete: bool


@dataclass(frozen=True, slots=True)
class PhaseAbortReceipt:
    ledger_id: str
    ledger_instance_id: str
    ticket_token: str
    phase: str
    phase_index: int
    generation: int


@dataclass(frozen=True, slots=True)
class PhaseStartTicketLedgerSnapshot:
    ledger_id: str
    ledger_instance_id: str
    plan_digest: str
    phases: tuple[str, ...]
    phase_work_upper_bounds: tuple[int, ...]
    aggregate_work_upper_bound: int
    max_work: int
    completed_phases: tuple[str, ...]
    phase_charges: tuple[int, ...]
    charged_work: int
    unexecuted_suffix: tuple[str, ...]
    unexecuted_suffix_work_upper_bound: int
    aggregate_work_remaining: int
    max_work_remaining: int
    generation: int
    active_ticket: PhaseStartTicket | None
    consumed_ticket_tokens: tuple[str, ...]
    aborted_ticket_tokens: tuple[str, ...]
    complete: bool


class PhaseStartTicketLedger:
    """A thread-safe, single-use capability ledger for canonical phase starts.

    The ledger is intentionally mutable: consuming or aborting a ticket changes
    the same ledger instance, so a second use of that capability is rejected.
    All public state is exposed through immutable tuples and snapshots.
    """

    __slots__ = (
        "_ledger_id",
        "_ledger_instance_id",
        "_plan_digest",
        "_secret",
        "_phases",
        "_bounds",
        "_aggregate_work_upper_bound",
        "_max_work",
        "_completed_phases",
        "_phase_charges",
        "_charged_work",
        "_generation",
        "_active_ticket",
        "_retired_tokens",
        "_consumed_tokens",
        "_aborted_tokens",
        "_lock",
    )

    def __init__(
        self,
        ledger_id: str,
        phases: Iterable[str],
        phase_work_upper_bounds: Iterable[int],
        *,
        aggregate_work_upper_bound: int,
        max_work: int,
        completed_phases: Iterable[str] = (),
        phase_charges: Iterable[int] = (),
    ) -> None:
        logical_id = _nonempty_text("ledger_id", ledger_id)
        canonical_phases = tuple(_nonempty_text("phase", value) for value in phases)
        if not canonical_phases:
            raise PhaseTicketError("a phase ticket ledger requires at least one phase")
        if len(set(canonical_phases)) != len(canonical_phases):
            raise PhaseTicketError("phase names must be unique")

        bounds = tuple(
            _nonnegative_integer("phase_work_upper_bound", value)
            for value in phase_work_upper_bounds
        )
        if len(bounds) != len(canonical_phases):
            raise PhaseTicketError("phase names and phase bounds must have equal length")

        aggregate = _nonnegative_integer(
            "aggregate_work_upper_bound", aggregate_work_upper_bound
        )
        cap = _nonnegative_integer("max_work", max_work)
        total_reserved = sum(bounds)
        if total_reserved > aggregate:
            raise PhaseTicketError(
                "aggregate work upper bound does not reserve every phase bound"
            )
        if aggregate > cap:
            raise PhaseTicketError("aggregate work upper bound exceeds max_work")

        completed = tuple(completed_phases)
        charges = tuple(
            _nonnegative_integer("phase_charge", value) for value in phase_charges
        )
        if len(completed) != len(charges):
            raise PhaseTicketError("completed phases and phase charges must align")
        if len(completed) > len(canonical_phases):
            raise PhaseTicketError("completed phase prefix is longer than the plan")
        if completed != canonical_phases[: len(completed)]:
            raise PhaseTicketError("completed phases must be a canonical plan prefix")
        for offset, charge in enumerate(charges):
            if charge > bounds[offset]:
                raise PhaseTicketError("a completed phase charge exceeds its reservation")

        charged = sum(charges)
        suffix_bound = sum(bounds[len(completed) :])
        if charged + suffix_bound > aggregate:
            raise PhaseTicketError(
                "completed charges no longer preserve the unexecuted aggregate suffix"
            )
        if charged + suffix_bound > cap:
            raise PhaseTicketError(
                "completed charges no longer preserve the unexecuted max_work suffix"
            )

        plan_payload = {
            "ledger_id": logical_id,
            "phases": canonical_phases,
            "phase_work_upper_bounds": bounds,
            "aggregate_work_upper_bound": aggregate,
            "max_work": cap,
        }
        encoded_plan = json.dumps(
            plan_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")

        self._ledger_id = logical_id
        self._ledger_instance_id = secrets.token_hex(16)
        self._plan_digest = sha256(encoded_plan).hexdigest()
        self._secret = secrets.token_bytes(32)
        self._phases = canonical_phases
        self._bounds = bounds
        self._aggregate_work_upper_bound = aggregate
        self._max_work = cap
        self._completed_phases = completed
        self._phase_charges = charges
        self._charged_work = charged
        self._generation = 0
        self._active_ticket: PhaseStartTicket | None = None
        self._retired_tokens: set[str] = set()
        self._consumed_tokens: list[str] = []
        self._aborted_tokens: list[str] = []
        self._lock = RLock()

    @property
    def ledger_id(self) -> str:
        return self._ledger_id

    @property
    def ledger_instance_id(self) -> str:
        return self._ledger_instance_id

    @property
    def phases(self) -> tuple[str, ...]:
        return self._phases

    @property
    def phase_work_upper_bounds(self) -> tuple[int, ...]:
        return self._bounds

    @property
    def aggregate_work_upper_bound(self) -> int:
        return self._aggregate_work_upper_bound

    @property
    def max_work(self) -> int:
        return self._max_work

    @property
    def completed_phases(self) -> tuple[str, ...]:
        with self._lock:
            return self._completed_phases

    @property
    def phase_charges(self) -> tuple[int, ...]:
        with self._lock:
            return self._phase_charges

    @property
    def charged_work(self) -> int:
        with self._lock:
            return self._charged_work

    @property
    def unexecuted_suffix(self) -> tuple[str, ...]:
        with self._lock:
            return self._phases[len(self._completed_phases) :]

    @property
    def complete(self) -> bool:
        with self._lock:
            return len(self._completed_phases) == len(self._phases)

    @property
    def active_ticket(self) -> PhaseStartTicket | None:
        with self._lock:
            return self._active_ticket

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation

    def snapshot(self) -> PhaseStartTicketLedgerSnapshot:
        with self._lock:
            index = len(self._completed_phases)
            suffix = self._phases[index:]
            suffix_bound = sum(self._bounds[index:])
            return PhaseStartTicketLedgerSnapshot(
                ledger_id=self._ledger_id,
                ledger_instance_id=self._ledger_instance_id,
                plan_digest=self._plan_digest,
                phases=self._phases,
                phase_work_upper_bounds=self._bounds,
                aggregate_work_upper_bound=self._aggregate_work_upper_bound,
                max_work=self._max_work,
                completed_phases=self._completed_phases,
                phase_charges=self._phase_charges,
                charged_work=self._charged_work,
                unexecuted_suffix=suffix,
                unexecuted_suffix_work_upper_bound=suffix_bound,
                aggregate_work_remaining=(
                    self._aggregate_work_upper_bound - self._charged_work
                ),
                max_work_remaining=self._max_work - self._charged_work,
                generation=self._generation,
                active_ticket=self._active_ticket,
                consumed_ticket_tokens=tuple(self._consumed_tokens),
                aborted_ticket_tokens=tuple(self._aborted_tokens),
                complete=not suffix,
            )


def phase_start_ticket_ledger(
    ledger_id: str,
    phases: Iterable[str],
    phase_work_upper_bounds: Iterable[int],
    *,
    aggregate_work_upper_bound: int,
    max_work: int,
    completed_phases: Iterable[str] = (),
    phase_charges: Iterable[int] = (),
) -> PhaseStartTicketLedger:
    """Build an admitted phase ledger while preserving every remaining bound."""
    return PhaseStartTicketLedger(
        ledger_id,
        phases,
        phase_work_upper_bounds,
        aggregate_work_upper_bound=aggregate_work_upper_bound,
        max_work=max_work,
        completed_phases=completed_phases,
        phase_charges=phase_charges,
    )


def phase_start_ticket_ledger_from_envelope(
    envelope: Any,
    *,
    ledger_id: str,
    expected_phases: Iterable[str] | None = None,
) -> PhaseStartTicketLedger:
    """Create a ticket ledger from an admitted envelope-shaped object.

    The adapter is deliberately structural, so the existing Design envelope can
    use it without this module importing or modifying the shared implementation.
    """
    if not bool(_required_attribute(envelope, "admitted")):
        raise PhaseTicketError("cannot ticket a rejected resource envelope")

    completed = tuple(_required_attribute(envelope, "completed_phases"))
    suffix = tuple(_required_attribute(envelope, "unexecuted_suffix"))
    envelope_phases = completed + suffix
    if expected_phases is None:
        phases = envelope_phases
    else:
        phases = tuple(expected_phases)
        if envelope_phases != phases:
            raise PhaseTicketError(
                "resource envelope phase prefix/suffix does not match expected phases"
            )

    bounds = tuple(_required_attribute(envelope, "phase_work_upper_bounds"))
    if len(phases) != len(bounds):
        raise PhaseTicketError("resource envelope phases and bounds do not align")

    charges = tuple(_required_attribute(envelope, "phase_charges"))
    recorded_charged = _nonnegative_integer(
        "charged_work", _required_attribute(envelope, "charged_work")
    )
    if recorded_charged != sum(_nonnegative_integer("phase_charge", x) for x in charges):
        raise PhaseTicketError("resource envelope charged_work disagrees with phase charges")
    if bool(_required_attribute(envelope, "complete")) != (not suffix):
        raise PhaseTicketError("resource envelope complete flag disagrees with its suffix")

    ledger = phase_start_ticket_ledger(
        ledger_id,
        phases,
        bounds,
        aggregate_work_upper_bound=_required_attribute(
            envelope, "work_upper_bound"
        ),
        max_work=_required_attribute(envelope, "max_work"),
        completed_phases=completed,
        phase_charges=charges,
    )
    if ledger.charged_work != recorded_charged:
        raise PhaseTicketError("ticket ledger failed to reproduce envelope charges")
    return ledger


def issue_phase_start_ticket(
    ledger: PhaseStartTicketLedger,
    phase: str,
) -> PhaseStartTicket:
    """Issue the only capability that may authorize the next canonical phase."""
    _require_ledger(ledger)
    requested_phase = _nonempty_text("phase", phase)
    with ledger._lock:
        if ledger._active_ticket is not None:
            raise PhaseTicketError("a phase-start ticket is already active")
        index = len(ledger._completed_phases)
        if index >= len(ledger._phases):
            raise PhaseTicketError("all ledger phases are already complete")
        expected_phase = ledger._phases[index]
        if requested_phase != expected_phase:
            raise PhaseTicketError(
                f"next phase is {expected_phase!r}, not {requested_phase!r}"
            )

        suffix = ledger._phases[index:]
        suffix_bound = sum(ledger._bounds[index:])
        post_suffix = ledger._phases[index + 1 :]
        post_suffix_bound = sum(ledger._bounds[index + 1 :])
        if ledger._charged_work + suffix_bound > ledger._aggregate_work_upper_bound:
            raise PhaseTicketError("aggregate reservation no longer covers the phase suffix")
        if ledger._charged_work + suffix_bound > ledger._max_work:
            raise PhaseTicketError("max_work no longer covers the phase suffix")

        token_payload = {
            "ledger_instance_id": ledger._ledger_instance_id,
            "plan_digest": ledger._plan_digest,
            "generation": ledger._generation,
            "phase": requested_phase,
            "phase_index": index,
            "charged_work_before": ledger._charged_work,
            "reserved_suffix_work_upper_bound": suffix_bound,
        }
        encoded = json.dumps(
            token_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        token = sha256(ledger._secret + encoded).hexdigest()
        ticket = PhaseStartTicket(
            ledger_id=ledger._ledger_id,
            ledger_instance_id=ledger._ledger_instance_id,
            plan_digest=ledger._plan_digest,
            token=token,
            generation=ledger._generation,
            phase=requested_phase,
            phase_index=index,
            phase_work_upper_bound=ledger._bounds[index],
            charged_work_before=ledger._charged_work,
            aggregate_work_upper_bound=ledger._aggregate_work_upper_bound,
            max_work=ledger._max_work,
            reserved_suffix=suffix,
            reserved_suffix_work_upper_bound=suffix_bound,
            post_phase_suffix=post_suffix,
            post_phase_suffix_work_upper_bound=post_suffix_bound,
        )
        ledger._active_ticket = ticket
        return ticket


def commit_phase_start_ticket(
    ledger: PhaseStartTicketLedger,
    ticket: PhaseStartTicket,
    *,
    charged_work: int,
) -> PhaseCommitReceipt:
    """Consume one active ticket and preserve the complete future suffix reserve."""
    _require_ledger(ledger)
    charge = _nonnegative_integer("charged_work", charged_work)
    with ledger._lock:
        _validate_current_ticket_locked(ledger, ticket)
        if charge > ticket.phase_work_upper_bound:
            raise PhaseTicketError("phase charge exceeds the ticket reservation")

        cumulative = ledger._charged_work + charge
        next_index = ticket.phase_index + 1
        suffix = ledger._phases[next_index:]
        suffix_bound = sum(ledger._bounds[next_index:])
        if cumulative + suffix_bound > ledger._aggregate_work_upper_bound:
            raise PhaseTicketError(
                "phase charge would consume the reserved aggregate suffix"
            )
        if cumulative + suffix_bound > ledger._max_work:
            raise PhaseTicketError("phase charge would consume the reserved max_work suffix")

        ledger._completed_phases = ledger._completed_phases + (ticket.phase,)
        ledger._phase_charges = ledger._phase_charges + (charge,)
        ledger._charged_work = cumulative
        ledger._active_ticket = None
        ledger._retired_tokens.add(ticket.token)
        ledger._consumed_tokens.append(ticket.token)
        ledger._generation += 1
        complete = next_index == len(ledger._phases)
        return PhaseCommitReceipt(
            ledger_id=ledger._ledger_id,
            ledger_instance_id=ledger._ledger_instance_id,
            ticket_token=ticket.token,
            phase=ticket.phase,
            phase_index=ticket.phase_index,
            charged_work=charge,
            cumulative_charged_work=cumulative,
            unexecuted_suffix=suffix,
            unexecuted_suffix_work_upper_bound=suffix_bound,
            aggregate_work_remaining=(
                ledger._aggregate_work_upper_bound - cumulative
            ),
            max_work_remaining=ledger._max_work - cumulative,
            generation=ledger._generation,
            complete=complete,
        )


def commit_phase_start_ticket_from_envelope(
    ledger: PhaseStartTicketLedger,
    ticket: PhaseStartTicket,
    envelope: Any,
) -> PhaseCommitReceipt:
    """Consume a ticket only after an immutable envelope records exactly one phase.

    All envelope checks happen before the ledger mutates.  This lets the existing
    ``record_design_original_root_pipeline_phase`` result serve as the durable
    evidence for the charge without importing that shared module here.
    """
    _require_ledger(ledger)
    with ledger._lock:
        _validate_current_ticket_locked(ledger, ticket)
        if not bool(_required_attribute(envelope, "admitted")):
            raise PhaseTicketError("resource envelope is not admitted")
        completed = tuple(_required_attribute(envelope, "completed_phases"))
        charges = tuple(_required_attribute(envelope, "phase_charges"))
        suffix = tuple(_required_attribute(envelope, "unexecuted_suffix"))
        expected_completed = ledger._completed_phases + (ticket.phase,)
        if completed != expected_completed:
            raise PhaseTicketError(
                "resource envelope did not record exactly the ticketed phase"
            )
        if len(charges) != len(ledger._phase_charges) + 1:
            raise PhaseTicketError("resource envelope did not append exactly one charge")
        if charges[:-1] != ledger._phase_charges:
            raise PhaseTicketError("resource envelope rewrote an earlier phase charge")
        if suffix != ticket.post_phase_suffix:
            raise PhaseTicketError("resource envelope suffix disagrees with the ticket")
        if tuple(_required_attribute(envelope, "phase_work_upper_bounds")) != ledger._bounds:
            raise PhaseTicketError("resource envelope phase bounds changed after ticketing")
        if _nonnegative_integer(
            "work_upper_bound", _required_attribute(envelope, "work_upper_bound")
        ) != ledger._aggregate_work_upper_bound:
            raise PhaseTicketError("resource envelope aggregate reservation changed")
        if _nonnegative_integer(
            "max_work", _required_attribute(envelope, "max_work")
        ) != ledger._max_work:
            raise PhaseTicketError("resource envelope max_work changed")
        recorded_total = _nonnegative_integer(
            "charged_work", _required_attribute(envelope, "charged_work")
        )
        normalized_charges = tuple(
            _nonnegative_integer("phase_charge", value) for value in charges
        )
        if recorded_total != sum(normalized_charges):
            raise PhaseTicketError("resource envelope charged_work is inconsistent")
        if bool(_required_attribute(envelope, "complete")) != (not suffix):
            raise PhaseTicketError("resource envelope complete flag is inconsistent")
        appended_charge = normalized_charges[-1]
        # RLock makes this nested call atomic with all precondition checks.
        return commit_phase_start_ticket(
            ledger,
            ticket,
            charged_work=appended_charge,
        )


def abort_phase_start_ticket(
    ledger: PhaseStartTicketLedger,
    ticket: PhaseStartTicket,
) -> PhaseAbortReceipt:
    """Retire an unconsumed ticket without advancing the canonical phase."""
    _require_ledger(ledger)
    with ledger._lock:
        _validate_current_ticket_locked(ledger, ticket)
        ledger._active_ticket = None
        ledger._retired_tokens.add(ticket.token)
        ledger._aborted_tokens.append(ticket.token)
        ledger._generation += 1
        return PhaseAbortReceipt(
            ledger_id=ledger._ledger_id,
            ledger_instance_id=ledger._ledger_instance_id,
            ticket_token=ticket.token,
            phase=ticket.phase,
            phase_index=ticket.phase_index,
            generation=ledger._generation,
        )


def assert_phase_ticket_ledger_matches_envelope(
    ledger: PhaseStartTicketLedger,
    envelope: Any,
    *,
    expected_phases: Iterable[str] | None = None,
) -> PhaseStartTicketLedgerSnapshot:
    """Fail closed unless the live ledger and an envelope have identical state."""
    _require_ledger(ledger)
    snapshot = ledger.snapshot()
    phases = (
        snapshot.phases if expected_phases is None else tuple(expected_phases)
    )
    completed = tuple(_required_attribute(envelope, "completed_phases"))
    suffix = tuple(_required_attribute(envelope, "unexecuted_suffix"))
    if completed + suffix != phases or phases != snapshot.phases:
        raise PhaseTicketError("resource envelope phase order differs from the ledger")
    comparisons = (
        (tuple(_required_attribute(envelope, "phase_work_upper_bounds")), snapshot.phase_work_upper_bounds, "phase bounds"),
        (tuple(_required_attribute(envelope, "phase_charges")), snapshot.phase_charges, "phase charges"),
        (completed, snapshot.completed_phases, "completed phases"),
        (suffix, snapshot.unexecuted_suffix, "unexecuted suffix"),
        (_nonnegative_integer("work_upper_bound", _required_attribute(envelope, "work_upper_bound")), snapshot.aggregate_work_upper_bound, "aggregate reservation"),
        (_nonnegative_integer("max_work", _required_attribute(envelope, "max_work")), snapshot.max_work, "max_work"),
        (_nonnegative_integer("charged_work", _required_attribute(envelope, "charged_work")), snapshot.charged_work, "charged_work"),
        (bool(_required_attribute(envelope, "complete")), snapshot.complete, "complete flag"),
    )
    if not bool(_required_attribute(envelope, "admitted")):
        raise PhaseTicketError("resource envelope is no longer admitted")
    for observed, expected, label in comparisons:
        if observed != expected:
            raise PhaseTicketError(f"resource envelope {label} differs from the ledger")
    return snapshot


def _validate_current_ticket_locked(
    ledger: PhaseStartTicketLedger,
    ticket: PhaseStartTicket,
) -> None:
    if not isinstance(ticket, PhaseStartTicket):
        raise PhaseTicketError("ticket has the wrong type")
    if ticket.ledger_id != ledger._ledger_id:
        raise PhaseTicketError("ticket belongs to a different logical ledger")
    if ticket.ledger_instance_id != ledger._ledger_instance_id:
        raise PhaseTicketError("ticket belongs to a different ledger instance")
    if ticket.plan_digest != ledger._plan_digest:
        raise PhaseTicketError("ticket plan digest does not match the ledger")
    if ticket.token in ledger._retired_tokens:
        raise PhaseTicketError("ticket has already been consumed or aborted")
    active = ledger._active_ticket
    if active is None:
        raise PhaseTicketError("there is no active phase-start ticket")
    if not compare_digest(active.token, ticket.token):
        raise PhaseTicketError("ticket is not the active phase-start capability")
    if ticket != active:
        raise PhaseTicketError(
            "ticket payload does not match the active phase-start capability"
        )
    if ticket.generation != ledger._generation:
        raise PhaseTicketError("ticket generation is stale")
    index = len(ledger._completed_phases)
    if ticket.phase_index != index or ticket.phase != ledger._phases[index]:
        raise PhaseTicketError("ticket no longer names the next canonical phase")
    if ticket.charged_work_before != ledger._charged_work:
        raise PhaseTicketError("ticket charge snapshot is stale")
    if ticket.reserved_suffix != ledger._phases[index:]:
        raise PhaseTicketError("ticket suffix snapshot is stale")
    if ticket.reserved_suffix_work_upper_bound != sum(ledger._bounds[index:]):
        raise PhaseTicketError("ticket suffix reservation is stale")


def _required_attribute(value: Any, name: str) -> Any:
    try:
        return getattr(value, name)
    except AttributeError as exc:
        raise PhaseTicketError(
            f"resource envelope is missing required attribute {name!r}"
        ) from exc


def _nonempty_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PhaseTicketError(f"{name} must be nonempty text")
    return value


def _nonnegative_integer(name: str, value: Any) -> int:
    if isinstance(value, bool):
        raise PhaseTicketError(f"{name} must be an integer, not bool")
    try:
        result = integer_index(value)
    except TypeError as exc:
        raise PhaseTicketError(f"{name} must be an integer") from exc
    if result < 0:
        raise PhaseTicketError(f"{name} must be nonnegative")
    return result


def _require_ledger(value: Any) -> None:
    if not isinstance(value, PhaseStartTicketLedger):
        raise PhaseTicketError("ledger has the wrong type")


__all__ = [
    "PhaseAbortReceipt",
    "PhaseCommitReceipt",
    "PhaseStartTicket",
    "PhaseStartTicketLedger",
    "PhaseStartTicketLedgerSnapshot",
    "PhaseTicketError",
    "abort_phase_start_ticket",
    "assert_phase_ticket_ledger_matches_envelope",
    "commit_phase_start_ticket",
    "commit_phase_start_ticket_from_envelope",
    "issue_phase_start_ticket",
    "phase_start_ticket_ledger",
    "phase_start_ticket_ledger_from_envelope",
]
