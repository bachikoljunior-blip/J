from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Iterable

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "2026-08-19_0851_JST"
if str(LEGACY) not in sys.path:
    sys.path.insert(0, str(LEGACY))

from coset_stabilizer_primitives import RightCoset
from homogeneous_block_action_kernel_v1 import (
    BlockActionKernelFactorization,
    replay_block_action_kernel_factorization,
)
from homogeneous_block_action_provenance_v1 import (
    BlockActionProvenance,
    replay_group_block_action_equivariance,
)
from homogeneous_block_relation_provenance_v1 import RelationStructure
from permutation_group_schreier import compose, identity, schreier_stabilizer_chain

SCHEMA_VERSION = 1
STATUS_EXACT = "exact_homogeneous_block_quotient_relation_coset"
STATUS_EMPTY = "exact_empty_homogeneous_block_quotient_relation_coset"
STATUS_FAIL = "fail_closed_homogeneous_block_quotient_relation_si"


@dataclass(frozen=True)
class HomogeneousBlockQuotientSIResult:
    schema_version: int
    status: str
    exact: bool
    complete: bool
    provenance_digest: str
    factorization_digest: str
    domain_degree: int
    block_count: int
    quotient_image_order: int
    max_quotient_group_order: int
    max_relation_transport_checks: int
    estimated_relation_transport_checks: int
    source_group_elements_checked: int
    target_stabilizer_elements_checked: int
    target_stabilizer_order: int
    representative: tuple[int, ...] | None
    target_stabilizer_generators: tuple[tuple[int, ...], ...]
    coset: RightCoset | None
    certificate_digest: str
    reason: str


def _fail(reason: str, *, provenance_digest: str = "", factorization_digest: str = "", max_group: int = 0, max_checks: int = 0) -> HomogeneousBlockQuotientSIResult:
    return HomogeneousBlockQuotientSIResult(
        SCHEMA_VERSION,
        STATUS_FAIL,
        False,
        False,
        provenance_digest,
        factorization_digest,
        0,
        0,
        0,
        max_group,
        max_checks,
        0,
        0,
        0,
        0,
        None,
        (),
        None,
        "",
        reason,
    )


