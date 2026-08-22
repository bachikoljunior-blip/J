from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = 1
VIEW_STATUS = "certified_recursive_production_post_replay_view"
ENVELOPE_STATUS = "certified_recursive_production_post_replay_envelope"
_ALLOWED_KINDS = frozenset({"production_cost_provenance", "provenance_total_cost"})
_ALLOWED_OUTCOMES = frozenset({"exact_empty", "nonempty"})
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class RecursiveProductionPostReplayView:
    schema_version: int
    status: str
    kind: str
    replay_verified: bool
    exact: bool
    complete: bool
    outcome_kind: str
    parent_action_degree: int
    child_ground_size: int
    reduction_identity: str
    production_provenance_identity: str
    construction_cost_binding_identity: str
    construction_multiplicative_cost_bound: float
    charged_log2_reduction_cost: float
    upstream_identity: str
    view_identity: str
    reason: str


@dataclass(frozen=True)
class RecursiveProductionPostReplayEnvelope:
    schema_version: int
    status: str
    certified: bool
    exact: bool
    complete: bool
    outcome_kind: str
    parent_action_degree: int
    child_ground_size: int
    reduction_identity: str
    production_provenance_identity: str
    construction_cost_binding_identity: str
    construction_multiplicative_cost_bound: float
    charged_log2_reduction_cost: float
    production_cost_provenance_identity: str
    provenance_total_cost_identity: str
    envelope_identity: str
    reason: str


def _canonical_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _strict_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a strict boolean")
    return value


def _strict_int(value: Any, name: str, *, minimum: int = 1) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be a strict integer >= {minimum}")
    return value


def _digest(value: Any, name: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{name} must be a canonical sha256 digest")
    return value


def _finite(value: Any, name: str, *, minimum: float = 0.0) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise ValueError(f"{name} must be a finite real number")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return result


def _fail_view(kind: str, reason: str) -> RecursiveProductionPostReplayView:
    return RecursiveProductionPostReplayView(
        SCHEMA_VERSION,
        "recursive_production_post_replay_view_not_certified",
        kind,
        False,
        False,
        False,
        "undetermined",
        0,
        0,
        "",
        "",
        "",
        0.0,
        0.0,
        "",
        "",
        reason,
    )


def _fail_envelope(reason: str) -> RecursiveProductionPostReplayEnvelope:
    return RecursiveProductionPostReplayEnvelope(
        SCHEMA_VERSION,
        "recursive_production_post_replay_envelope_not_certified",
        False,
        False,
        False,
        "undetermined",
        0,
        0,
        "",
        "",
        "",
        0.0,
        0.0,
        "",
        "",
        "",
        reason,
    )


def certify_post_replay_view(
    *,
    kind: str,
    replay_verified: bool,
    exact: bool,
    complete: bool,
    outcome_kind: str,
    parent_action_degree: int,
    child_ground_size: int,
    reduction_identity: str,
    production_provenance_identity: str,
    construction_cost_binding_identity: str,
    construction_multiplicative_cost_bound: float,
    charged_log2_reduction_cost: float,
    upstream_identity: str,
) -> RecursiveProductionPostReplayView:
    """Normalize one already replay-verified upstream certificate without importing it.

    This function deliberately does not claim to replay branch-only rev720/rev900
    objects. The caller must obtain ``replay_verified=True`` from the owning
    upstream replay routine and expose only this public compatibility tuple.
    """
    try:
        if kind not in _ALLOWED_KINDS:
            raise ValueError("kind is not a recognized upstream compatibility role")
        if not _strict_bool(replay_verified, "replay_verified"):
            raise ValueError("upstream certificate was not independently replay-verified")
        if not _strict_bool(exact, "exact"):
            raise ValueError("upstream exact flag must be true")
        if not _strict_bool(complete, "complete"):
            raise ValueError("upstream complete flag must be true")
        if outcome_kind not in _ALLOWED_OUTCOMES:
            raise ValueError("outcome_kind must preserve exact_empty versus nonempty")
        parent = _strict_int(parent_action_degree, "parent_action_degree")
        child = _strict_int(child_ground_size, "child_ground_size")
        if child >= parent:
            raise ValueError("child_ground_size must certify strict positive shrink")
        reduction = _digest(reduction_identity, "reduction_identity")
        production = _digest(
            production_provenance_identity, "production_provenance_identity"
        )
        construction = _digest(
            construction_cost_binding_identity, "construction_cost_binding_identity"
        )
        upstream = _digest(upstream_identity, "upstream_identity")
        bound = _finite(
            construction_multiplicative_cost_bound,
            "construction_multiplicative_cost_bound",
            minimum=1.0,
        )
        charge = _finite(
            charged_log2_reduction_cost,
            "charged_log2_reduction_cost",
            minimum=0.0,
        )
        if not bound.is_integer():
            raise ValueError("construction cost bound must be an integral power of two")
        bound_int = int(bound)
        if bound_int < 1 or bound_int & (bound_int - 1):
            raise ValueError("construction cost bound must be a power of two")
        exact_charge = float(bound_int.bit_length() - 1)
        if charge != exact_charge:
            raise ValueError(
                "charged_log2_reduction_cost must equal exactly log2 of construction bound"
            )
    except (TypeError, ValueError) as exc:
        return _fail_view(str(kind), str(exc))

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": VIEW_STATUS,
        "kind": kind,
        "replay_verified": True,
        "exact": True,
        "complete": True,
        "outcome_kind": outcome_kind,
        "parent_action_degree": parent,
        "child_ground_size": child,
        "reduction_identity": reduction,
        "production_provenance_identity": production,
        "construction_cost_binding_identity": construction,
        "construction_multiplicative_cost_bound": bound,
        "charged_log2_reduction_cost": charge,
        "upstream_identity": upstream,
    }
    identity = _canonical_hash(payload)
    return RecursiveProductionPostReplayView(
        SCHEMA_VERSION,
        VIEW_STATUS,
        kind,
        True,
        True,
        True,
        outcome_kind,
        parent,
        child,
        reduction,
        production,
        construction,
        bound,
        charge,
        upstream,
        identity,
        "strict normalized view of an independently replay-verified upstream certificate",
    )


