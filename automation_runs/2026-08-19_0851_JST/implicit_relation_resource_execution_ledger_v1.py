from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
from operator import index as integer_index
from types import SimpleNamespace
from typing import Any

from phase_start_ticket_ledger_v1 import (
    PhaseAbortReceipt,
    PhaseCommitReceipt,
    PhaseStartTicket,
    PhaseStartTicketLedger,
    PhaseStartTicketLedgerSnapshot,
    PhaseTicketError,
    abort_phase_start_ticket,
    commit_phase_start_ticket,
    issue_phase_start_ticket,
    phase_start_ticket_ledger_from_envelope,
)


PHASES = (
    "induced_action",
    "domain_schreier",
    "image_schreier",
    "value_coset_intersection",
    "paired_preimage",
    "verification",
)
EXPECTED_ENVELOPE_STATUS = "certified_implicit_relation_image_work_bound"
SCHEMA_VERSION = 1


class ImplicitRelationResourceExecutionError(ValueError):
    """Raised when a rev265-style resource plan cannot be execution-linked safely."""


@dataclass(frozen=True, slots=True)
class ImplicitRelationResourceExecutionPlan:
    schema_version: int
    envelope_digest: str
    original_root_degree: int
    domain_degree: int
    auxiliary_degree: int
    generator_count: int
    domain_order_upper_bound: int
    image_order_upper_bound: int
    image_order_gate: int
    phase_work_upper_bounds: tuple[int, ...]
    work_upper_bound: int
    max_work: int
    ledger: PhaseStartTicketLedger


@dataclass(frozen=True, slots=True)
class ImplicitRelationResourceExecutionCertificate:
    schema_version: int
    envelope_digest: str
    execution_digest: str
    original_root_degree: int
    domain_degree: int
    auxiliary_degree: int
    phase_work_upper_bounds: tuple[int, ...]
    phase_charges: tuple[int, ...]
    charged_work: int
    work_upper_bound: int
    max_work: int
    resource_complete: bool
    reason: str


def _required(value: Any, name: str) -> Any:
    try:
        return getattr(value, name)
    except AttributeError as exc:
        raise ImplicitRelationResourceExecutionError(
            f"resource envelope is missing required attribute {name!r}"
        ) from exc


def _integer(name: str, value: Any, *, positive: bool = False) -> int:
    if isinstance(value, bool):
        raise ImplicitRelationResourceExecutionError(f"{name} must be an integer, not bool")
    try:
        result = integer_index(value)
    except TypeError as exc:
        raise ImplicitRelationResourceExecutionError(f"{name} must be an integer") from exc
    if result < 0 or (positive and result == 0):
        qualifier = "positive" if positive else "nonnegative"
        raise ImplicitRelationResourceExecutionError(f"{name} must be {qualifier}")
    return result


def _phase_bounds(envelope: Any) -> tuple[int, ...]:
    raw = tuple(_required(envelope, "phase_work_upper_bounds"))
    if len(raw) != len(PHASES):
        raise ImplicitRelationResourceExecutionError(
            "resource envelope does not expose the complete six-phase reservation"
        )
    names: list[str] = []
    bounds: list[int] = []
    for offset, item in enumerate(raw):
        if not isinstance(item, tuple) or len(item) != 2:
            raise ImplicitRelationResourceExecutionError(
                "phase_work_upper_bounds must contain (phase, bound) pairs"
            )
        phase, bound = item
        if not isinstance(phase, str):
            raise ImplicitRelationResourceExecutionError("phase name must be text")
        names.append(phase)
        bounds.append(_integer(f"phase_work_upper_bounds[{offset}]", bound))
    if tuple(names) != PHASES:
        raise ImplicitRelationResourceExecutionError(
            "resource envelope phase order differs from the canonical implicit-relation pipeline"
        )
    return tuple(bounds)


def _canonical_envelope_payload(
    *,
    original_root_degree: int,
    domain_degree: int,
    auxiliary_degree: int,
    generator_count: int,
    domain_order_upper_bound: int,
    image_order_upper_bound: int,
    image_order_gate: int,
    phase_work_upper_bounds: tuple[int, ...],
    work_upper_bound: int,
    max_work: int,
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": EXPECTED_ENVELOPE_STATUS,
        "original_root_degree": original_root_degree,
        "domain_degree": domain_degree,
        "auxiliary_degree": auxiliary_degree,
        "generator_count": generator_count,
        "domain_order_upper_bound": domain_order_upper_bound,
        "image_order_upper_bound": image_order_upper_bound,
        "image_order_gate": image_order_gate,
        "phases": PHASES,
        "phase_work_upper_bounds": phase_work_upper_bounds,
        "work_upper_bound": work_upper_bound,
        "max_work": max_work,
        "root_lift_certified": True,
        "order_bounds_compatible": True,
        "image_gate_certified": True,
        "admitted": True,
        "complete": False,
    }


