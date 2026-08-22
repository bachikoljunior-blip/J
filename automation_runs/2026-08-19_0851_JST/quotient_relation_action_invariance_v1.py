from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Mapping

from homogeneous_block_action_provenance_v1 import (
    BlockActionProvenance,
    replay_group_block_action_equivariance,
)


SCHEMA_VERSION = 1
STATUS_EXACT = "exact_quotient_relation_action_invariance"
STATUS_FAIL = "fail_closed_quotient_relation_action_invariance"


class QuotientRelationActionInvariantError(ValueError):
    pass


@dataclass(frozen=True)
class QuotientRelationActionInvariantCertificate:
    schema_version: int
    status: str
    exact: bool
    complete: bool
    block_count: int
    block_bijection: tuple[int, ...]
    source_unary_relations: tuple[tuple[str, tuple[int, ...]], ...]
    target_unary_relations: tuple[tuple[str, tuple[int, ...]], ...]
    source_binary_relations: tuple[tuple[str, tuple[tuple[int, int], ...]], ...]
    target_binary_relations: tuple[tuple[str, tuple[tuple[int, int], ...]], ...]
    source_quotient_generators: tuple[tuple[int, ...], ...]
    target_quotient_generators: tuple[tuple[int, ...], ...]
    block_action_digest: str
    certificate_digest: str
    reason: str


def _fail(reason: str) -> QuotientRelationActionInvariantCertificate:
    return QuotientRelationActionInvariantCertificate(
        SCHEMA_VERSION,
        STATUS_FAIL,
        False,
        False,
        0,
        (),
        (),
        (),
        (),
        (),
        (),
        (),
        "",
        "",
        reason,
    )


def _relation_items(raw, field: str):
    if not isinstance(raw, Mapping):
        raise QuotientRelationActionInvariantError(f"{field} must be a mapping from names to relations")
    items = []
    for name, value in raw.items():
        if not isinstance(name, str) or not name.strip():
            raise QuotientRelationActionInvariantError(f"{field} contains an empty/non-string relation name")
        items.append((name, value))
    items.sort(key=lambda item: item[0])
    return items


def _normalize_unary(raw, degree: int, field: str):
    normalized = []
    for name, values in _relation_items(raw, field):
        try:
            points = tuple(int(x) for x in values)
        except (TypeError, ValueError) as exc:
            raise QuotientRelationActionInvariantError(
                f"{field}[{name!r}] is not an iterable of integer quotient points"
            ) from exc
        if len(set(points)) != len(points):
            raise QuotientRelationActionInvariantError(f"{field}[{name!r}] repeats a quotient point")
        if any(x < 0 or x >= degree for x in points):
            raise QuotientRelationActionInvariantError(f"{field}[{name!r}] contains an out-of-range quotient point")
        normalized.append((name, tuple(sorted(points))))
    return tuple(normalized)


def _normalize_binary(raw, degree: int, field: str):
    normalized = []
    for name, values in _relation_items(raw, field):
        pairs = []
        try:
            for value in values:
                pair = tuple(value)
                if len(pair) != 2:
                    raise QuotientRelationActionInvariantError(
                        f"{field}[{name!r}] contains a non-pair"
                    )
                left, right = int(pair[0]), int(pair[1])
                if left < 0 or left >= degree or right < 0 or right >= degree:
                    raise QuotientRelationActionInvariantError(
                        f"{field}[{name!r}] contains an out-of-range quotient pair"
                    )
                pairs.append((left, right))
        except QuotientRelationActionInvariantError:
            raise
        except (TypeError, ValueError) as exc:
            raise QuotientRelationActionInvariantError(
                f"{field}[{name!r}] is not an iterable of integer quotient pairs"
            ) from exc
        if len(set(pairs)) != len(pairs):
            raise QuotientRelationActionInvariantError(f"{field}[{name!r}] repeats a quotient pair")
        normalized.append((name, tuple(sorted(pairs))))
    return tuple(normalized)


def _as_dict(relations):
    return {name: value for name, value in relations}


def _check_same_names(source, target, kind: str):
    source_names = tuple(name for name, _ in source)
    target_names = tuple(name for name, _ in target)
    if source_names != target_names:
        raise QuotientRelationActionInvariantError(
            f"source/target {kind} relation names differ"
        )


def _check_generator_invariance(unary, binary, generators, side: str):
    unary_map = _as_dict(unary)
    binary_map = _as_dict(binary)
    for generator_index, generator in enumerate(generators):
        for name, points in unary_map.items():
            transported = tuple(sorted(generator[point] for point in points))
            if transported != points:
                raise QuotientRelationActionInvariantError(
                    f"{side} quotient generator {generator_index} does not stabilize unary relation {name!r}"
                )
        for name, pairs in binary_map.items():
            transported = tuple(
                sorted((generator[left], generator[right]) for left, right in pairs)
            )
            if transported != pairs:
                raise QuotientRelationActionInvariantError(
                    f"{side} quotient generator {generator_index} does not stabilize binary relation {name!r}"
                )


