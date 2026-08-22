from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from collections.abc import Mapping
from typing import Any


EXPECTED_EVIDENCE_SCHEMA = "rev288_corrected_soj_strict_evidence_v1"
EXPECTED_ACCOUNTING_OPERATION = "corrected_soj_johnson_terminal_composition"
EXPECTED_TRANSITION_STATUS = "certified_corrected_soj_explicit_johnson_embedding"
EXPECTED_TRANSITION_KIND = "johnson_embedding"
EXPECTED_TERMINAL_OPERATION = "primitive_johnson_ground_terminal"
EXACT_TERMINAL_STATUSES = frozenset(
    {
        "exact_empty_primitive_johnson_ground",
        "exact_primitive_johnson_ground_coset",
    }
)

TRANSITION_FIELDS = (
    "status",
    "transition_kind",
    "theorem_input_gate",
    "canonical",
    "exact",
    "progress_certified",
    "multiplicative_cost",
    "max_multiplicative_cost",
    "johnson_ground_size",
    "johnson_subset_size",
    "johnson_vertex_count",
    "reason",
)

TERMINAL_FIELDS = (
    "status",
    "operation_kind",
    "root_n",
    "domain_size",
    "canonical",
    "exact",
    "local_cost_certified",
    "local_log2_cost_bound",
    "terminal_certified",
    "johnson_ground_size",
    "johnson_subset_size",
    "ground_permutations_checked",
    "recognition_search_nodes",
    "proof_identity",
)


class CorrectedSOJNormalizedJohnsonCostBindingError(ValueError):
    """Raised when normalized Johnson evidence and terminal accounting do not bind exactly."""


@dataclass(frozen=True)
class CorrectedSOJNormalizedJohnsonCostBinding:
    schema: str
    certified: bool
    root_n: int
    current_domain_size: int
    normalized_evidence_identity: str
    terminal_cost_identity: str
    transition_snapshot_identity: str
    terminal_status: str
    transition_log2_charge: float
    terminal_log2_charge: float
    combined_log2_charge: float
    upstream_terminal_identity_present: bool
    binding_identity: str
    reason: str


def _field(value: Any, name: str, *, owner: str) -> Any:
    if isinstance(value, Mapping):
        if name not in value:
            raise CorrectedSOJNormalizedJohnsonCostBindingError(
                f"{owner} is missing required field {name!r}"
            )
        return value[name]
    if not hasattr(value, name):
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            f"{owner} is missing required field {name!r}"
        )
    return getattr(value, name)


def _strict_bool(name: str, value: Any) -> bool:
    if type(value) is not bool:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            f"{name} must be an exact bool"
        )
    return value


def _strict_int(name: str, value: Any, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            f"{name} must be an exact integer"
        )
    if minimum is not None and value < minimum:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            f"{name} must be at least {minimum}"
        )
    return value


def _strict_real(name: str, value: Any, *, minimum: float | None = None) -> float:
    if type(value) not in (int, float):
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            f"{name} must be an exact JSON-style number"
        )
    result = float(value)
    if not math.isfinite(result):
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            f"{name} must be finite"
        )
    if minimum is not None and result < minimum:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            f"{name} must be at least {minimum}"
        )
    return result


def _strict_text(name: str, value: Any) -> str:
    if type(value) is not str or not value:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            f"{name} must be a non-empty exact string"
        )
    return value


def _optional_text(name: str, value: Any) -> str | None:
    if value is None:
        return None
    return _strict_text(name, value)


def _hex_identity(name: str, value: Any) -> str:
    text = _strict_text(name, value)
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            f"{name} must be a lowercase SHA-256 hex identity"
        )
    return text


def _assert_exact_field_equality(
    left: Any,
    right: Any,
    fields: tuple[str, ...],
    *,
    left_owner: str,
    right_owner: str,
) -> None:
    for name in fields:
        left_value = _field(left, name, owner=left_owner)
        right_value = _field(right, name, owner=right_owner)
        if type(left_value) is not type(right_value) or left_value != right_value:
            raise CorrectedSOJNormalizedJohnsonCostBindingError(
                f"{left_owner}.{name} differs from {right_owner}.{name}"
            )


