from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import isfinite, log2
from pathlib import Path
import sys
from typing import Any

_MAIN_RUN = Path(__file__).resolve().parents[1] / "2026-08-19_0851_JST"
if str(_MAIN_RUN) not in sys.path:
    sys.path.insert(0, str(_MAIN_RUN))

from quasipoly_recurrence_accounting_v1 import (  # noqa: E402
    QuasipolyAccountingValidation,
    RecurrenceAccountingNode,
    validate_quasipoly_recurrence_tree,
)


SCHEMA_VERSION = 1
EXPECTED_STATUS = "certified_corrected_soj_small_part_reduction"
EXPECTED_KIND = "small_part_reduction"
SUCCESS_STATUS = "certified_corrected_soj_zero_aux_terminal_accounting"
FAIL_STATUS = "corrected_soj_zero_aux_terminal_not_certified"


@dataclass(frozen=True)
class CorrectedSOJZeroAuxTransitionSnapshot:
    status: str
    transition_kind: str
    theorem_input_gate: bool
    canonical: bool
    exact: bool
    progress_certified: bool
    multiplicative_cost: float
    max_multiplicative_cost: float
    small_size_before: int
    small_size_after: int
    alpha: float


@dataclass(frozen=True)
class CorrectedSOJZeroAuxTerminalComposition:
    schema_version: int
    status: str
    certified: bool
    transition: CorrectedSOJZeroAuxTransitionSnapshot | None
    accounting_root: RecurrenceAccountingNode | None
    validation: QuasipolyAccountingValidation | None
    terminal_semantics_certified: bool
    transition_cost_bound_certified: bool
    charged_log2_transition_cost: float
    composition_digest: str
    reason: str


def _fail(reason: str) -> CorrectedSOJZeroAuxTerminalComposition:
    return CorrectedSOJZeroAuxTerminalComposition(
        SCHEMA_VERSION,
        FAIL_STATUS,
        False,
        None,
        None,
        None,
        False,
        False,
        0.0,
        "",
        reason,
    )


def _field(obj: Any, name: str):
    if not hasattr(obj, name):
        raise ValueError(f"transition is missing required field {name!r}")
    return getattr(obj, name)


def _snapshot(transition: Any) -> CorrectedSOJZeroAuxTransitionSnapshot:
    return CorrectedSOJZeroAuxTransitionSnapshot(
        status=str(_field(transition, "status")),
        transition_kind=str(_field(transition, "transition_kind")),
        theorem_input_gate=bool(_field(transition, "theorem_input_gate")),
        canonical=bool(_field(transition, "canonical")),
        exact=bool(_field(transition, "exact")),
        progress_certified=bool(_field(transition, "progress_certified")),
        multiplicative_cost=float(_field(transition, "multiplicative_cost")),
        max_multiplicative_cost=float(_field(transition, "max_multiplicative_cost")),
        small_size_before=int(_field(transition, "small_size_before")),
        small_size_after=int(_field(transition, "small_size_after")),
        alpha=float(_field(transition, "alpha")),
    )


def _validate_transition_shape(
    snap: CorrectedSOJZeroAuxTransitionSnapshot,
    *,
    root_n: int,
) -> str | None:
    if snap.status != EXPECTED_STATUS or snap.transition_kind != EXPECTED_KIND:
        return "only a certified corrected-SOJ small-part reduction can terminate the auxiliary problem here"
    if not snap.theorem_input_gate:
        return "the corrected bipartite Split-or-Johnson theorem-input gate is not certified"
    if not snap.canonical or not snap.exact or not snap.progress_certified:
        return "transition must be canonical, exact, and progress-certified"
    if not isfinite(snap.multiplicative_cost) or snap.multiplicative_cost < 1.0:
        return "transition multiplicative cost must be finite and at least one"
    if not isfinite(snap.max_multiplicative_cost) or snap.max_multiplicative_cost < 1.0:
        return "transition multiplicative-cost bound must be finite and at least one"
    if snap.multiplicative_cost > snap.max_multiplicative_cost:
        return "transition multiplicative cost exceeds its certified upper bound"
    if snap.small_size_before <= 0:
        return "small_size_before must be positive"
    if snap.small_size_after != 0:
        return "zero-auxiliary terminal accounting requires small_size_after == 0 exactly"
    if snap.small_size_before > root_n:
        return "pre-transition auxiliary measure may not exceed the root primary measure"
    if not 2.0 / 3.0 <= snap.alpha < 1.0:
        return "transition alpha must lie in [2/3,1)"
    if not snap.small_size_after < snap.alpha * snap.small_size_before:
        return "transition does not satisfy its declared constant-factor auxiliary shrink"
    return None


