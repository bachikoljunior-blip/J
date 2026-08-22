from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from typing import Any

_BASE_DIR = Path(__file__).resolve().parents[1] / "2026-08-19_0851_JST"
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

from primitive_johnson_ground_terminal_v1 import PrimitiveJohnsonGroundProof
from quasipoly_recurrence_accounting_v1 import (
    QuasipolyAccountingValidation,
    RecurrenceAccountingNode,
    validate_quasipoly_recurrence_tree,
)


EXPECTED_TRANSITION_STATUS = "certified_corrected_soj_explicit_johnson_embedding"
EXPECTED_TRANSITION_KIND = "johnson_embedding"
EXPECTED_TERMINAL_OPERATION = "primitive_johnson_ground_terminal"
EXACT_TERMINAL_STATUSES = frozenset(
    {
        "exact_empty_primitive_johnson_ground",
        "exact_primitive_johnson_ground_coset",
    }
)


class CorrectedSOJJohnsonTerminalCostError(ValueError):
    """Raised when post-admission Johnson terminal accounting cannot be certified."""


@dataclass(frozen=True)
class CorrectedSOJJohnsonTransitionSnapshot:
    status: str
    transition_kind: str
    theorem_input_gate: bool
    current_domain_size: int
    johnson_ground_size: int
    johnson_subset_size: int
    johnson_vertex_count: int
    canonical: bool
    exact: bool
    progress_certified: bool
    multiplicative_cost: float
    max_multiplicative_cost: float
    proof_identity: str


@dataclass(frozen=True)
class PrimitiveJohnsonTerminalSnapshot:
    status: str
    operation_kind: str
    root_n: int
    domain_size: int
    canonical: bool
    exact: bool
    local_cost_certified: bool
    local_log2_cost_bound: float
    terminal_certified: bool
    johnson_ground_size: int
    johnson_subset_size: int
    ground_permutations_checked: int
    recognition_search_nodes: int
    proof_identity: str | None


@dataclass(frozen=True)
class CorrectedSOJJohnsonTerminalCostCertificate:
    certified: bool
    transition: CorrectedSOJJohnsonTransitionSnapshot
    terminal: PrimitiveJohnsonTerminalSnapshot
    transition_log2_charge: float
    terminal_log2_charge: float
    accounting_root: RecurrenceAccountingNode
    validation: QuasipolyAccountingValidation
    proof_identity: str
    reason: str


def _require_attr(value: Any, name: str) -> Any:
    if not hasattr(value, name):
        raise CorrectedSOJJohnsonTerminalCostError(
            f"transition is missing required field {name!r}"
        )
    return getattr(value, name)


def _snapshot_transition(value: Any) -> CorrectedSOJJohnsonTransitionSnapshot:
    identity = _require_attr(value, "proof_identity")
    if not isinstance(identity, str) or not identity:
        raise CorrectedSOJJohnsonTerminalCostError(
            "transition proof_identity must be a nonempty string"
        )
    return CorrectedSOJJohnsonTransitionSnapshot(
        status=str(_require_attr(value, "status")),
        transition_kind=str(_require_attr(value, "transition_kind")),
        theorem_input_gate=bool(_require_attr(value, "theorem_input_gate")),
        current_domain_size=int(_require_attr(value, "current_domain_size")),
        johnson_ground_size=int(_require_attr(value, "johnson_ground_size")),
        johnson_subset_size=int(_require_attr(value, "johnson_subset_size")),
        johnson_vertex_count=int(_require_attr(value, "johnson_vertex_count")),
        canonical=bool(_require_attr(value, "canonical")),
        exact=bool(_require_attr(value, "exact")),
        progress_certified=bool(_require_attr(value, "progress_certified")),
        multiplicative_cost=float(_require_attr(value, "multiplicative_cost")),
        max_multiplicative_cost=float(_require_attr(value, "max_multiplicative_cost")),
        proof_identity=identity,
    )