def _validate_normalized_bundle(bundle: Any) -> tuple[int, int, str, Any, Any, bool]:
    schema = _strict_text("normalized.schema", _field(bundle, "schema", owner="normalized"))
    if schema != EXPECTED_EVIDENCE_SCHEMA:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "normalized evidence schema is not rev288 strict evidence"
        )
    root_n = _strict_int(
        "normalized.root_n", _field(bundle, "root_n", owner="normalized"), minimum=1
    )
    current_domain_size = _strict_int(
        "normalized.current_domain_size",
        _field(bundle, "current_domain_size", owner="normalized"),
        minimum=1,
    )
    if current_domain_size > root_n:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "normalized current domain exceeds root envelope"
        )
    evidence_identity = _hex_identity(
        "normalized.evidence_identity",
        _field(bundle, "evidence_identity", owner="normalized"),
    )
    transition = _field(bundle, "transition", owner="normalized")
    terminal = _field(bundle, "terminal", owner="normalized")
    full_vertex_count = _strict_int(
        "normalized.full_johnson_vertex_count",
        _field(bundle, "full_johnson_vertex_count", owner="normalized"),
        minimum=1,
    )
    transition_vertex_count = _strict_int(
        "normalized.transition.johnson_vertex_count",
        _field(transition, "johnson_vertex_count", owner="normalized.transition"),
        minimum=1,
    )
    terminal_domain_size = _strict_int(
        "normalized.terminal.domain_size",
        _field(terminal, "domain_size", owner="normalized.terminal"),
        minimum=1,
    )
    if full_vertex_count != transition_vertex_count or full_vertex_count != terminal_domain_size:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "normalized Johnson domain cardinalities are inconsistent"
        )
    if current_domain_size <= full_vertex_count:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "normalized Johnson evidence is not a strict domain reduction"
        )
    terminal_root_n = _strict_int(
        "normalized.terminal.root_n",
        _field(terminal, "root_n", owner="normalized.terminal"),
        minimum=1,
    )
    if terminal_root_n != root_n:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "normalized terminal root differs from root envelope"
        )
    transition_status = _strict_text(
        "normalized.transition.status",
        _field(transition, "status", owner="normalized.transition"),
    )
    transition_kind = _strict_text(
        "normalized.transition.transition_kind",
        _field(transition, "transition_kind", owner="normalized.transition"),
    )
    if transition_status != EXPECTED_TRANSITION_STATUS or transition_kind != EXPECTED_TRANSITION_KIND:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "normalized transition is not the exact corrected-SOJ Johnson embedding"
        )
    for flag in ("theorem_input_gate", "canonical", "exact", "progress_certified"):
        if not _strict_bool(
            f"normalized.transition.{flag}",
            _field(transition, flag, owner="normalized.transition"),
        ):
            raise CorrectedSOJNormalizedJohnsonCostBindingError(
                f"normalized.transition.{flag} must be true"
            )
    terminal_status = _strict_text(
        "normalized.terminal.status",
        _field(terminal, "status", owner="normalized.terminal"),
    )
    if terminal_status not in EXACT_TERMINAL_STATUSES:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "normalized terminal status is not exact"
        )
    if _strict_text(
        "normalized.terminal.operation_kind",
        _field(terminal, "operation_kind", owner="normalized.terminal"),
    ) != EXPECTED_TERMINAL_OPERATION:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "normalized terminal operation kind is not primitive Johnson"
        )
    for flag in ("canonical", "exact", "local_cost_certified", "terminal_certified"):
        if not _strict_bool(
            f"normalized.terminal.{flag}",
            _field(terminal, flag, owner="normalized.terminal"),
        ):
            raise CorrectedSOJNormalizedJohnsonCostBindingError(
                f"normalized.terminal.{flag} must be true"
            )
    proof_identity = _optional_text(
        "normalized.terminal.proof_identity",
        _field(terminal, "proof_identity", owner="normalized.terminal"),
    )
    replay_stable = _strict_bool(
        "normalized.replay_stable_upstream_identity",
        _field(bundle, "replay_stable_upstream_identity", owner="normalized"),
    )
    if replay_stable != (proof_identity is not None):
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "normalized replay-stability flag disagrees with terminal proof identity presence"
        )
    return root_n, current_domain_size, evidence_identity, transition, terminal, replay_stable