def _digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def implicit_relation_resource_execution_plan(
    envelope: Any,
    *,
    ledger_id: str,
) -> ImplicitRelationResourceExecutionPlan:
    """Adapt one admitted rev265-style envelope to the reusable rev250 ticket ledger.

    The adapter is structural on purpose: rev265 remains independently owned and
    need not be imported here.  Only its exact public resource contract is
    consumed.  Every phase receives a rev250 single-use start capability, so a
    later production caller can reserve the complete suffix before execution,
    charge one phase exactly once, and fail closed on replay or overcharge.
    """
    if _required(envelope, "status") != EXPECTED_ENVELOPE_STATUS:
        raise ImplicitRelationResourceExecutionError(
            "only the certified implicit relation-image resource status can start execution"
        )
    for flag in (
        "root_lift_certified",
        "order_bounds_compatible",
        "image_gate_certified",
        "admitted",
    ):
        if _required(envelope, flag) is not True:
            raise ImplicitRelationResourceExecutionError(
                f"resource envelope flag {flag!r} is not certified"
            )
    if _required(envelope, "complete") is not False:
        raise ImplicitRelationResourceExecutionError(
            "the rev265 resource envelope must remain execution-incomplete at ticket creation"
        )

    root = _integer("original_root_degree", _required(envelope, "original_root_degree"), positive=True)
    degree = _integer("domain_degree", _required(envelope, "domain_degree"), positive=True)
    auxiliary = _integer("auxiliary_degree", _required(envelope, "auxiliary_degree"), positive=True)
    generators = _integer("generator_count", _required(envelope, "generator_count"), positive=True)
    domain_order = _integer("domain_order_upper_bound", _required(envelope, "domain_order_upper_bound"), positive=True)
    image_order = _integer("image_order_upper_bound", _required(envelope, "image_order_upper_bound"), positive=True)
    image_gate = _integer("image_order_gate", _required(envelope, "image_order_gate"), positive=True)
    bounds = _phase_bounds(envelope)
    aggregate = _integer("work_upper_bound", _required(envelope, "work_upper_bound"))
    cap = _integer("max_work", _required(envelope, "max_work"), positive=True)

    if degree > root or auxiliary > root * root:
        raise ImplicitRelationResourceExecutionError(
            "resource envelope degrees no longer satisfy the original-root lift"
        )
    if image_order > domain_order or image_order > image_gate:
        raise ImplicitRelationResourceExecutionError(
            "resource envelope order bounds no longer satisfy their certified gates"
        )
    if sum(bounds) != aggregate:
        raise ImplicitRelationResourceExecutionError(
            "aggregate work bound does not equal the complete admitted phase reservation"
        )
    if aggregate > cap:
        raise ImplicitRelationResourceExecutionError(
            "aggregate admitted work exceeds max_work"
        )

    payload = _canonical_envelope_payload(
        original_root_degree=root,
        domain_degree=degree,
        auxiliary_degree=auxiliary,
        generator_count=generators,
        domain_order_upper_bound=domain_order,
        image_order_upper_bound=image_order,
        image_order_gate=image_gate,
        phase_work_upper_bounds=bounds,
        work_upper_bound=aggregate,
        max_work=cap,
    )
    envelope_digest = _digest(payload)

    adapter = SimpleNamespace(
        admitted=True,
        completed_phases=(),
        unexecuted_suffix=PHASES,
        phase_work_upper_bounds=bounds,
        phase_charges=(),
        charged_work=0,
        complete=False,
        work_upper_bound=aggregate,
        max_work=cap,
    )
    try:
        ledger = phase_start_ticket_ledger_from_envelope(
            adapter,
            ledger_id=ledger_id,
            expected_phases=PHASES,
        )
    except PhaseTicketError as exc:
        raise ImplicitRelationResourceExecutionError(
            f"rev250 phase-ticket adapter rejected the resource plan: {exc}"
        ) from exc

    return ImplicitRelationResourceExecutionPlan(
        schema_version=SCHEMA_VERSION,
        envelope_digest=envelope_digest,
        original_root_degree=root,
        domain_degree=degree,
        auxiliary_degree=auxiliary,
        generator_count=generators,
        domain_order_upper_bound=domain_order,
        image_order_upper_bound=image_order,
        image_order_gate=image_gate,
        phase_work_upper_bounds=bounds,
        work_upper_bound=aggregate,
        max_work=cap,
        ledger=ledger,
    )