def replay_post_replay_view(view: RecursiveProductionPostReplayView) -> bool:
    if not isinstance(view, RecursiveProductionPostReplayView):
        return False
    if view.status != VIEW_STATUS or not view.replay_verified:
        return False
    replay = certify_post_replay_view(
        kind=view.kind,
        replay_verified=view.replay_verified,
        exact=view.exact,
        complete=view.complete,
        outcome_kind=view.outcome_kind,
        parent_action_degree=view.parent_action_degree,
        child_ground_size=view.child_ground_size,
        reduction_identity=view.reduction_identity,
        production_provenance_identity=view.production_provenance_identity,
        construction_cost_binding_identity=view.construction_cost_binding_identity,
        construction_multiplicative_cost_bound=view.construction_multiplicative_cost_bound,
        charged_log2_reduction_cost=view.charged_log2_reduction_cost,
        upstream_identity=view.upstream_identity,
    )
    return bool(
        replay.replay_verified
        and replay == view
        and replay.view_identity == view.view_identity
    )


def certify_recursive_production_post_replay_envelope(
    production_cost_provenance: RecursiveProductionPostReplayView,
    provenance_total_cost: RecursiveProductionPostReplayView,
) -> RecursiveProductionPostReplayEnvelope:
    """Bind rev720/rev900-compatible post-replay views without redoing their proofs."""
    if not replay_post_replay_view(production_cost_provenance):
        return _fail_envelope("production-cost provenance normalized view replay failed")
    if not replay_post_replay_view(provenance_total_cost):
        return _fail_envelope("provenance/total-cost normalized view replay failed")
    if production_cost_provenance.kind != "production_cost_provenance":
        return _fail_envelope("first view must have production_cost_provenance role")
    if provenance_total_cost.kind != "provenance_total_cost":
        return _fail_envelope("second view must have provenance_total_cost role")

    shared_fields = (
        "outcome_kind",
        "parent_action_degree",
        "child_ground_size",
        "reduction_identity",
        "production_provenance_identity",
        "construction_cost_binding_identity",
        "construction_multiplicative_cost_bound",
        "charged_log2_reduction_cost",
    )
    for field in shared_fields:
        if getattr(production_cost_provenance, field) != getattr(
            provenance_total_cost, field
        ):
            return _fail_envelope(f"upstream compatibility mismatch at {field}")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": ENVELOPE_STATUS,
        "outcome_kind": production_cost_provenance.outcome_kind,
        "parent_action_degree": production_cost_provenance.parent_action_degree,
        "child_ground_size": production_cost_provenance.child_ground_size,
        "reduction_identity": production_cost_provenance.reduction_identity,
        "production_provenance_identity": (
            production_cost_provenance.production_provenance_identity
        ),
        "construction_cost_binding_identity": (
            production_cost_provenance.construction_cost_binding_identity
        ),
        "construction_multiplicative_cost_bound": (
            production_cost_provenance.construction_multiplicative_cost_bound
        ),
        "charged_log2_reduction_cost": (
            production_cost_provenance.charged_log2_reduction_cost
        ),
        "production_cost_provenance_identity": (
            production_cost_provenance.upstream_identity
        ),
        "provenance_total_cost_identity": provenance_total_cost.upstream_identity,
        "production_cost_provenance_view_identity": (
            production_cost_provenance.view_identity
        ),
        "provenance_total_cost_view_identity": provenance_total_cost.view_identity,
    }
    identity = _canonical_hash(payload)
    return RecursiveProductionPostReplayEnvelope(
        SCHEMA_VERSION,
        ENVELOPE_STATUS,
        True,
        True,
        True,
        production_cost_provenance.outcome_kind,
        production_cost_provenance.parent_action_degree,
        production_cost_provenance.child_ground_size,
        production_cost_provenance.reduction_identity,
        production_cost_provenance.production_provenance_identity,
        production_cost_provenance.construction_cost_binding_identity,
        production_cost_provenance.construction_multiplicative_cost_bound,
        production_cost_provenance.charged_log2_reduction_cost,
        production_cost_provenance.upstream_identity,
        provenance_total_cost.upstream_identity,
        identity,
        "replay-verified production-cost provenance and provenance/total-cost views agree on one exact recursive reduction/cost tuple",
    )


def replay_recursive_production_post_replay_envelope(
    envelope: RecursiveProductionPostReplayEnvelope,
    production_cost_provenance: RecursiveProductionPostReplayView,
    provenance_total_cost: RecursiveProductionPostReplayView,
) -> bool:
    if not isinstance(envelope, RecursiveProductionPostReplayEnvelope):
        return False
    if envelope.status != ENVELOPE_STATUS or not envelope.certified:
        return False
    replay = certify_recursive_production_post_replay_envelope(
        production_cost_provenance, provenance_total_cost
    )
    return bool(
        replay.certified
        and replay == envelope
        and replay.envelope_identity == envelope.envelope_identity
    )


__all__ = [
    "RecursiveProductionPostReplayView",
    "RecursiveProductionPostReplayEnvelope",
    "certify_post_replay_view",
    "replay_post_replay_view",
    "certify_recursive_production_post_replay_envelope",
    "replay_recursive_production_post_replay_envelope",
]