def _validate_transition(
    transition: CorrectedSOJJohnsonTransitionSnapshot,
    *,
    transition_cost_bound_certified: bool,
) -> int:
    if not transition_cost_bound_certified:
        raise CorrectedSOJJohnsonTerminalCostError(
            "transition multiplicative-cost bound lacks an external/mechanical certificate"
        )
    if transition.status != EXPECTED_TRANSITION_STATUS:
        raise CorrectedSOJJohnsonTerminalCostError(
            "transition status is not the certified corrected-SOJ Johnson embedding status"
        )
    if transition.transition_kind != EXPECTED_TRANSITION_KIND:
        raise CorrectedSOJJohnsonTerminalCostError(
            "transition kind is not johnson_embedding"
        )
    if not (
        transition.theorem_input_gate
        and transition.canonical
        and transition.exact
        and transition.progress_certified
    ):
        raise CorrectedSOJJohnsonTerminalCostError(
            "transition theorem gate/canonical/exact/progress contract is incomplete"
        )

    v = transition.johnson_ground_size
    k = transition.johnson_subset_size
    if v < 4 or k < 2 or k > v - 2:
        raise CorrectedSOJJohnsonTerminalCostError(
            "invalid Johnson ground/subset parameters"
        )
    full_vertex_count = math.comb(v, k)
    if transition.johnson_vertex_count != full_vertex_count:
        raise CorrectedSOJJohnsonTerminalCostError(
            "only a full Johnson domain can be composed with the exact primitive-Johnson terminal"
        )
    if transition.current_domain_size <= full_vertex_count:
        raise CorrectedSOJJohnsonTerminalCostError(
            "Johnson embedding must strictly reduce the current domain before terminal execution"
        )

    actual = transition.multiplicative_cost
    bound = transition.max_multiplicative_cost
    if not math.isfinite(actual) or actual < 0.0:
        raise CorrectedSOJJohnsonTerminalCostError(
            "transition multiplicative cost must be finite and nonnegative"
        )
    if not math.isfinite(bound) or bound < 1.0:
        raise CorrectedSOJJohnsonTerminalCostError(
            "transition maximum multiplicative cost must be finite and at least one"
        )
    if actual > bound + 1e-12:
        raise CorrectedSOJJohnsonTerminalCostError(
            "transition actual multiplicative cost exceeds its certified maximum"
        )
    return full_vertex_count


def _snapshot_terminal(
    proof: PrimitiveJohnsonGroundProof,
) -> PrimitiveJohnsonTerminalSnapshot:
    proof_identity = proof.proof_identity
    if proof_identity is not None:
        proof_identity = str(proof_identity)
    return PrimitiveJohnsonTerminalSnapshot(
        status=str(proof.status),
        operation_kind=str(proof.operation_kind),
        root_n=int(proof.root_n),
        domain_size=int(proof.domain_size),
        canonical=bool(proof.canonical),
        exact=bool(proof.exact),
        local_cost_certified=bool(proof.local_cost_certified),
        local_log2_cost_bound=float(proof.local_log2_cost_bound),
        terminal_certified=bool(proof.terminal_certified),
        johnson_ground_size=int(proof.johnson_ground_size),
        johnson_subset_size=int(proof.johnson_subset_size),
        ground_permutations_checked=int(proof.ground_permutations_checked),
        recognition_search_nodes=int(proof.recognition_search_nodes),
        proof_identity=proof_identity,
    )