def _digest(
    snap: CorrectedSOJZeroAuxTransitionSnapshot,
    *,
    root_n: int,
    charged_log2_transition_cost: float,
    shrink_fraction: float,
    polylog_power: int,
    quasipoly_power: int,
    quasipoly_constant: float,
) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "transition": snap.__dict__,
        "root_n": int(root_n),
        "terminal_semantics_certified": True,
        "transition_cost_bound_certified": True,
        "terminal_encoding": {
            "n": int(root_n),
            "m": int(snap.small_size_before),
            "terminal_certified": True,
            "children": 0,
        },
        "charged_log2_transition_cost": float(charged_log2_transition_cost),
        "recurrence_parameters": {
            "shrink_fraction": float(shrink_fraction),
            "polylog_power": int(polylog_power),
            "quasipoly_power": int(quasipoly_power),
            "quasipoly_constant": float(quasipoly_constant),
        },
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compose_corrected_soj_zero_aux_terminal_accounting(
    transition: Any,
    *,
    root_n: int,
    terminal_semantics_certified: bool,
    transition_cost_bound_certified: bool,
    shrink_fraction: float = 0.9,
    polylog_power: int = 2,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
) -> CorrectedSOJZeroAuxTerminalComposition:
    """Map an exactly terminal zero-aux corrected-SOJ edge into main recurrence accounting.

    ``small_size_after == 0`` alone is not treated as a proof that the original
    problem is solved. The caller must separately certify exact terminal
    semantics. If that gate is present, the transition is represented as a
    terminal node at the *pre-transition* positive auxiliary measure, so no
    synthetic ``m = 1`` child is introduced merely to satisfy the main type.
    """
    try:
        root_n = int(root_n)
        snap = _snapshot(transition)
    except (TypeError, ValueError, OverflowError) as exc:
        return _fail(f"malformed transition: {exc}")

    if root_n <= 0:
        return _fail("root_n must be positive")
    reason = _validate_transition_shape(snap, root_n=root_n)
    if reason is not None:
        return _fail(reason)
    if not terminal_semantics_certified:
        return _fail("zero auxiliary output lacks a separate exact terminal-semantics certificate")
    if not transition_cost_bound_certified:
        return _fail("transition multiplicative-cost upper bound is not mechanically certified")
    if not (0.0 < shrink_fraction < 1.0):
        return _fail("recurrence shrink_fraction must lie in (0,1)")
    if polylog_power < 1 or quasipoly_power < 1 or quasipoly_constant <= 0:
        return _fail("invalid quasipolynomial recurrence parameters")

    charge = log2(snap.max_multiplicative_cost)
    root = RecurrenceAccountingNode(
        n=root_n,
        m=snap.small_size_before,
        operation_kind="corrected_soj_zero_aux_terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=charge,
        children=(),
        terminal_certified=True,
        reason="caller-certified exact zero-auxiliary corrected-SOJ terminal",
    )
    try:
        validation = validate_quasipoly_recurrence_tree(
            root,
            shrink_fraction=shrink_fraction,
            polylog_power=polylog_power,
            quasipoly_power=quasipoly_power,
            quasipoly_constant=quasipoly_constant,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        return _fail(f"main recurrence validator rejected parameters: {exc}")
    if not validation.certified:
        return CorrectedSOJZeroAuxTerminalComposition(
            SCHEMA_VERSION,
            FAIL_STATUS,
            False,
            snap,
            root,
            validation,
            True,
            True,
            charge,
            "",
            f"main recurrence accounting rejected the terminal mapping: {validation.status}: {validation.reason}",
        )

    digest = _digest(
        snap,
        root_n=root_n,
        charged_log2_transition_cost=charge,
        shrink_fraction=shrink_fraction,
        polylog_power=polylog_power,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    return CorrectedSOJZeroAuxTerminalComposition(
        SCHEMA_VERSION,
        SUCCESS_STATUS,
        True,
        snap,
        root,
        validation,
        True,
        True,
        charge,
        digest,
        "exact zero-auxiliary corrected-SOJ transition is terminal-accounted without fabricating a positive child measure",
    )


def replay_corrected_soj_zero_aux_terminal_accounting(
    composition: CorrectedSOJZeroAuxTerminalComposition,
    transition: Any,
    *,
    root_n: int,
    terminal_semantics_certified: bool,
    transition_cost_bound_certified: bool,
    shrink_fraction: float = 0.9,
    polylog_power: int = 2,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
) -> bool:
    if not composition.certified or not composition.composition_digest:
        return False
    replayed = compose_corrected_soj_zero_aux_terminal_accounting(
        transition,
        root_n=root_n,
        terminal_semantics_certified=terminal_semantics_certified,
        transition_cost_bound_certified=transition_cost_bound_certified,
        shrink_fraction=shrink_fraction,
        polylog_power=polylog_power,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    return bool(
        replayed.certified
        and replayed.composition_digest == composition.composition_digest
        and replayed.accounting_root == composition.accounting_root
        and replayed.validation == composition.validation
    )
