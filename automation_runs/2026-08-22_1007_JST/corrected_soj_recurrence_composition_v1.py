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
    AccountingChild,
    QuasipolyAccountingValidation,
    RecurrenceAccountingNode,
    validate_quasipoly_recurrence_tree,
)


SCHEMA_VERSION = 1
EXPECTED_STATUS = "certified_corrected_soj_small_part_reduction"
EXPECTED_KIND = "small_part_reduction"


@dataclass(frozen=True)
class CorrectedSOJTransitionSnapshot:
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
class CorrectedSOJRecurrenceComposition:
    schema_version: int
    status: str
    certified: bool
    transition: CorrectedSOJTransitionSnapshot | None
    accounting_root: RecurrenceAccountingNode | None
    validation: QuasipolyAccountingValidation | None
    branch_multiplicity: int
    charged_log2_transition_cost: float
    composition_digest: str
    reason: str


def _fail(reason: str) -> CorrectedSOJRecurrenceComposition:
    return CorrectedSOJRecurrenceComposition(
        SCHEMA_VERSION,
        "corrected_soj_recurrence_not_certified",
        False,
        None,
        None,
        None,
        0,
        0.0,
        "",
        reason,
    )


def _field(obj: Any, name: str):
    if not hasattr(obj, name):
        raise ValueError(f"transition is missing required field {name!r}")
    return getattr(obj, name)


def _snapshot(transition: Any) -> CorrectedSOJTransitionSnapshot:
    return CorrectedSOJTransitionSnapshot(
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
    snap: CorrectedSOJTransitionSnapshot,
    *,
    shrink_fraction: float,
) -> str | None:
    if snap.status != EXPECTED_STATUS or snap.transition_kind != EXPECTED_KIND:
        return "only the certified constant-factor small-part transition is recurrence-composable here"
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
    if not 1 <= snap.small_size_after < snap.small_size_before:
        return "recurrence composition requires a positive strictly smaller auxiliary child measure"
    if not 2.0 / 3.0 <= snap.alpha < 1.0:
        return "transition alpha must lie in [2/3,1)"
    if not snap.small_size_after < snap.alpha * snap.small_size_before:
        return "transition does not satisfy its declared constant-factor auxiliary shrink"
    if not 0.0 < shrink_fraction < 1.0:
        return "recurrence shrink_fraction must lie in (0,1)"
    if snap.alpha > shrink_fraction + 1e-12:
        return "transition alpha is weaker than the configured global recurrence shrink fraction"
    return None


def _digest(
    snap: CorrectedSOJTransitionSnapshot,
    root_n: int,
    child: RecurrenceAccountingNode,
    branch_multiplicity: int,
    shrink_fraction: float,
    charge: float,
) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "transition": snap.__dict__,
        "root_n": int(root_n),
        "child_measure": [int(child.n), int(child.m)],
        "child_operation_kind": str(child.operation_kind),
        "branch_multiplicity": int(branch_multiplicity),
        "shrink_fraction": float(shrink_fraction),
        "charged_log2_transition_cost": float(charge),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def compose_corrected_soj_small_part_recurrence(
    transition: Any,
    *,
    root_n: int,
    child_accounting: RecurrenceAccountingNode,
    transition_cost_bound_certified: bool,
    branch_multiplicity: int = 1,
    shrink_fraction: float = 0.9,
    polylog_power: int = 2,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
) -> CorrectedSOJRecurrenceComposition:
    """Compose one certified corrected-SOJ shrink edge into main recurrence accounting.

    The transition object is validated structurally rather than imported from the
    independently active transition branch.  This bridge deliberately accepts
    only the constant-factor auxiliary-part reduction form.  A Johnson embedding
    is structural evidence for a later exact caller, not by itself an `aux_shrink`
    recurrence edge.
    """
    try:
        snap = _snapshot(transition)
    except (TypeError, ValueError) as exc:
        return _fail(str(exc))

    reason = _validate_transition_shape(snap, shrink_fraction=shrink_fraction)
    if reason is not None:
        return _fail(reason)
    if not transition_cost_bound_certified:
        return _fail(
            "recurrence accounting does not manufacture a local cost certificate; the transition bound must be certified externally"
        )
    if not isinstance(child_accounting, RecurrenceAccountingNode):
        return _fail("child_accounting must be a main-integrated RecurrenceAccountingNode")

    n = int(root_n)
    multiplicity = int(branch_multiplicity)
    if n <= 0 or snap.small_size_before > n:
        return _fail("parent recurrence measure requires 1 <= small_size_before <= root_n")
    if multiplicity <= 0:
        return _fail("branch multiplicity must be positive")
    if child_accounting.n > n:
        return _fail("child primary measure may not exceed the parent root measure")
    if child_accounting.m != snap.small_size_after:
        return _fail("child auxiliary measure does not equal the certified transition output size")

    charge = log2(snap.max_multiplicative_cost)
    accounting_root = RecurrenceAccountingNode(
        n=n,
        m=snap.small_size_before,
        operation_kind="aux_shrink",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=charge,
        children=(AccountingChild(child_accounting, multiplicity=multiplicity),),
        terminal_certified=False,
        reason="corrected Split-or-Johnson constant-factor auxiliary reduction",
    )
    validation = validate_quasipoly_recurrence_tree(
        accounting_root,
        shrink_fraction=shrink_fraction,
        polylog_power=polylog_power,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not validation.certified:
        return CorrectedSOJRecurrenceComposition(
            SCHEMA_VERSION,
            "corrected_soj_recurrence_not_certified",
            False,
            snap,
            accounting_root,
            validation,
            multiplicity,
            charge,
            "",
            "main recurrence validator rejected the composed edge: " + validation.reason,
        )

    return CorrectedSOJRecurrenceComposition(
        SCHEMA_VERSION,
        "certified_corrected_soj_recurrence_composition",
        True,
        snap,
        accounting_root,
        validation,
        multiplicity,
        charge,
        _digest(snap, n, child_accounting, multiplicity, shrink_fraction, charge),
        "the certified corrected-SOJ auxiliary reduction is linked to the exact child measure and composes through the main quasipolynomial recurrence validator",
    )


def replay_corrected_soj_recurrence_composition(
    composition: CorrectedSOJRecurrenceComposition,
    transition: Any,
    *,
    root_n: int,
    child_accounting: RecurrenceAccountingNode,
    transition_cost_bound_certified: bool,
    branch_multiplicity: int = 1,
    shrink_fraction: float = 0.9,
    polylog_power: int = 2,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
) -> bool:
    if not isinstance(composition, CorrectedSOJRecurrenceComposition) or not composition.certified:
        return False
    replay = compose_corrected_soj_small_part_recurrence(
        transition,
        root_n=root_n,
        child_accounting=child_accounting,
        transition_cost_bound_certified=transition_cost_bound_certified,
        branch_multiplicity=branch_multiplicity,
        shrink_fraction=shrink_fraction,
        polylog_power=polylog_power,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    return replay == composition and replay.composition_digest == composition.composition_digest


__all__ = [
    "CorrectedSOJRecurrenceComposition",
    "CorrectedSOJTransitionSnapshot",
    "compose_corrected_soj_small_part_recurrence",
    "replay_corrected_soj_recurrence_composition",
]
