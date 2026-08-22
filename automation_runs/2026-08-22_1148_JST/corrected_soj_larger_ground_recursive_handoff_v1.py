from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import comb, isfinite, log2
from pathlib import Path
import re
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
GROUND_CAP_STATUS = "undetermined_johnson_ground_cap"
GROUND_CAP_OPERATION = "primitive_johnson_ground_cap"
REDUCTION_STATUS = "certified_johnson_ground_relational_reduction"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class JohnsonGroundCapSnapshot:
    status: str
    operation_kind: str
    root_n: int
    domain_size: int
    canonical: bool
    exact: bool
    local_cost_certified: bool
    terminal_certified: bool
    johnson_ground_size: int
    johnson_subset_size: int


@dataclass(frozen=True)
class JohnsonGroundRelationalReductionSnapshot:
    status: str
    canonical: bool
    exact: bool
    progress_certified: bool
    solution_transport_certified: bool
    ambient_membership_transport_certified: bool
    complement_ambiguity_handled: bool
    source_action_degree: int
    johnson_ground_size: int
    johnson_subset_size: int
    child_ground_size: int
    multiplicative_cost: float
    max_multiplicative_cost: float
    reduction_identity: str


@dataclass(frozen=True)
class CorrectedSOJLargerGroundRecursiveHandoff:
    schema_version: int
    status: str
    certified: bool
    ground_cap: JohnsonGroundCapSnapshot | None
    reduction: JohnsonGroundRelationalReductionSnapshot | None
    accounting_root: RecurrenceAccountingNode | None
    validation: QuasipolyAccountingValidation | None
    charged_log2_reduction_cost: float
    handoff_digest: str
    reason: str


def _fail(
    reason: str,
    *,
    ground_cap: JohnsonGroundCapSnapshot | None = None,
    reduction: JohnsonGroundRelationalReductionSnapshot | None = None,
    accounting_root: RecurrenceAccountingNode | None = None,
    validation: QuasipolyAccountingValidation | None = None,
    charge: float = 0.0,
    status: str = "corrected_soj_larger_ground_handoff_not_certified",
) -> CorrectedSOJLargerGroundRecursiveHandoff:
    return CorrectedSOJLargerGroundRecursiveHandoff(
        SCHEMA_VERSION,
        status,
        False,
        ground_cap,
        reduction,
        accounting_root,
        validation,
        charge,
        "",
        reason,
    )


def _field(obj: Any, name: str):
    if not hasattr(obj, name):
        raise ValueError(f"missing required field {name!r}")
    return getattr(obj, name)


def _strict_bool(obj: Any, name: str) -> bool:
    value = _field(obj, name)
    if type(value) is not bool:
        raise ValueError(f"{name} must be a strict boolean")
    return value


def _strict_int(obj: Any, name: str) -> int:
    value = _field(obj, name)
    if type(value) is not int:
        raise ValueError(f"{name} must be a strict integer")
    return value


def _ground_cap_snapshot(proof: Any) -> JohnsonGroundCapSnapshot:
    return JohnsonGroundCapSnapshot(
        status=str(_field(proof, "status")),
        operation_kind=str(_field(proof, "operation_kind")),
        root_n=_strict_int(proof, "root_n"),
        domain_size=_strict_int(proof, "domain_size"),
        canonical=_strict_bool(proof, "canonical"),
        exact=_strict_bool(proof, "exact"),
        local_cost_certified=_strict_bool(proof, "local_cost_certified"),
        terminal_certified=_strict_bool(proof, "terminal_certified"),
        johnson_ground_size=_strict_int(proof, "johnson_ground_size"),
        johnson_subset_size=_strict_int(proof, "johnson_subset_size"),
    )


def _reduction_snapshot(reduction: Any) -> JohnsonGroundRelationalReductionSnapshot:
    cost = _field(reduction, "multiplicative_cost")
    max_cost = _field(reduction, "max_multiplicative_cost")
    if type(cost) not in (int, float) or type(cost) is bool:
        raise ValueError("multiplicative_cost must be a real number")
    if type(max_cost) not in (int, float) or type(max_cost) is bool:
        raise ValueError("max_multiplicative_cost must be a real number")
    return JohnsonGroundRelationalReductionSnapshot(
        status=str(_field(reduction, "status")),
        canonical=_strict_bool(reduction, "canonical"),
        exact=_strict_bool(reduction, "exact"),
        progress_certified=_strict_bool(reduction, "progress_certified"),
        solution_transport_certified=_strict_bool(reduction, "solution_transport_certified"),
        ambient_membership_transport_certified=_strict_bool(reduction, "ambient_membership_transport_certified"),
        complement_ambiguity_handled=_strict_bool(reduction, "complement_ambiguity_handled"),
        source_action_degree=_strict_int(reduction, "source_action_degree"),
        johnson_ground_size=_strict_int(reduction, "johnson_ground_size"),
        johnson_subset_size=_strict_int(reduction, "johnson_subset_size"),
        child_ground_size=_strict_int(reduction, "child_ground_size"),
        multiplicative_cost=float(cost),
        max_multiplicative_cost=float(max_cost),
        reduction_identity=str(_field(reduction, "reduction_identity")),
    )