def _strict_positive(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _relation_index(structure: RelationStructure) -> dict[tuple[str, int], frozenset[tuple[int, ...]]]:
    if not isinstance(structure, RelationStructure):
        raise ValueError("source and target must be RelationStructure values")
    if isinstance(structure.domain_size, bool) or not isinstance(structure.domain_size, int) or structure.domain_size < 0:
        raise ValueError("relation structure domain size must be a nonnegative integer")
    out: dict[tuple[str, int], frozenset[tuple[int, ...]]] = {}
    for relation in structure.relations:
        if not isinstance(relation.name, str) or not relation.name:
            raise ValueError("relation names must be nonempty strings")
        if relation.arity not in (1, 2):
            raise ValueError("only unary/binary relations are supported")
        key = (relation.name, relation.arity)
        if key in out:
            raise ValueError("relation signatures must be unique")
        normalized: set[tuple[int, ...]] = set()
        for raw in relation.tuples:
            item = tuple(raw)
            if len(item) != relation.arity:
                raise ValueError("relation tuple has the wrong arity")
            if any(isinstance(point, bool) or not isinstance(point, int) for point in item):
                raise ValueError("relation tuples must contain integer points")
            if any(point < 0 or point >= structure.domain_size for point in item):
                raise ValueError("relation tuple contains a point outside the domain")
            normalized.add(item)
        out[key] = frozenset(normalized)
    return out


def _quotient_relation_index(
    structure: RelationStructure,
    blocks: tuple[tuple[int, ...], ...],
) -> dict[tuple[str, int], frozenset[tuple[int, ...]]]:
    if structure.domain_size != sum(len(block) for block in blocks):
        raise ValueError("relation domain does not match the certified block-action domain")
    if {point for block in blocks for point in block} != set(range(structure.domain_size)):
        raise ValueError("certified blocks do not cover the relation domain exactly")
    relations = _relation_index(structure)
    quotient: dict[tuple[str, int], frozenset[tuple[int, ...]]] = {}
    for key, tuples in relations.items():
        _name, arity = key
        lifted: set[tuple[int, ...]] = set()
        if arity == 1:
            for i, block in enumerate(blocks):
                values = {(point,) in tuples for point in block}
                if len(values) != 1:
                    raise ValueError(f"relation {key!r} is nonhomogeneous on block {i}")
                if True in values:
                    lifted.add((i,))
        else:
            for i, left in enumerate(blocks):
                for j, right in enumerate(blocks):
                    values = {(u, v) in tuples for u in left for v in right}
                    if len(values) != 1:
                        raise ValueError(f"relation {key!r} is nonhomogeneous on block pair {(i, j)!r}")
                    if True in values:
                        lifted.add((i, j))
        quotient[key] = frozenset(lifted)
    return quotient


def _transport_relations(
    source: dict[tuple[str, int], frozenset[tuple[int, ...]]],
    target: dict[tuple[str, int], frozenset[tuple[int, ...]]],
    permutation: tuple[int, ...],
) -> bool:
    if source.keys() != target.keys():
        return False
    for key, tuples in source.items():
        transported = frozenset(tuple(permutation[p] for p in item) for item in tuples)
        if transported != target[key]:
            return False
    return True


def _enumerate_group(generators: Iterable[tuple[int, ...]], degree: int, cap: int) -> tuple[tuple[int, ...], ...]:
    ident = identity(degree)
    gens = tuple(sorted(set(generators))) or (ident,)
    seen = {ident}
    queue = deque([ident])
    while queue:
        current = queue.popleft()
        for generator in gens:
            nxt = compose(current, generator)
            if nxt not in seen:
                seen.add(nxt)
                if len(seen) > cap:
                    raise ValueError("quotient image enumeration exceeded the predeclared group-order cap")
                queue.append(nxt)
    return tuple(sorted(seen))


def _relation_width(index: dict[tuple[str, int], frozenset[tuple[int, ...]]]) -> int:
    return sum(arity * len(tuples) + len(tuples) for (_name, arity), tuples in index.items())


def _certificate_payload(
    *,
    provenance: BlockActionProvenance,
    factorization: BlockActionKernelFactorization,
    source_quotient,
    target_quotient,
    max_group: int,
    max_checks: int,
    estimated_checks: int,
    source_checked: int,
    target_checked: int,
    stabilizer_order: int,
    representative,
    stabilizer_generators,
    status: str,
):
    def rel_payload(index):
        return tuple(
            (name, arity, tuple(sorted(tuples)))
            for (name, arity), tuples in sorted(index.items())
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "provenance_digest": provenance.certificate_digest,
        "factorization_digest": factorization.certificate_digest,
        "domain_degree": provenance.domain_degree,
        "block_count": provenance.block_count,
        "quotient_image_order": factorization.quotient_image_order,
        "block_bijection": provenance.block_bijection,
        "source_quotient_relations": rel_payload(source_quotient),
        "target_quotient_relations": rel_payload(target_quotient),
        "max_quotient_group_order": max_group,
        "max_relation_transport_checks": max_checks,
        "estimated_relation_transport_checks": estimated_checks,
        "source_group_elements_checked": source_checked,
        "target_stabilizer_elements_checked": target_checked,
        "target_stabilizer_order": stabilizer_order,
        "representative": representative,
        "target_stabilizer_generators": stabilizer_generators,
    }


def exact_homogeneous_block_quotient_relation_si(
    source: RelationStructure,
    target: RelationStructure,
    provenance: BlockActionProvenance,
    factorization: BlockActionKernelFactorization,
    *,
    max_quotient_group_order: int = 4096,
    max_relation_transport_checks: int = 2_000_000,
) -> HomogeneousBlockQuotientSIResult:
    """Solve a bounded exact quotient-relation SI coset inside rev274's action.

    This is deliberately an algorithmic terminal rather than a provenance adapter.
    Rev274 supplies the exact source/target quotient group actions and the fixed
    coordinate bijection B. Rev275 supplies the exact common quotient-image order.
    If that order fits the explicit cap, both quotient image groups are completely
    enumerated and every element of ``G_source * B`` is checked against the
    independently reconstructed homogeneous unary/binary quotient relations.

    A nonempty result is returned in the repository ``RightCoset`` convention:
    the representative is an actual source-to-target block permutation and the
    subgroup is the complete target quotient-relation stabilizer. Exact empty is
    returned only after the complete bounded image group has been exhausted.
    """
    pd = provenance.certificate_digest if isinstance(provenance, BlockActionProvenance) else ""
    fd = factorization.certificate_digest if isinstance(factorization, BlockActionKernelFactorization) else ""
    try:
        max_group = _strict_positive("max_quotient_group_order", max_quotient_group_order)
        max_checks = _strict_positive("max_relation_transport_checks", max_relation_transport_checks)
        if not isinstance(provenance, BlockActionProvenance) or not replay_group_block_action_equivariance(provenance):
            raise ValueError("rev274 block-action provenance does not replay exactly")
        if not isinstance(factorization, BlockActionKernelFactorization) or not replay_block_action_kernel_factorization(factorization, provenance):
            raise ValueError("rev275 kernel factorization does not replay exactly against rev274")
        if source.domain_size != provenance.domain_degree or target.domain_size != provenance.domain_degree:
            raise ValueError("relation structures must use the rev274 original-domain degree")
        if factorization.quotient_image_order < 1:
            raise ValueError("rev275 quotient image order must be positive")
        if factorization.quotient_image_order > max_group:
            raise ValueError("exact quotient image order exceeds the predeclared enumeration cap")

        source_q = _quotient_relation_index(source, provenance.source_blocks)
        target_q = _quotient_relation_index(target, provenance.target_blocks)
        if source_q.keys() != target_q.keys():
            raise ValueError("source and target quotient relation signatures differ")
        width = max(1, _relation_width(source_q) + _relation_width(target_q))
        estimated_checks = 2 * factorization.quotient_image_order * width
        if estimated_checks > max_checks:
            raise ValueError("complete quotient relation transport work exceeds the predeclared check cap")

        source_group = _enumerate_group(
            provenance.source_quotient_generators,
            provenance.block_count,
            max_group,
        )
        target_group = _enumerate_group(
            provenance.target_quotient_generators,
            provenance.block_count,
            max_group,
        )
        expected_order = factorization.quotient_image_order
        if len(source_group) != expected_order or len(target_group) != expected_order:
            raise ValueError("enumerated quotient image order disagrees with the exact rev275 factorization")

        block_bijection = tuple(provenance.block_bijection)
        solutions = tuple(
            sorted(
                compose(g, block_bijection)
                for g in source_group
                if _transport_relations(source_q, target_q, compose(g, block_bijection))
            )
        )
        source_checked = len(source_group)
        target_stabilizer = tuple(
            sorted(k for k in target_group if _transport_relations(target_q, target_q, k))
        )
        target_checked = len(target_group)

        if not solutions:
            payload = _certificate_payload(
                provenance=provenance,
                factorization=factorization,
                source_quotient=source_q,
                target_quotient=target_q,
                max_group=max_group,
                max_checks=max_checks,
                estimated_checks=estimated_checks,
                source_checked=source_checked,
                target_checked=target_checked,
                stabilizer_order=len(target_stabilizer),
                representative=None,
                stabilizer_generators=(),
                status=STATUS_EMPTY,
            )
            return HomogeneousBlockQuotientSIResult(
                SCHEMA_VERSION,
                STATUS_EMPTY,
                True,
                True,
                provenance.certificate_digest,
                factorization.certificate_digest,
                provenance.domain_degree,
                provenance.block_count,
                expected_order,
                max_group,
                max_checks,
                estimated_checks,
                source_checked,
                target_checked,
                len(target_stabilizer),
                None,
                (),
                None,
                _digest(payload),
                "the complete bounded quotient image coset contains no transporter of the exact homogeneous quotient relations",
            )

        representative = min(solutions)
        ident = identity(provenance.block_count)
        stabilizer_chain = schreier_stabilizer_chain(target_stabilizer or (ident,))
        if stabilizer_chain.order != len(target_stabilizer):
            raise AssertionError("target quotient relation stabilizer chain has the wrong order")
        coset = RightCoset(stabilizer_chain, representative)
        reconstructed = tuple(sorted(p for p in (compose(representative, k) for k in target_stabilizer)))
        if reconstructed != solutions:
            raise AssertionError("complete quotient transporter set is not the expected target-stabilizer right coset")
        if not all(coset.contains(p) for p in solutions):
            raise AssertionError("repository RightCoset convention rejected a certified quotient transporter")
        stabilizer_generators = tuple(stabilizer_chain.original_generators)
        payload = _certificate_payload(
            provenance=provenance,
            factorization=factorization,
            source_quotient=source_q,
            target_quotient=target_q,
            max_group=max_group,
            max_checks=max_checks,
            estimated_checks=estimated_checks,
            source_checked=source_checked,
            target_checked=target_checked,
            stabilizer_order=stabilizer_chain.order,
            representative=representative,
            stabilizer_generators=stabilizer_generators,
            status=STATUS_EXACT,
        )
        return HomogeneousBlockQuotientSIResult(
            SCHEMA_VERSION,
            STATUS_EXACT,
            True,
            True,
            provenance.certificate_digest,
            factorization.certificate_digest,
            provenance.domain_degree,
            provenance.block_count,
            expected_order,
            max_group,
            max_checks,
            estimated_checks,
            source_checked,
            target_checked,
            stabilizer_chain.order,
            representative,
            stabilizer_generators,
            coset,
            _digest(payload),
            "complete bounded quotient-image enumeration yields the exact homogeneous quotient-relation transporter right coset",
        )
    except (AssertionError, TypeError, ValueError) as exc:
        mg = max_quotient_group_order if isinstance(max_quotient_group_order, int) and not isinstance(max_quotient_group_order, bool) else 0
        mc = max_relation_transport_checks if isinstance(max_relation_transport_checks, int) and not isinstance(max_relation_transport_checks, bool) else 0
        return _fail(str(exc), provenance_digest=pd, factorization_digest=fd, max_group=mg, max_checks=mc)


__all__ = [
    "HomogeneousBlockQuotientSIResult",
    "SCHEMA_VERSION",
    "STATUS_EMPTY",
    "STATUS_EXACT",
    "STATUS_FAIL",
    "exact_homogeneous_block_quotient_relation_si",
]