def _assert_plan_integrity(plan: ImplicitRelationResourceExecutionPlan) -> PhaseStartTicketLedgerSnapshot:
    if not isinstance(plan, ImplicitRelationResourceExecutionPlan):
        raise ImplicitRelationResourceExecutionError("execution plan has the wrong type")
    if plan.schema_version != SCHEMA_VERSION:
        raise ImplicitRelationResourceExecutionError("execution plan schema version is not recognized")
    payload = _canonical_envelope_payload(
        original_root_degree=plan.original_root_degree,
        domain_degree=plan.domain_degree,
        auxiliary_degree=plan.auxiliary_degree,
        generator_count=plan.generator_count,
        domain_order_upper_bound=plan.domain_order_upper_bound,
        image_order_upper_bound=plan.image_order_upper_bound,
        image_order_gate=plan.image_order_gate,
        phase_work_upper_bounds=plan.phase_work_upper_bounds,
        work_upper_bound=plan.work_upper_bound,
        max_work=plan.max_work,
    )
    if plan.envelope_digest != _digest(payload):
        raise ImplicitRelationResourceExecutionError(
            "execution plan context or reservation was changed after admission"
        )
    snapshot = plan.ledger.snapshot()
    if (
        snapshot.phases != PHASES
        or snapshot.phase_work_upper_bounds != plan.phase_work_upper_bounds
        or snapshot.aggregate_work_upper_bound != plan.work_upper_bound
        or snapshot.max_work != plan.max_work
    ):
        raise ImplicitRelationResourceExecutionError(
            "live rev250 ticket ledger no longer matches the admitted implicit-relation plan"
        )
    return snapshot


def issue_implicit_relation_phase_start(
    plan: ImplicitRelationResourceExecutionPlan,
    phase: str,
) -> PhaseStartTicket:
    """Issue the single-use rev250 capability for the next implicit-relation phase."""
    _assert_plan_integrity(plan)
    return issue_phase_start_ticket(plan.ledger, phase)


def commit_implicit_relation_phase(
    plan: ImplicitRelationResourceExecutionPlan,
    ticket: PhaseStartTicket,
    *,
    charged_work: int,
) -> PhaseCommitReceipt:
    """Consume one phase capability after execution and charge it exactly once."""
    _assert_plan_integrity(plan)
    return commit_phase_start_ticket(
        plan.ledger,
        ticket,
        charged_work=charged_work,
    )


def abort_implicit_relation_phase(
    plan: ImplicitRelationResourceExecutionPlan,
    ticket: PhaseStartTicket,
) -> PhaseAbortReceipt:
    """Retire an unconsumed phase capability without advancing the plan."""
    _assert_plan_integrity(plan)
    return abort_phase_start_ticket(plan.ledger, ticket)


def snapshot_implicit_relation_resource_execution(
    plan: ImplicitRelationResourceExecutionPlan,
) -> PhaseStartTicketLedgerSnapshot:
    """Return the current immutable rev250 ledger snapshot after context replay."""
    return _assert_plan_integrity(plan)


def finalize_implicit_relation_resource_execution(
    plan: ImplicitRelationResourceExecutionPlan,
) -> ImplicitRelationResourceExecutionCertificate:
    """Freeze a replay-stable resource certificate after all six phases complete.

    This certificate claims resource-accounting completeness only.  It deliberately
    carries no String-Isomorphism exactness bit and cannot promote an unresolved
    semantic result to an exact parent outcome.
    """
    snapshot = _assert_plan_integrity(plan)
    if snapshot.active_ticket is not None:
        raise ImplicitRelationResourceExecutionError(
            "cannot finalize while a phase-start capability is still active"
        )
    if not snapshot.complete or snapshot.unexecuted_suffix:
        raise ImplicitRelationResourceExecutionError(
            "cannot finalize before every canonical implicit-relation phase is charged"
        )
    execution_payload = {
        "schema_version": SCHEMA_VERSION,
        "envelope_digest": plan.envelope_digest,
        "phases": PHASES,
        "phase_work_upper_bounds": plan.phase_work_upper_bounds,
        "phase_charges": snapshot.phase_charges,
        "charged_work": snapshot.charged_work,
        "work_upper_bound": plan.work_upper_bound,
        "max_work": plan.max_work,
        "resource_complete": True,
    }
    return ImplicitRelationResourceExecutionCertificate(
        schema_version=SCHEMA_VERSION,
        envelope_digest=plan.envelope_digest,
        execution_digest=_digest(execution_payload),
        original_root_degree=plan.original_root_degree,
        domain_degree=plan.domain_degree,
        auxiliary_degree=plan.auxiliary_degree,
        phase_work_upper_bounds=plan.phase_work_upper_bounds,
        phase_charges=snapshot.phase_charges,
        charged_work=snapshot.charged_work,
        work_upper_bound=plan.work_upper_bound,
        max_work=plan.max_work,
        resource_complete=True,
        reason=(
            "all six admitted implicit-relation phases consumed one canonical rev250 "
            "start capability and preserved the complete unexecuted suffix reservation"
        ),
    )


__all__ = [
    "EXPECTED_ENVELOPE_STATUS",
    "ImplicitRelationResourceExecutionCertificate",
    "ImplicitRelationResourceExecutionError",
    "ImplicitRelationResourceExecutionPlan",
    "PHASES",
    "abort_implicit_relation_phase",
    "commit_implicit_relation_phase",
    "finalize_implicit_relation_resource_execution",
    "implicit_relation_resource_execution_plan",
    "issue_implicit_relation_phase_start",
    "snapshot_implicit_relation_resource_execution",
]
