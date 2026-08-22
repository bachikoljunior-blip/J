from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from operator import index as integer_index
from typing import Any, Mapping, Sequence


PHASES = (
    "induced_action",
    "domain_schreier",
    "image_schreier",
    "value_coset_intersection",
    "paired_preimage",
    "verification",
)
SCHEMA_VERSION = 1
EXPECTED_ENVELOPE_STATUS = "certified_implicit_relation_image_work_bound"


class ResourceLedgerReplayError(ValueError):
    """Raised when serialized implicit-relation resource evidence cannot be replayed."""


@dataclass(frozen=True, slots=True)
class ResourceLedgerReplayVerification:
    schema_version: int
    envelope_digest: str
    replay_digest: str
    verified: bool
    resource_complete: bool
    semantic_exactness_certified: bool
    completed_phases: tuple[str, ...]
    unexecuted_suffix: tuple[str, ...]
    phase_charges: tuple[int, ...]
    charged_work: int
    unexecuted_suffix_work_upper_bound: int
    aggregate_work_upper_bound: int
    aggregate_work_remaining: int
    max_work: int
    max_work_remaining: int
    generation: int
    status: str
    reason: str


def _mapping(name: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ResourceLedgerReplayError(f"{name} must be a mapping")
    return value


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ResourceLedgerReplayError(f"{name} must be non-empty text")
    return value


def _integer(name: str, value: Any, *, positive: bool = False) -> int:
    if isinstance(value, bool):
        raise ResourceLedgerReplayError(f"{name} must be an integer, not bool")
    try:
        result = integer_index(value)
    except TypeError as exc:
        raise ResourceLedgerReplayError(f"{name} must be an integer") from exc
    if result < 0 or (positive and result == 0):
        qualifier = "positive" if positive else "nonnegative"
        raise ResourceLedgerReplayError(f"{name} must be {qualifier}")
    return result


def _sequence(name: str, value: Any) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ResourceLedgerReplayError(f"{name} must be a sequence")
    return tuple(value)


def _phase_names(name: str, value: Any) -> tuple[str, ...]:
    values = _sequence(name, value)
    if not all(isinstance(item, str) and item for item in values):
        raise ResourceLedgerReplayError(f"{name} must contain non-empty phase names")
    return tuple(values)


def _integers(name: str, value: Any) -> tuple[int, ...]:
    return tuple(_integer(f"{name}[{index}]", item) for index, item in enumerate(_sequence(name, value)))


def _digest(payload: Mapping[str, Any], *, prefix: bool = True) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    value = sha256(encoded).hexdigest()
    return f"sha256:{value}" if prefix else value


def _canonical_envelope_payload(context: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[int, ...]]:
    root = _integer("context.original_root_degree", context.get("original_root_degree"), positive=True)
    degree = _integer("context.domain_degree", context.get("domain_degree"), positive=True)
    auxiliary = _integer("context.auxiliary_degree", context.get("auxiliary_degree"), positive=True)
    generators = _integer("context.generator_count", context.get("generator_count"), positive=True)
    domain_order = _integer("context.domain_order_upper_bound", context.get("domain_order_upper_bound"), positive=True)
    image_order = _integer("context.image_order_upper_bound", context.get("image_order_upper_bound"), positive=True)
    image_gate = _integer("context.image_order_gate", context.get("image_order_gate"), positive=True)
    bounds = _integers("context.phase_work_upper_bounds", context.get("phase_work_upper_bounds"))
    if len(bounds) != len(PHASES):
        raise ResourceLedgerReplayError("context must expose exactly six phase work bounds")
    aggregate = _integer("context.work_upper_bound", context.get("work_upper_bound"))
    cap = _integer("context.max_work", context.get("max_work"), positive=True)
    if degree > root or auxiliary > root * root:
        raise ResourceLedgerReplayError("context violates the original-root degree lift")
    if image_order > domain_order or image_order > image_gate:
        raise ResourceLedgerReplayError("context violates certified image-order gates")
    if sum(bounds) != aggregate:
        raise ResourceLedgerReplayError("context aggregate does not equal the six phase bounds")
    if aggregate > cap:
        raise ResourceLedgerReplayError("context aggregate exceeds max_work")
    return (
        {
            "schema_version": SCHEMA_VERSION,
            "status": EXPECTED_ENVELOPE_STATUS,
            "original_root_degree": root,
            "domain_degree": degree,
            "auxiliary_degree": auxiliary,
            "generator_count": generators,
            "domain_order_upper_bound": domain_order,
            "image_order_upper_bound": image_order,
            "image_order_gate": image_gate,
            "phases": PHASES,
            "phase_work_upper_bounds": bounds,
            "work_upper_bound": aggregate,
            "max_work": cap,
            "root_lift_certified": True,
            "order_bounds_compatible": True,
            "image_gate_certified": True,
            "admitted": True,
            "complete": False,
        },
        bounds,
    )


def verify_implicit_relation_resource_ledger(payload: Mapping[str, Any]) -> ResourceLedgerReplayVerification:
    """Replay a serialized rev265/rev270-style six-phase resource ledger.

    The verifier is deliberately structural.  It does not import the concurrently
    owned rev265 or rev270 modules.  It independently reconstructs the admitted
    envelope identity and the rev250 public ledger invariants from serialized
    evidence.  Successful verification certifies resource accounting only;
    semantic String-Isomorphism exactness is always outside this contract.
    """
    outer = _mapping("payload", payload)
    if _integer("schema_version", outer.get("schema_version"), positive=True) != SCHEMA_VERSION:
        raise ResourceLedgerReplayError("unsupported verifier schema_version")

    context = _mapping("context", outer.get("context"))
    envelope_payload, bounds = _canonical_envelope_payload(context)
    expected_envelope_digest = _digest(envelope_payload)
    envelope_digest = _text("envelope_digest", outer.get("envelope_digest"))
    if envelope_digest != expected_envelope_digest:
        raise ResourceLedgerReplayError("envelope digest does not match the admitted resource context")

    ledger = _mapping("ledger", outer.get("ledger"))
    ledger_id = _text("ledger.ledger_id", ledger.get("ledger_id"))
    ledger_instance_id = _text("ledger.ledger_instance_id", ledger.get("ledger_instance_id"))
    phases = _phase_names("ledger.phases", ledger.get("phases"))
    if phases != PHASES:
        raise ResourceLedgerReplayError("ledger phases differ from the canonical six-phase pipeline")
    ledger_bounds = _integers("ledger.phase_work_upper_bounds", ledger.get("phase_work_upper_bounds"))
    if ledger_bounds != bounds:
        raise ResourceLedgerReplayError("ledger phase bounds differ from the admitted envelope")

    aggregate = _integer("ledger.aggregate_work_upper_bound", ledger.get("aggregate_work_upper_bound"))
    cap = _integer("ledger.max_work", ledger.get("max_work"), positive=True)
    if aggregate != envelope_payload["work_upper_bound"] or cap != envelope_payload["max_work"]:
        raise ResourceLedgerReplayError("ledger aggregate/cap differs from the admitted envelope")

    expected_plan_digest = _digest(
        {
            "ledger_id": ledger_id,
            "phases": phases,
            "phase_work_upper_bounds": ledger_bounds,
            "aggregate_work_upper_bound": aggregate,
            "max_work": cap,
        },
        prefix=False,
    )
    if _text("ledger.plan_digest", ledger.get("plan_digest")) != expected_plan_digest:
        raise ResourceLedgerReplayError("ledger plan_digest does not replay from its public plan")

    completed = _phase_names("ledger.completed_phases", ledger.get("completed_phases"))
    charges = _integers("ledger.phase_charges", ledger.get("phase_charges"))
    if len(completed) != len(charges):
        raise ResourceLedgerReplayError("completed phases and charges do not align")
    if len(completed) > len(PHASES) or completed != PHASES[: len(completed)]:
        raise ResourceLedgerReplayError("completed phases are not a canonical prefix")
    for index, charge in enumerate(charges):
        if charge > bounds[index]:
            raise ResourceLedgerReplayError("a phase charge exceeds its admitted reservation")

    charged = _integer("ledger.charged_work", ledger.get("charged_work"))
    if charged != sum(charges):
        raise ResourceLedgerReplayError("charged_work disagrees with phase_charges")

    suffix = _phase_names("ledger.unexecuted_suffix", ledger.get("unexecuted_suffix"))
    expected_suffix = PHASES[len(completed) :]
    if suffix != expected_suffix:
        raise ResourceLedgerReplayError("unexecuted suffix is not the exact canonical tail")
    suffix_bound = _integer(
        "ledger.unexecuted_suffix_work_upper_bound",
        ledger.get("unexecuted_suffix_work_upper_bound"),
    )
    expected_suffix_bound = sum(bounds[len(completed) :])
    if suffix_bound != expected_suffix_bound:
        raise ResourceLedgerReplayError("unexecuted suffix work bound is inconsistent")
    if charged + suffix_bound > aggregate or charged + suffix_bound > cap:
        raise ResourceLedgerReplayError("completed charges consumed the reserved future suffix")

    aggregate_remaining = _integer("ledger.aggregate_work_remaining", ledger.get("aggregate_work_remaining"))
    max_remaining = _integer("ledger.max_work_remaining", ledger.get("max_work_remaining"))
    if aggregate_remaining != aggregate - charged:
        raise ResourceLedgerReplayError("aggregate_work_remaining is inconsistent")
    if max_remaining != cap - charged:
        raise ResourceLedgerReplayError("max_work_remaining is inconsistent")

    generation = _integer("ledger.generation", ledger.get("generation"))
    if ledger.get("active_ticket") is not None:
        raise ResourceLedgerReplayError("a replay-stable snapshot cannot retain an active phase ticket")
    consumed_tokens = tuple(_text(f"ledger.consumed_ticket_tokens[{i}]", value) for i, value in enumerate(_sequence("ledger.consumed_ticket_tokens", ledger.get("consumed_ticket_tokens"))))
    aborted_tokens = tuple(_text(f"ledger.aborted_ticket_tokens[{i}]", value) for i, value in enumerate(_sequence("ledger.aborted_ticket_tokens", ledger.get("aborted_ticket_tokens"))))
    if len(set(consumed_tokens)) != len(consumed_tokens) or len(set(aborted_tokens)) != len(aborted_tokens):
        raise ResourceLedgerReplayError("ticket token histories contain duplicates")
    if set(consumed_tokens).intersection(aborted_tokens):
        raise ResourceLedgerReplayError("a ticket token cannot be both consumed and aborted")
    if len(consumed_tokens) != len(completed):
        raise ResourceLedgerReplayError("consumed ticket count differs from completed phase count")
    if generation != len(consumed_tokens) + len(aborted_tokens):
        raise ResourceLedgerReplayError("generation does not equal the number of retired tickets")

    complete = outer_complete = ledger.get("complete")
    if not isinstance(outer_complete, bool):
        raise ResourceLedgerReplayError("ledger.complete must be bool")
    expected_complete = not suffix
    if complete != expected_complete:
        raise ResourceLedgerReplayError("complete flag disagrees with the canonical suffix")

    replay_payload = {
        "schema_version": SCHEMA_VERSION,
        "envelope_digest": envelope_digest,
        "ledger": {
            "ledger_id": ledger_id,
            "ledger_instance_id": ledger_instance_id,
            "plan_digest": expected_plan_digest,
            "phases": phases,
            "phase_work_upper_bounds": ledger_bounds,
            "aggregate_work_upper_bound": aggregate,
            "max_work": cap,
            "completed_phases": completed,
            "phase_charges": charges,
            "charged_work": charged,
            "unexecuted_suffix": suffix,
            "unexecuted_suffix_work_upper_bound": suffix_bound,
            "aggregate_work_remaining": aggregate_remaining,
            "max_work_remaining": max_remaining,
            "generation": generation,
            "consumed_ticket_tokens": consumed_tokens,
            "aborted_ticket_tokens": aborted_tokens,
            "complete": complete,
        },
    }
    resource_complete = bool(expected_complete)
    status = "verified_complete_resource_ledger" if resource_complete else "verified_incomplete_resource_prefix"
    reason = (
        "all six canonical phases are replay-consistent and resource-accounting complete"
        if resource_complete
        else "the canonical executed prefix and complete future suffix reservation are replay-consistent"
    )
    return ResourceLedgerReplayVerification(
        schema_version=SCHEMA_VERSION,
        envelope_digest=envelope_digest,
        replay_digest=_digest(replay_payload),
        verified=True,
        resource_complete=resource_complete,
        semantic_exactness_certified=False,
        completed_phases=completed,
        unexecuted_suffix=suffix,
        phase_charges=charges,
        charged_work=charged,
        unexecuted_suffix_work_upper_bound=suffix_bound,
        aggregate_work_upper_bound=aggregate,
        aggregate_work_remaining=aggregate_remaining,
        max_work=cap,
        max_work_remaining=max_remaining,
        generation=generation,
        status=status,
        reason=reason,
    )


__all__ = [
    "EXPECTED_ENVELOPE_STATUS",
    "PHASES",
    "ResourceLedgerReplayError",
    "ResourceLedgerReplayVerification",
    "verify_implicit_relation_resource_ledger",
]
