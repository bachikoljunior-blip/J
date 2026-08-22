"""Exact provenance verifier for homogeneous unary/binary block quotients.

This module is deliberately standalone. It does not discover a block system;
it verifies a supplied partition and a supplied block transport, failing closed
unless every named relation is constant on each relevant block fibre.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

PointTuple = tuple[int, ...]


@dataclass(frozen=True)
class NamedRelation:
    name: str
    arity: int
    tuples: frozenset[PointTuple]


@dataclass(frozen=True)
class RelationStructure:
    domain_size: int
    relations: tuple[NamedRelation, ...]


@dataclass(frozen=True)
class QuotientRelation:
    name: str
    arity: int
    tuples: frozenset[PointTuple]


@dataclass(frozen=True)
class QuotientStructure:
    block_count: int
    block_sizes: tuple[int, ...]
    relations: tuple[QuotientRelation, ...]


@dataclass(frozen=True)
class HomogeneousBlockTransportCertificate:
    source_partition: tuple[tuple[int, ...], ...]
    target_partition: tuple[tuple[int, ...], ...]
    block_map: tuple[int, ...]
    point_map: tuple[int, ...]
    source_quotient: QuotientStructure
    target_quotient: QuotientStructure


@dataclass(frozen=True)
class BlockProvenanceResult:
    exact: bool
    reason: str
    certificate: HomogeneousBlockTransportCertificate | None = None


def build_structure(
    domain_size: int,
    *,
    unary: Mapping[str, Iterable[int]] | None = None,
    binary: Mapping[str, Iterable[tuple[int, int]]] | None = None,
) -> RelationStructure:
    """Build a canonical explicit unary/binary relation structure."""
    if not isinstance(domain_size, int) or isinstance(domain_size, bool) or domain_size < 0:
        raise ValueError("domain_size must be a nonnegative integer")
    unary = {} if unary is None else unary
    binary = {} if binary is None else binary
    overlap = set(unary) & set(binary)
    if overlap:
        raise ValueError(f"relation name used at two arities: {sorted(overlap)!r}")

    relations: list[NamedRelation] = []
    for arity, mapping in ((1, unary), (2, binary)):
        for name in sorted(mapping):
            if not isinstance(name, str) or not name:
                raise ValueError("relation names must be nonempty strings")
            normalized: set[PointTuple] = set()
            for raw in mapping[name]:
                item = (
                    (raw,)
                    if arity == 1 and isinstance(raw, int) and not isinstance(raw, bool)
                    else tuple(raw)  # type: ignore[arg-type]
                )
                if len(item) != arity:
                    raise ValueError(f"relation {name!r} has a tuple of the wrong arity")
                if any(not isinstance(point, int) or isinstance(point, bool) for point in item):
                    raise ValueError(f"relation {name!r} contains a non-integer point")
                if any(point < 0 or point >= domain_size for point in item):
                    raise ValueError(f"relation {name!r} contains a point outside the domain")
                normalized.add(item)
            relations.append(NamedRelation(name=name, arity=arity, tuples=frozenset(normalized)))
    return RelationStructure(domain_size=domain_size, relations=tuple(relations))


def _normalize_partition(
    domain_size: int, partition: Sequence[Sequence[int]]
) -> tuple[tuple[int, ...], ...]:
    blocks: list[tuple[int, ...]] = []
    seen: set[int] = set()
    for raw_block in partition:
        block = tuple(raw_block)
        if not block:
            raise ValueError("partition blocks must be nonempty")
        if len(set(block)) != len(block):
            raise ValueError("a partition block repeats a point")
        if tuple(sorted(block)) != block:
            raise ValueError("partition blocks must list points in increasing order")
        for point in block:
            if not isinstance(point, int) or isinstance(point, bool):
                raise ValueError("partition points must be integers")
            if point < 0 or point >= domain_size:
                raise ValueError("partition point outside the domain")
            if point in seen:
                raise ValueError("partition blocks overlap")
            seen.add(point)
        blocks.append(block)
    if seen != set(range(domain_size)):
        raise ValueError("partition must cover the domain exactly")
    return tuple(blocks)


def _relation_index(structure: RelationStructure) -> dict[tuple[str, int], frozenset[PointTuple]]:
    return {(rel.name, rel.arity): rel.tuples for rel in structure.relations}


def _quotient_if_homogeneous(
    structure: RelationStructure,
    partition: tuple[tuple[int, ...], ...],
) -> tuple[QuotientStructure | None, str]:
    quotient_relations: list[QuotientRelation] = []
    for relation in structure.relations:
        quotient_tuples: set[PointTuple] = set()
        if relation.arity == 1:
            for i, block in enumerate(partition):
                values = {((point,) in relation.tuples) for point in block}
                if len(values) != 1:
                    return None, f"relation {relation.name!r} is nonuniform on unary block {i}"
                if True in values:
                    quotient_tuples.add((i,))
        elif relation.arity == 2:
            for i, left in enumerate(partition):
                for j, right in enumerate(partition):
                    values = {
                        ((u, v) in relation.tuples)
                        for u in left
                        for v in right
                    }
                    if len(values) != 1:
                        return None, (
                            f"relation {relation.name!r} is nonuniform on binary block pair {(i, j)!r}"
                        )
                    if True in values:
                        quotient_tuples.add((i, j))
        else:
            return None, f"unsupported relation arity {relation.arity}"
        quotient_relations.append(
            QuotientRelation(
                name=relation.name,
                arity=relation.arity,
                tuples=frozenset(quotient_tuples),
            )
        )
    return (
        QuotientStructure(
            block_count=len(partition),
            block_sizes=tuple(len(block) for block in partition),
            relations=tuple(quotient_relations),
        ),
        "ok",
    )


def _transport_tuple(item: PointTuple, mapping: Sequence[int]) -> PointTuple:
    return tuple(mapping[index] for index in item)


def _verify_full_transport(
    source: RelationStructure,
    target: RelationStructure,
    point_map: tuple[int, ...],
) -> bool:
    source_index = _relation_index(source)
    target_index = _relation_index(target)
    if source_index.keys() != target_index.keys():
        return False
    for key, source_tuples in source_index.items():
        transported = frozenset(_transport_tuple(item, point_map) for item in source_tuples)
        if transported != target_index[key]:
            return False
    return True


def certify_homogeneous_block_transport(
    source: RelationStructure,
    target: RelationStructure,
    source_partition: Sequence[Sequence[int]],
    target_partition: Sequence[Sequence[int]],
    block_map: Sequence[int],
) -> BlockProvenanceResult:
    """Certify exact transport through a supplied homogeneous block quotient.

    Exactness requires identical named unary/binary signatures, exact supplied
    partitions, block-constant relation fibres, a size-compatible block
    bijection, exact quotient transport, and an independently checked canonical
    point lift. Any unmet condition returns ``exact=False`` with no certificate.
    """
    try:
        source_blocks = _normalize_partition(source.domain_size, source_partition)
        target_blocks = _normalize_partition(target.domain_size, target_partition)
    except (TypeError, ValueError) as exc:
        return BlockProvenanceResult(False, f"invalid_partition: {exc}")

    source_signature = tuple((rel.name, rel.arity) for rel in source.relations)
    target_signature = tuple((rel.name, rel.arity) for rel in target.relations)
    if source_signature != target_signature:
        return BlockProvenanceResult(False, "relation_signature_mismatch")
    if len(source_blocks) != len(target_blocks):
        return BlockProvenanceResult(False, "block_count_mismatch")

    mapping = tuple(block_map)
    block_count = len(source_blocks)
    if len(mapping) != block_count:
        return BlockProvenanceResult(False, "block_map_length_mismatch")
    if any(not isinstance(item, int) or isinstance(item, bool) for item in mapping):
        return BlockProvenanceResult(False, "block_map_must_contain_integers")
    if sorted(mapping) != list(range(block_count)):
        return BlockProvenanceResult(False, "block_map_not_bijective")
    for source_index, target_index in enumerate(mapping):
        if len(source_blocks[source_index]) != len(target_blocks[target_index]):
            return BlockProvenanceResult(False, "mapped_block_size_mismatch")

    source_quotient, reason = _quotient_if_homogeneous(source, source_blocks)
    if source_quotient is None:
        return BlockProvenanceResult(False, f"source_not_block_homogeneous: {reason}")
    target_quotient, reason = _quotient_if_homogeneous(target, target_blocks)
    if target_quotient is None:
        return BlockProvenanceResult(False, f"target_not_block_homogeneous: {reason}")

    target_q_index = {
        (rel.name, rel.arity): rel.tuples for rel in target_quotient.relations
    }
    for relation in source_quotient.relations:
        transported = frozenset(
            _transport_tuple(item, mapping) for item in relation.tuples
        )
        if transported != target_q_index[(relation.name, relation.arity)]:
            return BlockProvenanceResult(False, "quotient_relation_transport_mismatch")

    point_map_list = [-1] * source.domain_size
    for source_index, target_index in enumerate(mapping):
        for source_point, target_point in zip(
            source_blocks[source_index], target_blocks[target_index], strict=True
        ):
            point_map_list[source_point] = target_point
    point_map = tuple(point_map_list)
    if sorted(point_map) != list(range(target.domain_size)):
        return BlockProvenanceResult(False, "canonical_point_lift_not_bijective")
    if not _verify_full_transport(source, target, point_map):
        return BlockProvenanceResult(False, "full_relation_transport_check_failed")

    certificate = HomogeneousBlockTransportCertificate(
        source_partition=source_blocks,
        target_partition=target_blocks,
        block_map=mapping,
        point_map=point_map,
        source_quotient=source_quotient,
        target_quotient=target_quotient,
    )
    return BlockProvenanceResult(True, "exact_homogeneous_block_transport", certificate)