def _validate_ground_cap(snap: JohnsonGroundCapSnapshot) -> str | None:
    if snap.status != GROUND_CAP_STATUS or snap.operation_kind != GROUND_CAP_OPERATION:
        return "handoff requires the main primitive-Johnson ground-cap outcome"
    if not snap.canonical:
        return "ground-cap recognition must be canonical"
    if snap.exact or snap.local_cost_certified or snap.terminal_certified:
        return "a larger-ground handoff may not relabel an unresolved cap result as an exact/cost-certified terminal"
    if snap.root_n <= 0 or snap.domain_size <= 0 or snap.domain_size > snap.root_n:
        return "ground-cap proof has invalid root/domain measures"
    v = snap.johnson_ground_size
    k = snap.johnson_subset_size
    if v < 4 or not 2 <= k <= v - 2:
        return "ground-cap proof has malformed Johnson parameters"
    if comb(v, k) != snap.domain_size:
        return "Johnson parameters do not reconstruct the represented action degree"
    return None


def _validate_reduction(
    snap: JohnsonGroundRelationalReductionSnapshot,
    parent: JohnsonGroundCapSnapshot,
    *,
    shrink_fraction: float,
) -> str | None:
    if snap.status != REDUCTION_STATUS:
        return "recursive handoff requires certified Johnson-ground relational reduction evidence"
    if not (snap.canonical and snap.exact and snap.progress_certified):
        return "relational reduction must be canonical, exact, and progress-certified"
    if not snap.solution_transport_certified:
        return "relational reduction does not certify exact solution transport"
    if not snap.ambient_membership_transport_certified:
        return "relational reduction does not certify ambient-membership transport"
    if not snap.complement_ambiguity_handled:
        return "Johnson complement ambiguity must be handled explicitly before recursive handoff"
    if snap.source_action_degree != parent.domain_size:
        return "relational reduction source degree differs from the certified Johnson action degree"
    if snap.johnson_ground_size != parent.johnson_ground_size or snap.johnson_subset_size != parent.johnson_subset_size:
        return "relational reduction Johnson parameters disagree with the ground-cap recognition"
    if snap.child_ground_size != parent.johnson_ground_size:
        return "recursive child measure must equal the certified Johnson ground size"
    if not isfinite(snap.multiplicative_cost) or snap.multiplicative_cost < 1.0:
        return "reduction multiplicative cost must be finite and at least one"
    if not isfinite(snap.max_multiplicative_cost) or snap.max_multiplicative_cost < 1.0:
        return "reduction multiplicative-cost bound must be finite and at least one"
    if snap.multiplicative_cost > snap.max_multiplicative_cost:
        return "reduction multiplicative cost exceeds its certified upper bound"
    if not _SHA256_RE.fullmatch(snap.reduction_identity):
        return "reduction identity must be a canonical sha256 digest"
    if not 0.0 < shrink_fraction < 1.0:
        return "shrink_fraction must lie in (0,1)"
    if snap.child_ground_size > shrink_fraction * parent.domain_size + 1e-12:
        return "Johnson-ground handoff does not achieve the configured auxiliary shrink"
    return None


