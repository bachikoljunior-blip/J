from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import isfinite
from numbers import Integral, Real
from pathlib import Path
import sys
from typing import Iterable

_LEGACY_DIR = Path(__file__).resolve().parents[1] / "2026-08-19_0851_JST"
if str(_LEGACY_DIR) not in sys.path:
    sys.path.insert(0, str(_LEGACY_DIR))

from relation_twin_restriction_provenance_v1 import (  # noqa: E402
    PairedRelationTwinRestriction,
    RelationTwinRestriction,
    certify_paired_relation_twin_restriction,
)


_SUCCESS_STATUS = "paired_relation_twin_restriction"


@dataclass(frozen=True)
class RelationTwinRestrictionReplayIdentity:
    schema: str
    solver_identity: tuple[str, str, int]
    left_size: int
    right_size: int
    source_edges: tuple[tuple[int, int], ...]
    target_edges: tuple[tuple[int, int], ...]
    alpha_hex: str
    max_subsets: int
    outcome_snapshot: tuple
    payload_digest: str
    replay_stable: bool


@dataclass(frozen=True)
class RelationTwinRestrictionReplayValidation:
    status: str
    certified: bool
    reason: str


@dataclass(frozen=True)
class RelationTwinRestrictionReplayResult:
    status: str
    result: PairedRelationTwinRestriction
    identity: RelationTwinRestrictionReplayIdentity | None
    validation: RelationTwinRestrictionReplayValidation | None
    reason: str


