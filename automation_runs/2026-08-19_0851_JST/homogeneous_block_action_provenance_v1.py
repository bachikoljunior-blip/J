from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Sequence

SCHEMA_VERSION = 1
STATUS_EXACT = "exact_group_block_action_equivariance"
STATUS_FAIL = "fail_closed_block_action_provenance"


class BlockActionProvenanceError(ValueError):
    pass


@dataclass(frozen=True)
class BlockActionProvenance:
    schema_version: int
    status: str
    exact: bool
    complete: bool
    domain_degree: int
    block_count: int
    block_size: int
    source_blocks: tuple[tuple[int, ...], ...]
    target_blocks: tuple[tuple[int, ...], ...]
    block_bijection: tuple[int, ...]
    source_generators: tuple[tuple[int, ...], ...]
    target_generators: tuple[tuple[int, ...], ...]
    source_quotient_generators: tuple[tuple[int, ...], ...]
    target_quotient_generators: tuple[tuple[int, ...], ...]
    certificate_digest: str
    reason: str


def _fail(reason: str) -> BlockActionProvenance:
    return BlockActionProvenance(
        SCHEMA_VERSION, STATUS_FAIL, False, False, 0, 0, 0, (), (), (), (), (), (), (), "", reason
    )


def _normalize_partition(raw_blocks: Iterable[Iterable[int]], side: str):
    try:
        raw = tuple(tuple(int(x) for x in block) for block in raw_blocks)
    except (TypeError, ValueError) as exc:
        raise BlockActionProvenanceError(f"{side} partition is not an integer block family") from exc
    if not raw:
        raise BlockActionProvenanceError(f"{side} partition must contain at least one block")
    if any(not block for block in raw):
        raise BlockActionProvenanceError(f"{side} partition contains an empty block")
    if any(len(set(block)) != len(block) for block in raw):
        raise BlockActionProvenanceError(f"{side} partition repeats a point within a block")
    normalized_raw = tuple(tuple(sorted(block)) for block in raw)
    flat = tuple(x for block in normalized_raw for x in block)
    if any(x < 0 for x in flat):
        raise BlockActionProvenanceError(f"{side} partition contains a negative point")
    if len(set(flat)) != len(flat):
        raise BlockActionProvenanceError(f"{side} partition blocks overlap")
    degree = len(flat)
    if set(flat) != set(range(degree)):
        raise BlockActionProvenanceError(f"{side} partition must cover exactly points 0..{degree - 1}")
    sizes = {len(block) for block in normalized_raw}
    if len(sizes) != 1:
        raise BlockActionProvenanceError(f"{side} partition must have uniform block size")
    order = tuple(sorted(range(len(normalized_raw)), key=lambda i: normalized_raw[i]))
    canonical = tuple(normalized_raw[i] for i in order)
    raw_to_canonical = {raw_index: canon_index for canon_index, raw_index in enumerate(order)}
    return canonical, raw_to_canonical, degree, next(iter(sizes))


def _normalize_permutation(value: Sequence[int], degree: int, field: str) -> tuple[int, ...]:
    try:
        perm = tuple(int(x) for x in value)
    except (TypeError, ValueError) as exc:
        raise BlockActionProvenanceError(f"{field} must be an integer permutation") from exc
    if len(perm) != degree or set(perm) != set(range(degree)):
        raise BlockActionProvenanceError(f"{field} must be a bijection of 0..{degree - 1}")
    return perm


def _induced_quotient(blocks, generators, side):
    point_to_block = {point: i for i, block in enumerate(blocks) for point in block}
    quotient = []
    for gen_index, generator in enumerate(generators):
        induced = []
        for block_index, block in enumerate(blocks):
            image_blocks = {point_to_block[generator[point]] for point in block}
            if len(image_blocks) != 1:
                raise BlockActionProvenanceError(
                    f"{side} generator {gen_index} does not map block {block_index} into one block"
                )
            target_block = next(iter(image_blocks))
            image_points = {generator[point] for point in block}
            if image_points != set(blocks[target_block]):
                raise BlockActionProvenanceError(
                    f"{side} generator {gen_index} does not map block {block_index} onto a full block"
                )
            induced.append(target_block)
        induced = tuple(induced)
        if set(induced) != set(range(len(blocks))):
            raise BlockActionProvenanceError(f"{side} generator {gen_index} does not induce a block permutation")
        quotient.append(induced)
    return tuple(quotient)