def _digest(
    parent: JohnsonGroundCapSnapshot,
    reduction: JohnsonGroundRelationalReductionSnapshot,
    child: RecurrenceAccountingNode,
    charge: float,
    shrink_fraction: float,
) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "ground_cap": parent.__dict__,
        "reduction": reduction.__dict__,
        "child_measure": [int(child.n), int(child.m)],
        "child_operation_kind": str(child.operation_kind),
        "charged_log2_reduction_cost": float(charge),
        "shrink_fraction": float(shrink_fraction),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def compose_corrected_soj_larger_ground_recursive_handoff(
    ground_cap_proof: Any,
    relational_reduction: Any,
    *,
    child_accounting: RecurrenceAccountingNode,
    reduction_cost_bound_certified: bool,
    shrink_fraction: float = 0.9,
    polylog_power: int = 2,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
) -> CorrectedSOJLargerGroundRecursiveHandoff:
    """Bind the primitive Johnson ground-cap case to a certified recursive child.

    This function does not construct the relational reduction. It only consumes
    caller-supplied evidence that the J(v,k) action has been transformed exactly
    and canonically to a recursive problem on its ground v, including exact
    solution/ambient-membership transport and complement handling. The resulting
    measure change C(v,k) -> v is admitted as an ``aux_shrink`` edge only after
    the main recurrence validator accepts the complete child accounting tree.
    """
    try:
        parent = _ground_cap_snapshot(ground_cap_proof)
        reduction = _reduction_snapshot(relational_reduction)
    except (TypeError, ValueError) as exc:
        return _fail(str(exc))

    reason = _validate_ground_cap(parent)
    if reason is not None:
        return _fail(reason, ground_cap=parent)
    reason = _validate_reduction(reduction, parent, shrink_fraction=shrink_fraction)
    if reason is not None:
        return _fail(reason, ground_cap=parent, reduction=reduction)
    if type(reduction_cost_bound_certified) is not bool or not reduction_cost_bound_certified:
        return _fail(
            "recursive handoff does not manufacture a reduction cost certificate",
            ground_cap=parent,
            reduction=reduction,
        )
    if not isinstance(child_accounting, RecurrenceAccountingNode):
        return _fail(
            "child_accounting must be a main-integrated RecurrenceAccountingNode",
            ground_cap=parent,
            reduction=reduction,
        )
    if child_accounting.n != parent.root_n:
        return _fail(
            "recursive child must preserve the original-root primary accounting measure",
            ground_cap=parent,
            reduction=reduction,
        )
    if child_accounting.m != reduction.child_ground_size:
        return _fail(
            "recursive child auxiliary measure differs from the certified Johnson ground",
            ground_cap=parent,
            reduction=reduction,
        )

    charge = log2(reduction.max_multiplicative_cost)
    accounting_root = RecurrenceAccountingNode(
        n=parent.root_n,
        m=parent.domain_size,
        operation_kind="aux_shrink",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=charge,
        children=(AccountingChild(child_accounting, multiplicity=1),),
        terminal_certified=False,
        reason="certified exact Johnson-action to Johnson-ground relational recursive handoff",
    )
    validation = validate_quasipoly_recurrence_tree(
        accounting_root,
        shrink_fraction=shrink_fraction,
        polylog_power=polylog_power,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not validation.certified:
        return _fail(
            "main recurrence validator rejected the Johnson-ground recursive handoff: " + validation.reason,
            ground_cap=parent,
            reduction=reduction,
            accounting_root=accounting_root,
            validation=validation,
            charge=charge,
            status="corrected_soj_larger_ground_recurrence_rejected",
        )

    return CorrectedSOJLargerGroundRecursiveHandoff(
        SCHEMA_VERSION,
        "certified_corrected_soj_larger_ground_recursive_handoff",
        True,
        parent,
        reduction,
        accounting_root,
        validation,
        charge,
        _digest(parent, reduction, child_accounting, charge, shrink_fraction),
        "the unresolved primitive Johnson ground-cap is bound to exact relational reduction evidence and a strictly smaller replayable recursive child accepted by main recurrence accounting",
    )


def replay_corrected_soj_larger_ground_recursive_handoff(
    handoff: CorrectedSOJLargerGroundRecursiveHandoff,
    ground_cap_proof: Any,
    relational_reduction: Any,
    **kwargs,
) -> bool:
    if not isinstance(handoff, CorrectedSOJLargerGroundRecursiveHandoff) or not handoff.certified:
        return False
    replay = compose_corrected_soj_larger_ground_recursive_handoff(
        ground_cap_proof,
        relational_reduction,
        **kwargs,
    )
    return bool(
        replay.certified
        and replay == handoff
        and replay.handoff_digest == handoff.handoff_digest
    )


__all__ = [
    "JohnsonGroundCapSnapshot",
    "JohnsonGroundRelationalReductionSnapshot",
    "CorrectedSOJLargerGroundRecursiveHandoff",
    "compose_corrected_soj_larger_ground_recursive_handoff",
    "replay_corrected_soj_larger_ground_recursive_handoff",
]