def _validate_cost_certificate(
    certificate: Any,
    *,
    root_n: int,
    current_domain_size: int,
    normalized_transition: Any,
    normalized_terminal: Any,
) -> tuple[str, str, float, float, float]:
    if not _strict_bool(
        "cost.certified", _field(certificate, "certified", owner="cost")
    ):
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "Johnson terminal-cost certificate is not certified"
        )
    cost_current_domain = _strict_int(
        "cost.current_domain_size",
        _field(certificate, "current_domain_size", owner="cost"),
        minimum=1,
    )
    if cost_current_domain != current_domain_size:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "terminal-cost current domain differs from normalized evidence"
        )

    cost_transition = _field(certificate, "transition", owner="cost")
    cost_terminal = _field(certificate, "terminal", owner="cost")
    _assert_exact_field_equality(
        normalized_transition,
        cost_transition,
        TRANSITION_FIELDS,
        left_owner="normalized.transition",
        right_owner="cost.transition",
    )
    _assert_exact_field_equality(
        normalized_terminal,
        cost_terminal,
        TERMINAL_FIELDS,
        left_owner="normalized.terminal",
        right_owner="cost.terminal",
    )

    transition_snapshot_identity = _hex_identity(
        "cost.transition.snapshot_identity",
        _field(cost_transition, "snapshot_identity", owner="cost.transition"),
    )
    cost_identity = _hex_identity(
        "cost.proof_identity", _field(certificate, "proof_identity", owner="cost")
    )

    transition_charge = _strict_real(
        "cost.transition_log2_charge",
        _field(certificate, "transition_log2_charge", owner="cost"),
        minimum=0.0,
    )
    terminal_charge = _strict_real(
        "cost.terminal_log2_charge",
        _field(certificate, "terminal_log2_charge", owner="cost"),
        minimum=0.0,
    )
    combined_charge = transition_charge + terminal_charge
    if not math.isfinite(combined_charge):
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "combined Johnson charge is not finite"
        )

    accounting = _field(certificate, "accounting_root", owner="cost")
    if _strict_int(
        "cost.accounting_root.n",
        _field(accounting, "n", owner="cost.accounting_root"),
        minimum=1,
    ) != root_n:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "terminal-cost accounting root_n differs from normalized evidence"
        )
    if _strict_int(
        "cost.accounting_root.m",
        _field(accounting, "m", owner="cost.accounting_root"),
        minimum=1,
    ) != current_domain_size:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "terminal-cost accounting measure differs from normalized current domain"
        )
    if _strict_text(
        "cost.accounting_root.operation_kind",
        _field(accounting, "operation_kind", owner="cost.accounting_root"),
    ) != EXPECTED_ACCOUNTING_OPERATION:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "terminal-cost accounting operation kind is not the Johnson composition"
        )
    for flag in ("canonical", "cost_certified", "terminal_certified"):
        if not _strict_bool(
            f"cost.accounting_root.{flag}",
            _field(accounting, flag, owner="cost.accounting_root"),
        ):
            raise CorrectedSOJNormalizedJohnsonCostBindingError(
                f"cost.accounting_root.{flag} must be true"
            )
    children = _field(accounting, "children", owner="cost.accounting_root")
    if not isinstance(children, (tuple, list)) or len(children) != 0:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "terminal-cost accounting root must be a terminal leaf"
        )
    accounting_charge = _strict_real(
        "cost.accounting_root.local_log2_cost_bound",
        _field(accounting, "local_log2_cost_bound", owner="cost.accounting_root"),
        minimum=0.0,
    )
    if not math.isclose(
        accounting_charge,
        combined_charge,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "terminal-cost accounting charge differs from transition plus terminal charges"
        )

    validation = _field(certificate, "validation", owner="cost")
    if not _strict_bool(
        "cost.validation.certified",
        _field(validation, "certified", owner="cost.validation"),
    ):
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "terminal-cost recurrence validation is not certified"
        )

    return (
        cost_identity,
        transition_snapshot_identity,
        transition_charge,
        terminal_charge,
        accounting_charge,
    )