def _strict_int(value, *, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be a strict integer")
    normalized = int(value)
    if normalized < minimum:
        raise ValueError(f"{name} is below its minimum")
    return normalized


def _strict_alpha(value) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("alpha must be a finite real number")
    normalized = float(value)
    if not isfinite(normalized) or not 2.0 / 3.0 <= normalized < 1.0:
        raise ValueError("alpha must lie in [2/3,1)")
    return normalized


def _normalize_edges(
    edges: Iterable[tuple[int, int]], *, left_size: int, right_size: int
) -> tuple[tuple[int, int], ...]:
    normalized: set[tuple[int, int]] = set()
    for edge in edges:
        try:
            a, b = edge
        except (TypeError, ValueError) as exc:
            raise ValueError("every edge must contain exactly two endpoints") from exc
        if isinstance(a, bool) or not isinstance(a, Integral):
            raise ValueError("left edge endpoints must be strict integers")
        if isinstance(b, bool) or not isinstance(b, Integral):
            raise ValueError("right edge endpoints must be strict integers")
        a = int(a)
        b = int(b)
        if not 0 <= a < left_size or not 0 <= b < right_size:
            raise ValueError("edge endpoint outside the declared bipartite parts")
        normalized.add((a, b))
    return tuple(sorted(normalized))


def _restriction_snapshot(cert) -> tuple | None:
    if cert is None:
        return None
    defect = cert.selected_relative_symmetry_defect
    return (
        str(cert.status),
        int(cert.left_size),
        int(cert.right_size),
        float(cert.alpha).hex(),
        tuple(tuple(int(x) for x in cell) for cell in cert.full_left_twin_classes),
        tuple(int(x) for x in cert.part0),
        tuple(int(x) for x in cert.part1),
        tuple(tuple(int(x) for x in cell) for cell in cert.part0_left_twin_classes),
        tuple(tuple(int(x) for x in cell) for cell in cert.part1_left_twin_classes),
        int(cert.part0_largest_left_twin_class),
        int(cert.part1_largest_left_twin_class),
        bool(cert.part0_exercise55_gate),
        bool(cert.part1_exercise55_gate),
        None if cert.selected_part_index is None else int(cert.selected_part_index),
        tuple(int(x) for x in cert.selected_part),
        None
        if cert.selected_largest_left_twin_class is None
        else int(cert.selected_largest_left_twin_class),
        None if defect is None else float(defect).hex(),
        bool(cert.selected_alpha_shrink),
        bool(cert.theorem_gate_verified),
        bool(cert.exact),
    )


def _side_snapshot(side: RelationTwinRestriction) -> tuple:
    relation = side.relation
    return (
        str(side.status),
        (
            str(relation.status),
            int(relation.left_size),
            int(relation.right_size),
            None
            if relation.original_common_degree is None
            else int(relation.original_common_degree),
            None if relation.normalized_degree is None else int(relation.normalized_degree),
            bool(relation.complemented),
            tuple(tuple(int(x) for x in neighborhood) for neighborhood in relation.neighborhoods),
            None if relation.relation_arity is None else int(relation.relation_arity),
            tuple((int(color), int(count)) for color, count in relation.relation_inventory),
            bool(relation.exact),
        ),
        tuple(tuple(int(x) for x in cell) for cell in side.twin_classes),
        tuple(int(x) for x in side.twin_class_size_inventory),
        tuple(int(x) for x in side.large_twin_class),
        tuple(int(x) for x in side.complement),
        _restriction_snapshot(side.restriction),
        None if side.selected_part_index is None else int(side.selected_part_index),
        tuple(int(x) for x in side.selected_part),
        bool(side.provenance_verified),
        bool(side.exact),
    )


def _outcome_snapshot(result: PairedRelationTwinRestriction) -> tuple:
    return (
        str(result.status),
        _side_snapshot(result.source),
        _side_snapshot(result.target),
        None
        if result.selected_large_class_size is None
        else int(result.selected_large_class_size),
        bool(result.restriction_pair_complete),
        bool(result.provenance_verified),
        bool(result.exact),
    )


def _digest_payload(
    *,
    left_size: int,
    right_size: int,
    source_edges: tuple[tuple[int, int], ...],
    target_edges: tuple[tuple[int, int], ...],
    alpha_hex: str,
    max_subsets: int,
    outcome_snapshot: tuple,
) -> str:
    payload = {
        "schema": "relation-twin-restriction-replay-identity-v1",
        "solver_identity": [
            "relation_twin_restriction_provenance_v1",
            "bipartite_reduce_part2_by_color_v1",
            2501,
        ],
        "left_size": left_size,
        "right_size": right_size,
        "source_edges": source_edges,
        "target_edges": target_edges,
        "alpha_hex": alpha_hex,
        "max_subsets": max_subsets,
        "outcome_snapshot": outcome_snapshot,
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _successful_exact_result(result: PairedRelationTwinRestriction) -> bool:
    return bool(
        result.status == _SUCCESS_STATUS
        and result.exact
        and result.provenance_verified
        and result.restriction_pair_complete
        and result.source.status == "certified_relation_twin_restriction"
        and result.target.status == "certified_relation_twin_restriction"
        and result.source.exact
        and result.target.exact
        and result.source.provenance_verified
        and result.target.provenance_verified
        and result.source.restriction is not None
        and result.target.restriction is not None
        and result.source.restriction.exact
        and result.target.restriction.exact
        and result.source.restriction.theorem_gate_verified
        and result.target.restriction.theorem_gate_verified
    )


def build_relation_twin_restriction_replay_identity(
    left_size,
    right_size,
    source_edges,
    target_edges,
    result: PairedRelationTwinRestriction,
    *,
    alpha: float = 0.75,
    max_subsets: int = 200000,
) -> RelationTwinRestrictionReplayIdentity:
    left_size = _strict_int(left_size, name="left_size", minimum=2)
    right_size = _strict_int(right_size, name="right_size", minimum=3)
    alpha = _strict_alpha(alpha)
    max_subsets = _strict_int(max_subsets, name="max_subsets", minimum=1)
    source_edges = _normalize_edges(
        source_edges, left_size=left_size, right_size=right_size
    )
    target_edges = _normalize_edges(
        target_edges, left_size=left_size, right_size=right_size
    )
    if not isinstance(result, PairedRelationTwinRestriction):
        raise ValueError("result must be a PairedRelationTwinRestriction")
    if not _successful_exact_result(result):
        raise ValueError("only the complete exact paired rev203 restriction may receive an identity")

    snapshot = _outcome_snapshot(result)
    alpha_hex = alpha.hex()
    digest = _digest_payload(
        left_size=left_size,
        right_size=right_size,
        source_edges=source_edges,
        target_edges=target_edges,
        alpha_hex=alpha_hex,
        max_subsets=max_subsets,
        outcome_snapshot=snapshot,
    )
    return RelationTwinRestrictionReplayIdentity(
        "relation-twin-restriction-replay-identity-v1",
        (
            "relation_twin_restriction_provenance_v1",
            "bipartite_reduce_part2_by_color_v1",
            2501,
        ),
        left_size,
        right_size,
        source_edges,
        target_edges,
        alpha_hex,
        max_subsets,
        snapshot,
        digest,
        True,
    )


def validate_relation_twin_restriction_replay_identity(
    left_size,
    right_size,
    source_edges,
    target_edges,
    result: PairedRelationTwinRestriction,
    identity: RelationTwinRestrictionReplayIdentity,
    *,
    alpha: float = 0.75,
    max_subsets: int = 200000,
) -> RelationTwinRestrictionReplayValidation:
    try:
        left_size = _strict_int(left_size, name="left_size", minimum=2)
        right_size = _strict_int(right_size, name="right_size", minimum=3)
        alpha = _strict_alpha(alpha)
        max_subsets = _strict_int(max_subsets, name="max_subsets", minimum=1)
        source_edges = _normalize_edges(
            source_edges, left_size=left_size, right_size=right_size
        )
        target_edges = _normalize_edges(
            target_edges, left_size=left_size, right_size=right_size
        )
    except ValueError as exc:
        return RelationTwinRestrictionReplayValidation(
            "invalid_relation_twin_replay_input", False, str(exc)
        )

    if not isinstance(identity, RelationTwinRestrictionReplayIdentity):
        return RelationTwinRestrictionReplayValidation(
            "wrong_relation_twin_replay_identity_type",
            False,
            "the supplied identity is not RelationTwinRestrictionReplayIdentity v1",
        )
    if (
        identity.schema != "relation-twin-restriction-replay-identity-v1"
        or identity.solver_identity
        != (
            "relation_twin_restriction_provenance_v1",
            "bipartite_reduce_part2_by_color_v1",
            2501,
        )
        or not identity.replay_stable
    ):
        return RelationTwinRestrictionReplayValidation(
            "invalid_relation_twin_replay_identity_schema",
            False,
            "the identity schema, solver version, or replay-stability bit is invalid",
        )
    if not isinstance(result, PairedRelationTwinRestriction) or not _successful_exact_result(result):
        return RelationTwinRestrictionReplayValidation(
            "nonexact_relation_twin_replay_result",
            False,
            "only the complete exact paired rev203 restriction may be replay-certified",
        )

    if (
        identity.left_size != left_size
        or identity.right_size != right_size
        or identity.source_edges != source_edges
        or identity.target_edges != target_edges
        or identity.alpha_hex != alpha.hex()
        or identity.max_subsets != max_subsets
    ):
        return RelationTwinRestrictionReplayValidation(
            "relation_twin_replay_input_or_resource_drift",
            False,
            "the current bipartite inputs or resource parameters differ from the frozen identity",
        )

    replay = certify_paired_relation_twin_restriction(
        left_size,
        right_size,
        source_edges,
        target_edges,
        alpha=alpha,
        max_subsets=max_subsets,
    )
    if not _successful_exact_result(replay):
        return RelationTwinRestrictionReplayValidation(
            "relation_twin_replay_no_longer_exact",
            False,
            "independent rev203 replay no longer returns the complete exact paired restriction",
        )
    if _outcome_snapshot(result) != _outcome_snapshot(replay):
        return RelationTwinRestrictionReplayValidation(
            "relation_twin_replay_result_drift",
            False,
            "the supplied exact result differs structurally from independent rev203 replay",
        )

    expected = build_relation_twin_restriction_replay_identity(
        left_size,
        right_size,
        source_edges,
        target_edges,
        replay,
        alpha=alpha,
        max_subsets=max_subsets,
    )
    if identity.payload_digest != expected.payload_digest:
        return RelationTwinRestrictionReplayValidation(
            "relation_twin_replay_digest_mismatch",
            False,
            "the SHA-256 payload digest does not match the independently rebuilt identity",
        )
    if identity != expected:
        return RelationTwinRestrictionReplayValidation(
            "relation_twin_replay_identity_mismatch",
            False,
            "the frozen identity differs from the independently rebuilt replay identity",
        )
    return RelationTwinRestrictionReplayValidation(
        "verified_relation_twin_restriction_replay_identity",
        True,
        "the paired rev203 restriction, rev200 selection invariants, inputs, and resource gates replay exactly under one immutable SHA-256 identity",
    )


def certify_relation_twin_restriction_replay_identity(
    left_size,
    right_size,
    source_edges,
    target_edges,
    *,
    alpha: float = 0.75,
    max_subsets: int = 200000,
) -> RelationTwinRestrictionReplayResult:
    left_size = _strict_int(left_size, name="left_size", minimum=2)
    right_size = _strict_int(right_size, name="right_size", minimum=3)
    alpha = _strict_alpha(alpha)
    max_subsets = _strict_int(max_subsets, name="max_subsets", minimum=1)
    source_edges = _normalize_edges(
        source_edges, left_size=left_size, right_size=right_size
    )
    target_edges = _normalize_edges(
        target_edges, left_size=left_size, right_size=right_size
    )

    result = certify_paired_relation_twin_restriction(
        left_size,
        right_size,
        source_edges,
        target_edges,
        alpha=alpha,
        max_subsets=max_subsets,
    )
    if not _successful_exact_result(result):
        return RelationTwinRestrictionReplayResult(
            "underlying_relation_twin_restriction_not_complete",
            result,
            None,
            None,
            "rev203 did not produce the unique complete exact paired proper restriction required by this replay-identity child",
        )

    identity = build_relation_twin_restriction_replay_identity(
        left_size,
        right_size,
        source_edges,
        target_edges,
        result,
        alpha=alpha,
        max_subsets=max_subsets,
    )
    validation = validate_relation_twin_restriction_replay_identity(
        left_size,
        right_size,
        source_edges,
        target_edges,
        result,
        identity,
        alpha=alpha,
        max_subsets=max_subsets,
    )
    if not validation.certified:
        return RelationTwinRestrictionReplayResult(
            validation.status, result, identity, validation, validation.reason
        )
    return RelationTwinRestrictionReplayResult(
        "certified_relation_twin_restriction_replay_identity",
        result,
        identity,
        validation,
        "the main-integrated rev203 paired relation-twin restriction is independently replayed and bound to a deterministic immutable structural identity; no parent String Isomorphism exactness is promoted",
    )


__all__ = [
    "RelationTwinRestrictionReplayIdentity",
    "RelationTwinRestrictionReplayValidation",
    "RelationTwinRestrictionReplayResult",
    "build_relation_twin_restriction_replay_identity",
    "validate_relation_twin_restriction_replay_identity",
    "certify_relation_twin_restriction_replay_identity",
]