def _validate_terminal(
    proof: PrimitiveJohnsonGroundProof,
    terminal: PrimitiveJohnsonTerminalSnapshot,
    transition: CorrectedSOJJohnsonTransitionSnapshot,
    *,
    full_vertex_count: int,
    root_n: int,
    terminal_admission_certified: bool,
    quasipoly_power: int,
    quasipoly_constant: float,
) -> None:
    if not terminal_admission_certified:
        raise CorrectedSOJJohnsonTerminalCostError(
            "Johnson terminal admission must be certified by an external caller"
        )
    if not isinstance(proof, PrimitiveJohnsonGroundProof):
        raise CorrectedSOJJohnsonTerminalCostError(
            "terminal proof must be a PrimitiveJohnsonGroundProof"
        )
    if terminal.status not in EXACT_TERMINAL_STATUSES:
        raise CorrectedSOJJohnsonTerminalCostError(
            "primitive-Johnson terminal status is not exact"
        )
    if terminal.operation_kind != EXPECTED_TERMINAL_OPERATION:
        raise CorrectedSOJJohnsonTerminalCostError(
            "primitive-Johnson proof has the wrong terminal operation kind"
        )
    if not (
        terminal.canonical
        and terminal.exact
        and terminal.local_cost_certified
        and terminal.terminal_certified
    ):
        raise CorrectedSOJJohnsonTerminalCostError(
            "primitive-Johnson proof is not canonical, exact, cost-certified, and terminal"
        )
    if terminal.root_n != root_n:
        raise CorrectedSOJJohnsonTerminalCostError(
            "primitive-Johnson root envelope does not match the caller root_n"
        )
    if terminal.domain_size != full_vertex_count:
        raise CorrectedSOJJohnsonTerminalCostError(
            "primitive-Johnson domain size does not match the full Johnson embedding"
        )
    if (
        terminal.johnson_ground_size != transition.johnson_ground_size
        or terminal.johnson_subset_size != transition.johnson_subset_size
    ):
        raise CorrectedSOJJohnsonTerminalCostError(
            "primitive-Johnson ground/subset parameters do not match the transition"
        )
    if terminal.ground_permutations_checked < 0 or terminal.recognition_search_nodes < 0:
        raise CorrectedSOJJohnsonTerminalCostError(
            "primitive-Johnson execution counters must be nonnegative"
        )
    if (
        not math.isfinite(terminal.local_log2_cost_bound)
        or terminal.local_log2_cost_bound < 0.0
    ):
        raise CorrectedSOJJohnsonTerminalCostError(
            "primitive-Johnson local log2 cost bound must be finite and nonnegative"
        )
    if terminal.status == "exact_empty_primitive_johnson_ground":
        if proof.coset is not None:
            raise CorrectedSOJJohnsonTerminalCostError(
                "exact-empty primitive-Johnson proof must not carry a coset"
            )
    elif proof.coset is None:
        raise CorrectedSOJJohnsonTerminalCostError(
            "exact primitive-Johnson coset status requires a coset"
        )
    if proof.children:
        raise CorrectedSOJJohnsonTerminalCostError(
            "primitive-Johnson terminal proof may not contain proof children"
        )

    accounting = proof.accounting
    if not isinstance(accounting, RecurrenceAccountingNode):
        raise CorrectedSOJJohnsonTerminalCostError(
            "primitive-Johnson proof accounting has the wrong type"
        )
    if (
        accounting.n != root_n
        or accounting.m != full_vertex_count
        or accounting.operation_kind != EXPECTED_TERMINAL_OPERATION
        or not accounting.canonical
        or not accounting.cost_certified
        or not accounting.terminal_certified
        or accounting.children
        or abs(
            float(accounting.local_log2_cost_bound)
            - terminal.local_log2_cost_bound
        )
        > 1e-12
    ):
        raise CorrectedSOJJohnsonTerminalCostError(
            "primitive-Johnson proof/accounting leaf mismatch"
        )
    validation = validate_quasipoly_recurrence_tree(
        accounting,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not validation.certified:
        raise CorrectedSOJJohnsonTerminalCostError(
            f"primitive-Johnson accounting failed validation: {validation.status}"
        )


def _certificate_identity(
    *,
    transition: CorrectedSOJJohnsonTransitionSnapshot,
    terminal: PrimitiveJohnsonTerminalSnapshot,
    transition_log2_charge: float,
    terminal_log2_charge: float,
    accounting_root: RecurrenceAccountingNode,
    validation: QuasipolyAccountingValidation,
) -> str:
    payload = {
        "schema": "rev286_corrected_soj_johnson_terminal_cost_v1",
        "transition": asdict(transition),
        "terminal": asdict(terminal),
        "transition_log2_charge": transition_log2_charge,
        "terminal_log2_charge": terminal_log2_charge,
        "accounting_root": {
            "n": accounting_root.n,
            "m": accounting_root.m,
            "operation_kind": accounting_root.operation_kind,
            "canonical": accounting_root.canonical,
            "cost_certified": accounting_root.cost_certified,
            "local_log2_cost_bound": accounting_root.local_log2_cost_bound,
            "terminal_certified": accounting_root.terminal_certified,
            "children": len(accounting_root.children),
        },
        "validation": asdict(validation),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def compose_corrected_soj_johnson_terminal_cost(
    transition_value: Any,
    terminal_proof: PrimitiveJohnsonGroundProof,
    *,
    root_n: int,
    transition_cost_bound_certified: bool,
    terminal_admission_certified: bool,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
) -> CorrectedSOJJohnsonTerminalCostCertificate:
    """Compose an admitted full Johnson embedding with an exact primitive terminal.

    This function is deliberately post-admission. It does not decide whether a
    corrected Split-or-Johnson transition is semantically admissible, and it does
    not execute the primitive-Johnson terminal. The caller must separately
    certify both the transition cost bound and terminal admission.

    A full Johnson embedding followed by an already exact primitive-Johnson proof
    is represented as one terminal recurrence leaf at the pre-transition current
    domain measure. This charges both steps without pretending that the Johnson
    structural transition is an ``aux_shrink`` recurrence edge.
    """
    if root_n <= 0:
        raise CorrectedSOJJohnsonTerminalCostError("root_n must be positive")
    if quasipoly_power < 1 or quasipoly_constant <= 0:
        raise CorrectedSOJJohnsonTerminalCostError(
            "invalid quasipolynomial validation parameters"
        )

    transition = _snapshot_transition(transition_value)
    full_vertex_count = _validate_transition(
        transition,
        transition_cost_bound_certified=transition_cost_bound_certified,
    )
    if transition.current_domain_size > root_n:
        raise CorrectedSOJJohnsonTerminalCostError(
            "transition current domain exceeds the root envelope"
        )
    if not isinstance(terminal_proof, PrimitiveJohnsonGroundProof):
        raise CorrectedSOJJohnsonTerminalCostError(
            "terminal proof must be a PrimitiveJohnsonGroundProof"
        )
    terminal = _snapshot_terminal(terminal_proof)
    _validate_terminal(
        terminal_proof,
        terminal,
        transition,
        full_vertex_count=full_vertex_count,
        root_n=root_n,
        terminal_admission_certified=terminal_admission_certified,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )

    transition_charge = math.log2(transition.max_multiplicative_cost)
    terminal_charge = terminal.local_log2_cost_bound
    combined_charge = transition_charge + terminal_charge
    if not math.isfinite(combined_charge) or combined_charge < 0.0:
        raise CorrectedSOJJohnsonTerminalCostError(
            "combined terminal accounting charge is invalid"
        )

    accounting_root = RecurrenceAccountingNode(
        n=root_n,
        m=transition.current_domain_size,
        operation_kind="corrected_soj_johnson_terminal_composition",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=combined_charge,
        children=(),
        terminal_certified=True,
        reason=(
            "externally admitted full corrected-SOJ Johnson embedding followed by "
            "an already exact primitive-Johnson ground terminal; transition and "
            "terminal execution charges are composed into one terminal leaf"
        ),
    )
    validation = validate_quasipoly_recurrence_tree(
        accounting_root,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not validation.certified:
        raise CorrectedSOJJohnsonTerminalCostError(
            f"combined Johnson terminal accounting failed validation: {validation.status}"
        )

    identity = _certificate_identity(
        transition=transition,
        terminal=terminal,
        transition_log2_charge=transition_charge,
        terminal_log2_charge=terminal_charge,
        accounting_root=accounting_root,
        validation=validation,
    )
    return CorrectedSOJJohnsonTerminalCostCertificate(
        certified=True,
        transition=transition,
        terminal=terminal,
        transition_log2_charge=transition_charge,
        terminal_log2_charge=terminal_charge,
        accounting_root=accounting_root,
        validation=validation,
        proof_identity=identity,
        reason=(
            "full Johnson transition and exact primitive-Johnson terminal are "
            "structurally matched and jointly charged inside the root recurrence envelope"
        ),
    )


def replay_corrected_soj_johnson_terminal_cost(
    certificate: CorrectedSOJJohnsonTerminalCostCertificate,
    transition_value: Any,
    terminal_proof: PrimitiveJohnsonGroundProof,
    *,
    root_n: int,
    transition_cost_bound_certified: bool,
    terminal_admission_certified: bool,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
) -> bool:
    """Recompute the certificate and reject any structural/accounting drift."""
    if not isinstance(certificate, CorrectedSOJJohnsonTerminalCostCertificate):
        return False
    try:
        rebuilt = compose_corrected_soj_johnson_terminal_cost(
            transition_value,
            terminal_proof,
            root_n=root_n,
            transition_cost_bound_certified=transition_cost_bound_certified,
            terminal_admission_certified=terminal_admission_certified,
            quasipoly_power=quasipoly_power,
            quasipoly_constant=quasipoly_constant,
        )
    except (CorrectedSOJJohnsonTerminalCostError, TypeError, ValueError, OverflowError):
        return False
    return rebuilt == certificate
