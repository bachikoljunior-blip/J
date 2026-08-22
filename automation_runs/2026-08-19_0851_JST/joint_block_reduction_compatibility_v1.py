from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = 1
STATUS_EXACT = "exact_joint_block_reduction_compatibility"
STATUS_FAIL = "fail_closed_joint_block_reduction_compatibility"
REV274_STATUS_EXACT = "exact_group_block_action_equivariance"


class JointBlockReductionCompatibilityError(ValueError):
    pass


@dataclass(frozen=True)
class JointBlockReductionCompatibility:
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
    relation_point_map: tuple[int, ...]
    relation_identity_digest: str
    action_certificate_digest: str
    joint_certificate_digest: str
    reason: str


def _fail(reason: str) -> JointBlockReductionCompatibility:
    return JointBlockReductionCompatibility(
        schema_version=SCHEMA_VERSION,
        status=STATUS_FAIL,
        exact=False,
        complete=False,
        domain_degree=0,
        block_count=0,
        block_size=0,
        source_blocks=(),
        target_blocks=(),
        block_bijection=(),
        relation_point_map=(),
        relation_identity_digest="",
        action_certificate_digest="",
        joint_certificate_digest="",
        reason=reason,
    )


def _field(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        if name not in value:
            raise JointBlockReductionCompatibilityError(f"missing field {name!r}")
        return value[name]
    if not hasattr(value, name):
        raise JointBlockReductionCompatibilityError(f"missing field {name!r}")
    return getattr(value, name)


def _int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise JointBlockReductionCompatibilityError(f"{field} must be an integer")
    return value


def _permutation(value: Any, degree: int, field: str) -> tuple[int, ...]:
    try:
        result = tuple(_int(item, field) for item in value)
    except TypeError as exc:
        raise JointBlockReductionCompatibilityError(f"{field} must be iterable") from exc
    if len(result) != degree or set(result) != set(range(degree)):
        raise JointBlockReductionCompatibilityError(
            f"{field} must be a permutation of 0..{degree - 1}"
        )
    return result


def _canonical_partition(value: Any, side: str):
    try:
        raw = tuple(tuple(_int(point, f"{side} partition point") for point in block) for block in value)
    except TypeError as exc:
        raise JointBlockReductionCompatibilityError(f"{side} partition must be iterable") from exc
    if not raw or any(not block for block in raw):
        raise JointBlockReductionCompatibilityError(f"{side} partition must contain nonempty blocks")
    if any(len(set(block)) != len(block) for block in raw):
        raise JointBlockReductionCompatibilityError(f"{side} partition repeats a point within a block")
    normalized = tuple(tuple(sorted(block)) for block in raw)
    flat = tuple(point for block in normalized for point in block)
    if any(point < 0 for point in flat):
        raise JointBlockReductionCompatibilityError(f"{side} partition contains a negative point")
    if len(set(flat)) != len(flat):
        raise JointBlockReductionCompatibilityError(f"{side} partition blocks overlap")
    degree = len(flat)
    if set(flat) != set(range(degree)):
        raise JointBlockReductionCompatibilityError(
            f"{side} partition must cover exactly 0..{degree - 1}"
        )
    order = tuple(sorted(range(len(normalized)), key=lambda index: normalized[index]))
    canonical = tuple(normalized[index] for index in order)
    raw_to_canonical = {
        raw_index: canonical_index for canonical_index, raw_index in enumerate(order)
    }
    return raw, canonical, raw_to_canonical, degree


def _canonical_block_map(
    raw_map: Any,
    block_count: int,
    source_raw_to_canonical: Mapping[int, int],
    target_raw_to_canonical: Mapping[int, int],
) -> tuple[int, ...]:
    mapping = _permutation(raw_map, block_count, "relation block_map")
    canonical: list[int | None] = [None] * block_count
    for source_raw, target_raw in enumerate(mapping):
        canonical[source_raw_to_canonical[source_raw]] = target_raw_to_canonical[target_raw]
    if any(item is None for item in canonical):
        raise JointBlockReductionCompatibilityError("canonical relation block_map is incomplete")
    return tuple(int(item) for item in canonical)


def _normalize_blocks(value: Any, field: str) -> tuple[tuple[int, ...], ...]:
    try:
        return tuple(tuple(_int(point, field) for point in block) for block in value)
    except TypeError as exc:
        raise JointBlockReductionCompatibilityError(f"{field} must be a block family") from exc


def _normalize_permutation_family(value: Any, degree: int, field: str):
    try:
        return tuple(_permutation(item, degree, field) for item in value)
    except TypeError as exc:
        raise JointBlockReductionCompatibilityError(f"{field} must be iterable") from exc


def _digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _validated_action_identity(action: Any):
    schema_version = _int(_field(action, "schema_version"), "action schema_version")
    status = _field(action, "status")
    exact = _field(action, "exact")
    complete = _field(action, "complete")
    if schema_version != 1 or status != REV274_STATUS_EXACT or exact is not True or complete is not True:
        raise JointBlockReductionCompatibilityError("action certificate is not exact complete rev274 evidence")

    domain_degree = _int(_field(action, "domain_degree"), "action domain_degree")
    block_count = _int(_field(action, "block_count"), "action block_count")
    block_size = _int(_field(action, "block_size"), "action block_size")
    if domain_degree <= 0 or block_count <= 0 or block_size <= 0:
        raise JointBlockReductionCompatibilityError("action dimensions must be positive")
    if block_count * block_size != domain_degree:
        raise JointBlockReductionCompatibilityError("action block dimensions do not cover the domain")

    source_blocks = _normalize_blocks(_field(action, "source_blocks"), "action source_blocks")
    target_blocks = _normalize_blocks(_field(action, "target_blocks"), "action target_blocks")
    if len(source_blocks) != block_count or len(target_blocks) != block_count:
        raise JointBlockReductionCompatibilityError("action block count is inconsistent")
    if any(len(block) != block_size for block in source_blocks + target_blocks):
        raise JointBlockReductionCompatibilityError("action block size is inconsistent")
    if tuple(sorted(source_blocks)) != source_blocks or tuple(sorted(target_blocks)) != target_blocks:
        raise JointBlockReductionCompatibilityError("action partitions are not canonically ordered")

    block_bijection = _permutation(
        _field(action, "block_bijection"), block_count, "action block_bijection"
    )
    source_generators = _normalize_permutation_family(
        _field(action, "source_generators"), domain_degree, "action source_generators"
    )
    target_generators = _normalize_permutation_family(
        _field(action, "target_generators"), domain_degree, "action target_generators"
    )
    if len(source_generators) != len(target_generators):
        raise JointBlockReductionCompatibilityError("action original generator lists are not paired")
    source_quotient_generators = _normalize_permutation_family(
        _field(action, "source_quotient_generators"),
        block_count,
        "action source_quotient_generators",
    )
    target_quotient_generators = _normalize_permutation_family(
        _field(action, "target_quotient_generators"),
        block_count,
        "action target_quotient_generators",
    )
    if len(source_quotient_generators) != len(source_generators) or len(target_quotient_generators) != len(target_generators):
        raise JointBlockReductionCompatibilityError("action quotient generators do not match original generator pairing")
    for source_q, target_q in zip(
        source_quotient_generators, target_quotient_generators, strict=True
    ):
        for source_block in range(block_count):
            if block_bijection[source_q[source_block]] != target_q[block_bijection[source_block]]:
                raise JointBlockReductionCompatibilityError(
                    "action block bijection does not intertwine quotient generators"
                )

    payload = {
        "schema_version": 1,
        "status": REV274_STATUS_EXACT,
        "domain_degree": domain_degree,
        "block_count": block_count,
        "block_size": block_size,
        "source_blocks": source_blocks,
        "target_blocks": target_blocks,
        "block_bijection": block_bijection,
        "source_generators": source_generators,
        "target_generators": target_generators,
        "source_quotient_generators": source_quotient_generators,
        "target_quotient_generators": target_quotient_generators,
    }
    expected_digest = _digest(payload)
    supplied_digest = _field(action, "certificate_digest")
    if supplied_digest != expected_digest:
        raise JointBlockReductionCompatibilityError("action certificate digest mismatch")
    return (
        domain_degree,
        block_count,
        block_size,
        source_blocks,
        target_blocks,
        block_bijection,
        expected_digest,
    )


def _freeze_quotient(quotient: Any, side: str, block_count: int, block_size: int):
    if _int(_field(quotient, "block_count"), f"{side} quotient block_count") != block_count:
        raise JointBlockReductionCompatibilityError(f"{side} quotient block_count mismatch")
    try:
        block_sizes = tuple(
            _int(item, f"{side} quotient block_sizes")
            for item in _field(quotient, "block_sizes")
        )
    except TypeError as exc:
        raise JointBlockReductionCompatibilityError(f"{side} quotient block_sizes must be iterable") from exc
    if len(block_sizes) != block_count or any(item != block_size for item in block_sizes):
        raise JointBlockReductionCompatibilityError(f"{side} quotient block_sizes mismatch")

    frozen_relations = []
    try:
        relations = tuple(_field(quotient, "relations"))
    except TypeError as exc:
        raise JointBlockReductionCompatibilityError(f"{side} quotient relations must be iterable") from exc
    seen: set[tuple[str, int]] = set()
    for relation in relations:
        name = _field(relation, "name")
        arity = _int(_field(relation, "arity"), f"{side} quotient relation arity")
        if not isinstance(name, str) or not name or arity not in (1, 2):
            raise JointBlockReductionCompatibilityError(f"{side} quotient relation signature is invalid")
        key = (name, arity)
        if key in seen:
            raise JointBlockReductionCompatibilityError(f"{side} quotient repeats a relation signature")
        seen.add(key)
        normalized_tuples = []
        try:
            raw_tuples = tuple(_field(relation, "tuples"))
        except TypeError as exc:
            raise JointBlockReductionCompatibilityError(f"{side} quotient relation tuples must be iterable") from exc
        for item in raw_tuples:
            try:
                normalized = tuple(_int(point, f"{side} quotient relation point") for point in item)
            except TypeError as exc:
                raise JointBlockReductionCompatibilityError(f"{side} quotient relation tuple must be iterable") from exc
            if len(normalized) != arity or any(point < 0 or point >= block_count for point in normalized):
                raise JointBlockReductionCompatibilityError(f"{side} quotient relation tuple is outside the quotient domain")
            normalized_tuples.append(normalized)
        frozen_relations.append(
            {
                "name": name,
                "arity": arity,
                "tuples": tuple(sorted(set(normalized_tuples))),
            }
        )
    frozen_relations.sort(key=lambda item: (item["name"], item["arity"]))
    return {
        "block_count": block_count,
        "block_sizes": block_sizes,
        "relations": tuple(frozen_relations),
    }


def certify_joint_block_reduction_compatibility(
    relation_result: Any,
    action_certificate: Any,
) -> JointBlockReductionCompatibility:
    """Bind exact relation and group-action block evidence to one supplied reduction.

    This function does not re-prove relation homogeneity. It accepts only an
    upstream result explicitly marked exact with a non-null certificate, then
    proves that its partition/map/quotient dimensions are identical to the
    independently replayable rev274 action certificate. Any mismatch fails
    closed and no joint exactness is emitted.
    """
    try:
        if _field(relation_result, "exact") is not True:
            raise JointBlockReductionCompatibilityError("relation result is not exact")
        relation_certificate = _field(relation_result, "certificate")
        if relation_certificate is None:
            raise JointBlockReductionCompatibilityError("relation result has no certificate")

        (
            domain_degree,
            block_count,
            block_size,
            action_source_blocks,
            action_target_blocks,
            action_block_bijection,
            action_digest,
        ) = _validated_action_identity(action_certificate)

        relation_source_raw, relation_source_blocks, source_raw_to_canonical, source_degree = _canonical_partition(
            _field(relation_certificate, "source_partition"), "relation source"
        )
        relation_target_raw, relation_target_blocks, target_raw_to_canonical, target_degree = _canonical_partition(
            _field(relation_certificate, "target_partition"), "relation target"
        )
        if source_degree != domain_degree or target_degree != domain_degree:
            raise JointBlockReductionCompatibilityError("relation and action domain degrees differ")
        if len(relation_source_blocks) != block_count or len(relation_target_blocks) != block_count:
            raise JointBlockReductionCompatibilityError("relation and action block counts differ")
        if relation_source_blocks != action_source_blocks:
            raise JointBlockReductionCompatibilityError("relation and action source partitions differ")
        if relation_target_blocks != action_target_blocks:
            raise JointBlockReductionCompatibilityError("relation and action target partitions differ")

        relation_block_bijection = _canonical_block_map(
            _field(relation_certificate, "block_map"),
            block_count,
            source_raw_to_canonical,
            target_raw_to_canonical,
        )
        if relation_block_bijection != action_block_bijection:
            raise JointBlockReductionCompatibilityError("relation and action block bijections differ")

        relation_point_map = _permutation(
            _field(relation_certificate, "point_map"),
            domain_degree,
            "relation point_map",
        )
        for source_index, source_block in enumerate(relation_source_blocks):
            image = {relation_point_map[point] for point in source_block}
            expected = set(relation_target_blocks[relation_block_bijection[source_index]])
            if image != expected:
                raise JointBlockReductionCompatibilityError(
                    "relation point_map does not realize the common block bijection"
                )

        source_quotient = _freeze_quotient(
            _field(relation_certificate, "source_quotient"),
            "source",
            block_count,
            block_size,
        )
        target_quotient = _freeze_quotient(
            _field(relation_certificate, "target_quotient"),
            "target",
            block_count,
            block_size,
        )
        if tuple((item["name"], item["arity"]) for item in source_quotient["relations"]) != tuple(
            (item["name"], item["arity"]) for item in target_quotient["relations"]
        ):
            raise JointBlockReductionCompatibilityError("source and target quotient relation signatures differ")

        relation_identity_payload = {
            "source_partition_raw": relation_source_raw,
            "target_partition_raw": relation_target_raw,
            "canonical_source_blocks": relation_source_blocks,
            "canonical_target_blocks": relation_target_blocks,
            "canonical_block_bijection": relation_block_bijection,
            "point_map": relation_point_map,
            "source_quotient": source_quotient,
            "target_quotient": target_quotient,
        }
        relation_digest = _digest(relation_identity_payload)
        joint_payload = {
            "schema_version": SCHEMA_VERSION,
            "status": STATUS_EXACT,
            "domain_degree": domain_degree,
            "block_count": block_count,
            "block_size": block_size,
            "source_blocks": relation_source_blocks,
            "target_blocks": relation_target_blocks,
            "block_bijection": relation_block_bijection,
            "relation_point_map": relation_point_map,
            "relation_identity_digest": relation_digest,
            "action_certificate_digest": action_digest,
        }
        joint_digest = _digest(joint_payload)
        return JointBlockReductionCompatibility(
            schema_version=SCHEMA_VERSION,
            status=STATUS_EXACT,
            exact=True,
            complete=True,
            domain_degree=domain_degree,
            block_count=block_count,
            block_size=block_size,
            source_blocks=relation_source_blocks,
            target_blocks=relation_target_blocks,
            block_bijection=relation_block_bijection,
            relation_point_map=relation_point_map,
            relation_identity_digest=relation_digest,
            action_certificate_digest=action_digest,
            joint_certificate_digest=joint_digest,
            reason="exact upstream relation and group-action certificates are bound to the identical canonical block reduction",
        )
    except (JointBlockReductionCompatibilityError, TypeError, ValueError) as exc:
        return _fail(str(exc))


def replay_joint_block_reduction_compatibility(
    relation_result: Any,
    action_certificate: Any,
    certificate: JointBlockReductionCompatibility,
) -> bool:
    if not isinstance(certificate, JointBlockReductionCompatibility):
        return False
    if (
        certificate.schema_version != SCHEMA_VERSION
        or certificate.status != STATUS_EXACT
        or certificate.exact is not True
        or certificate.complete is not True
    ):
        return False
    replay = certify_joint_block_reduction_compatibility(
        relation_result, action_certificate
    )
    return replay == certificate and replay.joint_certificate_digest == certificate.joint_certificate_digest


__all__ = [
    "JointBlockReductionCompatibility",
    "JointBlockReductionCompatibilityError",
    "SCHEMA_VERSION",
    "STATUS_EXACT",
    "STATUS_FAIL",
    "certify_joint_block_reduction_compatibility",
    "replay_joint_block_reduction_compatibility",
]