def _binding_identity(payload: dict[str, Any]) -> str:
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "binding payload is not canonically serializable"
        ) from exc
    return sha256(encoded).hexdigest()


def bind_normalized_johnson_terminal_cost(
    normalized_bundle: Any,
    terminal_cost_certificate: Any,
    *,
    normalized_replay_verified: bool,
    terminal_cost_replay_verified: bool,
) -> CorrectedSOJNormalizedJohnsonCostBinding:
    """Bind two already-replayed sibling certificates without importing their implementations.

    rev290 is intentionally post-replay. The caller must replay rev288 and rev286
    with their owning implementations and pass exact booleans proving those checks
    succeeded. This closes the cross-certificate TOCTOU gap by requiring exact
    structural equality and the same root/accounting envelope.
    """

    if not _strict_bool("normalized_replay_verified", normalized_replay_verified):
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "normalized evidence replay must be mechanically verified"
        )
    if not _strict_bool("terminal_cost_replay_verified", terminal_cost_replay_verified):
        raise CorrectedSOJNormalizedJohnsonCostBindingError(
            "terminal-cost replay must be mechanically verified"
        )

    (
        root_n,
        current_domain_size,
        normalized_identity,
        normalized_transition,
        normalized_terminal,
        upstream_identity_present,
    ) = _validate_normalized_bundle(normalized_bundle)

    (
        cost_identity,
        transition_snapshot_identity,
        transition_charge,
        terminal_charge,
        accounting_charge,
    ) = _validate_cost_certificate(
        terminal_cost_certificate,
        root_n=root_n,
        current_domain_size=current_domain_size,
        normalized_transition=normalized_transition,
        normalized_terminal=normalized_terminal,
    )

    terminal_status = _strict_text(
        "normalized.terminal.status",
        _field(normalized_terminal, "status", owner="normalized.terminal"),
    )
    payload = {
        "schema": "rev290_corrected_soj_normalized_johnson_cost_binding_v1",
        "root_n": root_n,
        "current_domain_size": current_domain_size,
        "normalized_evidence_identity": normalized_identity,
        "terminal_cost_identity": cost_identity,
        "transition_snapshot_identity": transition_snapshot_identity,
        "terminal_status": terminal_status,
        "transition_log2_charge": transition_charge,
        "terminal_log2_charge": terminal_charge,
        "combined_log2_charge": accounting_charge,
        "upstream_terminal_identity_present": upstream_identity_present,
    }
    identity = _binding_identity(payload)
    return CorrectedSOJNormalizedJohnsonCostBinding(
        schema=payload["schema"],
        certified=True,
        root_n=root_n,
        current_domain_size=current_domain_size,
        normalized_evidence_identity=normalized_identity,
        terminal_cost_identity=cost_identity,
        transition_snapshot_identity=transition_snapshot_identity,
        terminal_status=terminal_status,
        transition_log2_charge=transition_charge,
        terminal_log2_charge=terminal_charge,
        combined_log2_charge=accounting_charge,
        upstream_terminal_identity_present=upstream_identity_present,
        binding_identity=identity,
        reason=(
            "rev288 strict normalized Johnson evidence and rev286 terminal-cost accounting "
            "were independently replayed and are field-for-field bound inside one root envelope"
        ),
    )


def replay_normalized_johnson_terminal_cost_binding(
    binding: CorrectedSOJNormalizedJohnsonCostBinding,
    normalized_bundle: Any,
    terminal_cost_certificate: Any,
    *,
    normalized_replay_verified: bool,
    terminal_cost_replay_verified: bool,
) -> bool:
    if not isinstance(binding, CorrectedSOJNormalizedJohnsonCostBinding):
        return False
    try:
        rebuilt = bind_normalized_johnson_terminal_cost(
            normalized_bundle,
            terminal_cost_certificate,
            normalized_replay_verified=normalized_replay_verified,
            terminal_cost_replay_verified=terminal_cost_replay_verified,
        )
    except (
        CorrectedSOJNormalizedJohnsonCostBindingError,
        TypeError,
        ValueError,
        OverflowError,
    ):
        return False
    return rebuilt == binding
