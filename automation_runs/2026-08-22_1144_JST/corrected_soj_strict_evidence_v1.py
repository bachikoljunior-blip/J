from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from collections.abc import Mapping
from typing import Any


EXPECTED_TRANSITION_STATUS = "certified_corrected_soj_explicit_johnson_embedding"
EXPECTED_TRANSITION_KIND = "johnson_embedding"
EXPECTED_TERMINAL_OPERATION = "primitive_johnson_ground_terminal"
EXACT_TERMINAL_STATUSES = frozenset(
    {
        "exact_empty_primitive_johnson_ground",
        "exact_primitive_johnson_ground_coset",
    }
)


class StrictCorrectedSOJEvidenceError(ValueError):
    """Raised when structural Johnson evidence is not type-exact and self-consistent."""


def _field(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        if name not in value:
            raise StrictCorrectedSOJEvidenceError(f"evidence is missing required field {name!r}")
        return value[name]
    if not hasattr(value, name):
        raise StrictCorrectedSOJEvidenceError(f"evidence is missing required field {name!r}")
    return getattr(value, name)


def _strict_bool(name: str, value: Any) -> bool:
    if type(value) is not bool:
        raise StrictCorrectedSOJEvidenceError(f"{name} must be an exact bool")
    return value


def _strict_int(name: str, value: Any, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise StrictCorrectedSOJEvidenceError(f"{name} must be an exact integer")
    if minimum is not None and value < minimum:
        raise StrictCorrectedSOJEvidenceError(f"{name} must be at least {minimum}")
    return value


def _strict_real(name: str, value: Any, *, minimum: float | None = None) -> float:
    if type(value) not in (int, float):
        raise StrictCorrectedSOJEvidenceError(f"{name} must be an exact JSON-style number")
    result = float(value)
    if not math.isfinite(result):
        raise StrictCorrectedSOJEvidenceError(f"{name} must be finite")
    if minimum is not None and result < minimum:
        raise StrictCorrectedSOJEvidenceError(f"{name} must be at least {minimum}")
    return result


def _strict_text(name: str, value: Any) -> str:
    if type(value) is not str or not value:
        raise StrictCorrectedSOJEvidenceError(f"{name} must be a non-empty exact string")
    return value


def _optional_identity(value: Any) -> str | None:
    if value is None:
        return None
    return _strict_text("terminal.proof_identity", value)


@dataclass(frozen=True)
class StrictTransitionEvidence:
    status: str
    transition_kind: str
    theorem_input_gate: bool
    canonical: bool
    exact: bool
    progress_certified: bool
    multiplicative_cost: float
    max_multiplicative_cost: float
    johnson_ground_size: int
    johnson_subset_size: int
    johnson_vertex_count: int
    reason: str


@dataclass(frozen=True)
class StrictTerminalEvidence:
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
class StrictJohnsonEvidenceBundle:
    schema: str
    root_n: int
    current_domain_size: int
    transition: StrictTransitionEvidence
    terminal: StrictTerminalEvidence
    full_johnson_vertex_count: int
    replay_stable_upstream_identity: bool
    evidence_identity: str


def _normalize_transition(value: Any) -> StrictTransitionEvidence:
    transition = StrictTransitionEvidence(
        status=_strict_text("transition.status", _field(value, "status")),
        transition_kind=_strict_text(
            "transition.transition_kind", _field(value, "transition_kind")
        ),
        theorem_input_gate=_strict_bool(
            "transition.theorem_input_gate", _field(value, "theorem_input_gate")
        ),
        canonical=_strict_bool("transition.canonical", _field(value, "canonical")),
        exact=_strict_bool("transition.exact", _field(value, "exact")),
        progress_certified=_strict_bool(
            "transition.progress_certified", _field(value, "progress_certified")
        ),
        multiplicative_cost=_strict_real(
            "transition.multiplicative_cost", _field(value, "multiplicative_cost"), minimum=0.0
        ),
        max_multiplicative_cost=_strict_real(
            "transition.max_multiplicative_cost",
            _field(value, "max_multiplicative_cost"),
            minimum=1.0,
        ),
        johnson_ground_size=_strict_int(
            "transition.johnson_ground_size", _field(value, "johnson_ground_size"), minimum=4
        ),
        johnson_subset_size=_strict_int(
            "transition.johnson_subset_size", _field(value, "johnson_subset_size"), minimum=2
        ),
        johnson_vertex_count=_strict_int(
            "transition.johnson_vertex_count", _field(value, "johnson_vertex_count"), minimum=1
        ),
        reason=_strict_text("transition.reason", _field(value, "reason")),
    )
    if transition.status != EXPECTED_TRANSITION_STATUS:
        raise StrictCorrectedSOJEvidenceError("transition status is not the certified Johnson status")
    if transition.transition_kind != EXPECTED_TRANSITION_KIND:
        raise StrictCorrectedSOJEvidenceError("transition kind is not johnson_embedding")
    if not (
        transition.theorem_input_gate
        and transition.canonical
        and transition.exact
        and transition.progress_certified
    ):
        raise StrictCorrectedSOJEvidenceError(
            "transition theorem/canonical/exact/progress flags must all be true"
        )
    if transition.johnson_subset_size > transition.johnson_ground_size - 2:
        raise StrictCorrectedSOJEvidenceError("invalid Johnson subset size")
    if transition.multiplicative_cost > transition.max_multiplicative_cost:
        raise StrictCorrectedSOJEvidenceError(
            "transition multiplicative cost exceeds its stated maximum"
        )
    expected_vertices = math.comb(
        transition.johnson_ground_size, transition.johnson_subset_size
    )
    if transition.johnson_vertex_count != expected_vertices:
        raise StrictCorrectedSOJEvidenceError(
            "transition Johnson vertex count is not the full J(v,k) domain"
        )
    return transition


def _normalize_terminal(value: Any) -> StrictTerminalEvidence:
    terminal = StrictTerminalEvidence(
        status=_strict_text("terminal.status", _field(value, "status")),
        operation_kind=_strict_text(
            "terminal.operation_kind", _field(value, "operation_kind")
        ),
        root_n=_strict_int("terminal.root_n", _field(value, "root_n"), minimum=1),
        domain_size=_strict_int(
            "terminal.domain_size", _field(value, "domain_size"), minimum=1
        ),
        canonical=_strict_bool("terminal.canonical", _field(value, "canonical")),
        exact=_strict_bool("terminal.exact", _field(value, "exact")),
        local_cost_certified=_strict_bool(
            "terminal.local_cost_certified", _field(value, "local_cost_certified")
        ),
        local_log2_cost_bound=_strict_real(
            "terminal.local_log2_cost_bound",
            _field(value, "local_log2_cost_bound"),
            minimum=0.0,
        ),
        terminal_certified=_strict_bool(
            "terminal.terminal_certified", _field(value, "terminal_certified")
        ),
        johnson_ground_size=_strict_int(
            "terminal.johnson_ground_size", _field(value, "johnson_ground_size"), minimum=4
        ),
        johnson_subset_size=_strict_int(
            "terminal.johnson_subset_size", _field(value, "johnson_subset_size"), minimum=2
        ),
        ground_permutations_checked=_strict_int(
            "terminal.ground_permutations_checked",
            _field(value, "ground_permutations_checked"),
            minimum=0,
        ),
        recognition_search_nodes=_strict_int(
            "terminal.recognition_search_nodes",
            _field(value, "recognition_search_nodes"),
            minimum=0,
        ),
        proof_identity=_optional_identity(_field(value, "proof_identity")),
    )
    if terminal.status not in EXACT_TERMINAL_STATUSES:
        raise StrictCorrectedSOJEvidenceError("terminal status is not an exact Johnson terminal status")
    if terminal.operation_kind != EXPECTED_TERMINAL_OPERATION:
        raise StrictCorrectedSOJEvidenceError("terminal operation kind is not primitive Johnson")
    if not (
        terminal.canonical
        and terminal.exact
        and terminal.local_cost_certified
        and terminal.terminal_certified
    ):
        raise StrictCorrectedSOJEvidenceError(
            "terminal canonical/exact/cost/terminal flags must all be true"
        )
    if terminal.johnson_subset_size > terminal.johnson_ground_size - 2:
        raise StrictCorrectedSOJEvidenceError("invalid terminal Johnson subset size")
    return terminal


def _identity_payload(
    *,
    root_n: int,
    current_domain_size: int,
    transition: StrictTransitionEvidence,
    terminal: StrictTerminalEvidence,
    full_johnson_vertex_count: int,
) -> str:
    payload = {
        "schema": "rev288_corrected_soj_strict_evidence_v1",
        "root_n": root_n,
        "current_domain_size": current_domain_size,
        "transition": asdict(transition),
        "terminal": asdict(terminal),
        "full_johnson_vertex_count": full_johnson_vertex_count,
    }
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StrictCorrectedSOJEvidenceError(
            "strict evidence is not canonically serializable"
        ) from exc
    return sha256(encoded).hexdigest()


def normalize_corrected_soj_johnson_evidence(
    transition_value: Any,
    terminal_value: Any,
    *,
    root_n: int,
    current_domain_size: int,
) -> StrictJohnsonEvidenceBundle:
    """Normalize already-produced Johnson transition/terminal evidence without coercion.

    This boundary intentionally performs no transition admission, terminal execution,
    recurrence accounting, coset promotion, or production dispatch.  It only proves
    that the public structural fields consumed by those later stages have exact
    primitive types and mutually consistent Johnson dimensions.
    """
    root_n = _strict_int("root_n", root_n, minimum=1)
    current_domain_size = _strict_int(
        "current_domain_size", current_domain_size, minimum=1
    )
    if current_domain_size > root_n:
        raise StrictCorrectedSOJEvidenceError("current domain exceeds the root envelope")

    transition = _normalize_transition(transition_value)
    terminal = _normalize_terminal(terminal_value)
    full_vertex_count = transition.johnson_vertex_count

    if current_domain_size <= full_vertex_count:
        raise StrictCorrectedSOJEvidenceError(
            "Johnson terminal evidence does not represent a strict domain reduction"
        )
    if terminal.root_n != root_n:
        raise StrictCorrectedSOJEvidenceError("terminal root_n differs from caller root_n")
    if terminal.domain_size != full_vertex_count:
        raise StrictCorrectedSOJEvidenceError(
            "terminal domain size differs from the full Johnson vertex count"
        )
    if (
        terminal.johnson_ground_size != transition.johnson_ground_size
        or terminal.johnson_subset_size != transition.johnson_subset_size
    ):
        raise StrictCorrectedSOJEvidenceError(
            "terminal Johnson parameters differ from the transition"
        )

    identity = _identity_payload(
        root_n=root_n,
        current_domain_size=current_domain_size,
        transition=transition,
        terminal=terminal,
        full_johnson_vertex_count=full_vertex_count,
    )
    return StrictJohnsonEvidenceBundle(
        schema="rev288_corrected_soj_strict_evidence_v1",
        root_n=root_n,
        current_domain_size=current_domain_size,
        transition=transition,
        terminal=terminal,
        full_johnson_vertex_count=full_vertex_count,
        replay_stable_upstream_identity=terminal.proof_identity is not None,
        evidence_identity=identity,
    )


def replay_corrected_soj_johnson_evidence(
    bundle: StrictJohnsonEvidenceBundle,
    transition_value: Any,
    terminal_value: Any,
    *,
    root_n: int,
    current_domain_size: int,
) -> bool:
    if not isinstance(bundle, StrictJohnsonEvidenceBundle):
        return False
    try:
        rebuilt = normalize_corrected_soj_johnson_evidence(
            transition_value,
            terminal_value,
            root_n=root_n,
            current_domain_size=current_domain_size,
        )
    except (StrictCorrectedSOJEvidenceError, TypeError, ValueError, OverflowError):
        return False
    return rebuilt == bundle