def _payload(**kwargs):
    return {"schema_version": SCHEMA_VERSION, "status": STATUS_EXACT, **kwargs}


def _digest(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def certify_group_block_action_equivariance(
    source_blocks: Iterable[Iterable[int]],
    target_blocks: Iterable[Iterable[int]],
    block_bijection: Sequence[int],
    source_generators: Iterable[Sequence[int]],
    target_generators: Iterable[Sequence[int]],
) -> BlockActionProvenance:
    try:
        sb, sraw, sd, ss = _normalize_partition(source_blocks, "source")
        tb, traw, td, ts = _normalize_partition(target_blocks, "target")
        if sd != td:
            raise BlockActionProvenanceError("source and target domain degrees differ")
        if len(sb) != len(tb):
            raise BlockActionProvenanceError("source and target block counts differ")
        if ss != ts:
            raise BlockActionProvenanceError("source and target block sizes differ")
        m = len(sb)
        raw_bij = tuple(int(x) for x in block_bijection)
        if len(raw_bij) != m or set(raw_bij) != set(range(m)):
            raise BlockActionProvenanceError("block_bijection must be a permutation of target raw block indices")
        canonical_bij = [None] * m
        for rs, rt in enumerate(raw_bij):
            canonical_bij[sraw[rs]] = traw[rt]
        canonical_bij = tuple(int(x) for x in canonical_bij)
        sg = tuple(_normalize_permutation(g, sd, f"source generator {i}") for i, g in enumerate(source_generators))
        tg = tuple(_normalize_permutation(g, td, f"target generator {i}") for i, g in enumerate(target_generators))
        if len(sg) != len(tg):
            raise BlockActionProvenanceError("source and target generator lists must be paired one-to-one")
        sq = _induced_quotient(sb, sg, "source")
        tq = _induced_quotient(tb, tg, "target")
        for gi, (sqi, tqi) in enumerate(zip(sq, tq)):
            for i in range(m):
                if canonical_bij[sqi[i]] != tqi[canonical_bij[i]]:
                    raise BlockActionProvenanceError(
                        f"block bijection does not intertwine paired quotient generator {gi} at source block {i}"
                    )
        payload = _payload(
            domain_degree=sd,
            block_count=m,
            block_size=ss,
            source_blocks=sb,
            target_blocks=tb,
            block_bijection=canonical_bij,
            source_generators=sg,
            target_generators=tg,
            source_quotient_generators=sq,
            target_quotient_generators=tq,
        )
        return BlockActionProvenance(
            **payload,
            exact=True,
            complete=True,
            certificate_digest=_digest(payload),
            reason="both supplied partitions are exact block systems for the supplied generator groups and the supplied block bijection intertwines every paired induced quotient generator",
        )
    except (BlockActionProvenanceError, TypeError, ValueError) as exc:
        return _fail(str(exc))


def replay_group_block_action_equivariance(certificate: BlockActionProvenance) -> bool:
    if not isinstance(certificate, BlockActionProvenance):
        return False
    if certificate.schema_version != SCHEMA_VERSION or certificate.status != STATUS_EXACT or not certificate.exact or not certificate.complete:
        return False
    replay = certify_group_block_action_equivariance(
        certificate.source_blocks,
        certificate.target_blocks,
        certificate.block_bijection,
        certificate.source_generators,
        certificate.target_generators,
    )
    return replay == certificate and replay.certificate_digest == certificate.certificate_digest


__all__ = [
    "BlockActionProvenance",
    "BlockActionProvenanceError",
    "SCHEMA_VERSION",
    "STATUS_EXACT",
    "STATUS_FAIL",
    "certify_group_block_action_equivariance",
    "replay_group_block_action_equivariance",
]