def _check_transport(source_unary, target_unary, source_binary, target_binary, block_bijection):
    target_unary_map = _as_dict(target_unary)
    for name, points in source_unary:
        transported = tuple(sorted(block_bijection[point] for point in points))
        if transported != target_unary_map[name]:
            raise QuotientRelationActionInvariantError(
                f"block bijection does not transport unary relation {name!r} exactly"
            )
    target_binary_map = _as_dict(target_binary)
    for name, pairs in source_binary:
        transported = tuple(
            sorted((block_bijection[left], block_bijection[right]) for left, right in pairs)
        )
        if transported != target_binary_map[name]:
            raise QuotientRelationActionInvariantError(
                f"block bijection does not transport binary relation {name!r} exactly"
            )


def _payload(**kwargs):
    return {"schema_version": SCHEMA_VERSION, "status": STATUS_EXACT, **kwargs}


def _digest(payload) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def certify_quotient_relation_action_invariance(
    block_action: BlockActionProvenance,
    source_unary_relations: Mapping[str, Iterable[int]],
    target_unary_relations: Mapping[str, Iterable[int]],
    source_binary_relations: Mapping[str, Iterable[tuple[int, int]]],
    target_binary_relations: Mapping[str, Iterable[tuple[int, int]]],
) -> QuotientRelationActionInvariantCertificate:
    """Certify exact quotient relation transport under an exact rev274 block action.

    This verifier does not discover blocks or solve quotient String Isomorphism.
    It consumes a replay-valid rev274 block-action certificate and proves that the
    supplied named unary/binary quotient relations are genuine invariants of the
    corresponding induced quotient groups and that the already-certified block
    bijection transports every relation exactly.
    """
    try:
        if not isinstance(block_action, BlockActionProvenance):
            raise QuotientRelationActionInvariantError(
                "block_action must be a rev274 BlockActionProvenance certificate"
            )
        if not replay_group_block_action_equivariance(block_action):
            raise QuotientRelationActionInvariantError(
                "block_action certificate is not exact/replay-valid"
            )
        if not block_action.exact or not block_action.complete:
            raise QuotientRelationActionInvariantError(
                "block_action certificate is not exact and complete"
            )
        degree = int(block_action.block_count)
        block_bijection = tuple(int(x) for x in block_action.block_bijection)
        if degree <= 0 or len(block_bijection) != degree or set(block_bijection) != set(range(degree)):
            raise QuotientRelationActionInvariantError(
                "rev274 block action carries an invalid quotient block bijection"
            )

        source_unary = _normalize_unary(source_unary_relations, degree, "source_unary_relations")
        target_unary = _normalize_unary(target_unary_relations, degree, "target_unary_relations")
        source_binary = _normalize_binary(source_binary_relations, degree, "source_binary_relations")
        target_binary = _normalize_binary(target_binary_relations, degree, "target_binary_relations")
        if not source_unary and not source_binary:
            raise QuotientRelationActionInvariantError(
                "at least one quotient unary or binary relation is required"
            )
        _check_same_names(source_unary, target_unary, "unary")
        _check_same_names(source_binary, target_binary, "binary")

        source_generators = tuple(tuple(g) for g in block_action.source_quotient_generators)
        target_generators = tuple(tuple(g) for g in block_action.target_quotient_generators)
        _check_generator_invariance(
            source_unary, source_binary, source_generators, "source"
        )
        _check_generator_invariance(
            target_unary, target_binary, target_generators, "target"
        )
        _check_transport(
            source_unary,
            target_unary,
            source_binary,
            target_binary,
            block_bijection,
        )

        payload = _payload(
            block_count=degree,
            block_bijection=block_bijection,
            source_unary_relations=source_unary,
            target_unary_relations=target_unary,
            source_binary_relations=source_binary,
            target_binary_relations=target_binary,
            source_quotient_generators=source_generators,
            target_quotient_generators=target_generators,
            block_action_digest=block_action.certificate_digest,
        )
        return QuotientRelationActionInvariantCertificate(
            **payload,
            exact=True,
            complete=True,
            certificate_digest=_digest(payload),
            reason=(
                "the rev274 block action replays exactly; every supplied quotient relation is "
                "invariant under its induced quotient generators and the certified block "
                "bijection transports every named relation exactly"
            ),
        )
    except (QuotientRelationActionInvariantError, TypeError, ValueError) as exc:
        return _fail(str(exc))


def replay_quotient_relation_action_invariance(
    certificate: QuotientRelationActionInvariantCertificate,
    block_action: BlockActionProvenance,
) -> bool:
    if not isinstance(certificate, QuotientRelationActionInvariantCertificate):
        return False
    if (
        certificate.schema_version != SCHEMA_VERSION
        or certificate.status != STATUS_EXACT
        or not certificate.exact
        or not certificate.complete
    ):
        return False
    if not isinstance(block_action, BlockActionProvenance):
        return False
    if certificate.block_action_digest != block_action.certificate_digest:
        return False
    replay = certify_quotient_relation_action_invariance(
        block_action,
        dict(certificate.source_unary_relations),
        dict(certificate.target_unary_relations),
        dict(certificate.source_binary_relations),
        dict(certificate.target_binary_relations),
    )
    return replay == certificate and replay.certificate_digest == certificate.certificate_digest


__all__ = [
    "QuotientRelationActionInvariantCertificate",
    "QuotientRelationActionInvariantError",
    "SCHEMA_VERSION",
    "STATUS_EXACT",
    "STATUS_FAIL",
    "certify_quotient_relation_action_invariance",
    "replay_quotient_relation_action_invariance",
]
