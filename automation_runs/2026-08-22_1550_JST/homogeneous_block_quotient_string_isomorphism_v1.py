from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Optional, Sequence

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "2026-08-19_0851_JST"
REV950 = HERE.parent / "2026-08-22_1453_JST"
for path in (LEGACY, REV950):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from block_action_kernel_proof_dag_consumer_v1 import block_action_kernel_proof_dag_consumer
from canonical_partition_transporter_v1 import canonical_partition_transporter
from coset_stabilizer_primitives import RightCoset
from homogeneous_block_action_kernel_v1 import (
    BlockActionKernelFactorization,
    replay_block_action_kernel_factorization,
)
from homogeneous_block_action_provenance_v1 import (
    BlockActionProvenance,
    replay_group_block_action_equivariance,
)
from permutation_group_schreier import (
    compose,
    identity,
    inverse,
    schreier_stabilizer_chain,
)

STATUS_EXACT = "exact_homogeneous_block_quotient_string_isomorphism"
STATUS_EMPTY_INVENTORY = "exact_empty_homogeneous_block_quotient_feature_inventory"
STATUS_EMPTY_ORBIT = "exact_empty_homogeneous_block_quotient_string_isomorphism"
STATUS_UNDETERMINED_LIMIT = "undetermined_homogeneous_block_quotient_partition_orbit_limit"
STATUS_FAIL = "fail_closed_homogeneous_block_quotient_string_isomorphism"


@dataclass(frozen=True)
class HomogeneousBlockQuotientStringIsomorphism:
    status: str
    exact: bool
    complete: bool
    block_count: int
    quotient_group_order: int
    partition_orbit_states: int
    target_stabilizer_order: int
    coset: Optional[RightCoset]
    provenance_digest: str
    factorization_digest: str
    reason: str


def _result(
    status: str,
    *,
    exact: bool,
    complete: bool,
    block_count: int = 0,
    quotient_group_order: int = 0,
    partition_orbit_states: int = 0,
    target_stabilizer_order: int = 0,
    coset: Optional[RightCoset] = None,
    provenance_digest: str = "",
    factorization_digest: str = "",
    reason: str,
) -> HomogeneousBlockQuotientStringIsomorphism:
    return HomogeneousBlockQuotientStringIsomorphism(
        status,
        exact,
        complete,
        block_count,
        quotient_group_order,
        partition_orbit_states,
        target_stabilizer_order,
        coset,
        provenance_digest,
        factorization_digest,
        reason,
    )


def _ordered_cells(values: tuple[str, ...], labels: tuple[str, ...]):
    positions = {label: [] for label in labels}
    for point, value in enumerate(values):
        positions[value].append(point)
    return tuple(tuple(positions[label]) for label in labels)


def _maps_cross(source: tuple[str, ...], target: tuple[str, ...], permutation) -> bool:
    return all(source[i] == target[permutation[i]] for i in range(len(source)))


def _stabilizes(values: tuple[str, ...], permutation) -> bool:
    return all(values[i] == values[permutation[i]] for i in range(len(values)))


def exact_homogeneous_block_quotient_string_isomorphism(
    provenance: BlockActionProvenance,
    factorization: BlockActionKernelFactorization,
    source_features: Sequence[str],
    target_features: Sequence[str],
    *,
    max_partition_states: int = 200_000,
) -> HomogeneousBlockQuotientStringIsomorphism:
    """Solve the certified homogeneous block quotient String-Isomorphism leaf.

    rev274 supplies the exact paired block actions and canonical source-to-target
    block bijection. rev275 certifies the complete quotient image and kernels;
    rev950 links that factorization to the shared proof-DAG accounting. This
    executor solves only the quotient-domain feature transporter. It deliberately
    does not lift a quotient transporter back to the original domain.

    On a completed orbit, absence is exact. If the explicit partition-state cap
    is hit before completeness, the result is undetermined rather than empty.
    """
    if isinstance(max_partition_states, bool) or not isinstance(max_partition_states, int) or max_partition_states < 1:
        return _result(
            STATUS_FAIL,
            exact=False,
            complete=False,
            reason="max_partition_states must be a positive integer",
        )
    if not isinstance(provenance, BlockActionProvenance):
        return _result(STATUS_FAIL, exact=False, complete=False, reason="provenance must be a rev274 BlockActionProvenance")
    if not isinstance(factorization, BlockActionKernelFactorization):
        return _result(STATUS_FAIL, exact=False, complete=False, reason="factorization must be a rev275 BlockActionKernelFactorization")

    provenance_digest = provenance.certificate_digest
    factorization_digest = factorization.certificate_digest
    try:
        if not replay_group_block_action_equivariance(provenance):
            raise ValueError("rev274 block-action provenance does not replay exactly")
        if not replay_block_action_kernel_factorization(factorization, provenance):
            raise ValueError("rev275 block-action kernel factorization does not replay exactly")
        proof = block_action_kernel_proof_dag_consumer(provenance, factorization)
        if not proof.certified:
            raise ValueError(f"rev950 block-action kernel proof-DAG did not certify: {proof.status}")

        k = provenance.block_count
        if factorization.block_count != k:
            raise AssertionError("rev274/rev275 block counts differ")
        source = tuple(source_features)
        target = tuple(target_features)
        if len(source) != k or len(target) != k:
            raise ValueError("source_features and target_features must each have one string per certified quotient block")
        if any(not isinstance(value, str) for value in source + target):
            raise ValueError("quotient String-Isomorphism features must be strings")

        source_generators = provenance.source_quotient_generators or (identity(k),)
        target_generators = provenance.target_quotient_generators or (identity(k),)
        source_group = schreier_stabilizer_chain(source_generators)
        target_group = schreier_stabilizer_chain(target_generators)
        if source_group.order != factorization.quotient_image_order or target_group.order != factorization.quotient_image_order:
            raise AssertionError("reconstructed quotient image order differs from rev275")

        bijection = tuple(provenance.block_bijection)
        if len(bijection) != k or set(bijection) != set(range(k)):
            raise AssertionError("rev274 block bijection is not a quotient permutation")
        pulled_target = tuple(target[bijection[i]] for i in range(k))

        if Counter(source) != Counter(pulled_target):
            return _result(
                STATUS_EMPTY_INVENTORY,
                exact=True,
                complete=True,
                block_count=k,
                quotient_group_order=source_group.order,
                provenance_digest=provenance_digest,
                factorization_digest=factorization_digest,
                reason="source and target quotient feature inventories differ after the certified block-bijection pullback",
            )

        labels = tuple(sorted(set(source)))
        source_cells = _ordered_cells(source, labels)
        target_cells = _ordered_cells(pulled_target, labels)
        singleton_blocks = tuple((i,) for i in range(k))
        transported = canonical_partition_transporter(
            source_group,
            singleton_blocks,
            source_cells,
            target_cells,
            max_states=max_partition_states,
        )
        if transported.status == "undetermined_partition_orbit_limit":
            return _result(
                STATUS_UNDETERMINED_LIMIT,
                exact=False,
                complete=False,
                block_count=k,
                quotient_group_order=source_group.order,
                partition_orbit_states=transported.orbit_states,
                provenance_digest=provenance_digest,
                factorization_digest=factorization_digest,
                reason="certified quotient partition orbit exceeded max_partition_states before completeness was established",
            )
        if transported.status in {"partition_shape_mismatch", "no_partition_transporter"}:
            return _result(
                STATUS_EMPTY_ORBIT,
                exact=True,
                complete=True,
                block_count=k,
                quotient_group_order=source_group.order,
                partition_orbit_states=transported.orbit_states,
                provenance_digest=provenance_digest,
                factorization_digest=factorization_digest,
                reason="the complete certified source quotient image contains no feature transporter compatible with the rev274 block bijection",
            )
        if transported.status != "partition_transporter_coset":
            raise AssertionError(f"unexpected canonical partition transporter status: {transported.status}")
        if transported.transporter is None or transported.source_stabilizer is None:
            raise AssertionError("exact canonical partition transporter omitted its witness or stabilizer")

        source_witness = transported.transporter
        representative = compose(source_witness, bijection)
        if not source_group.contains(source_witness):
            raise AssertionError("partition witness escaped the certified source quotient image")
        if not _maps_cross(source, target, representative):
            raise AssertionError("cross-coordinate quotient representative does not transport the source feature string")

        rinv = inverse(representative)
        target_stabilizer_generators = tuple(
            compose(rinv, compose(generator, representative))
            for generator in transported.source_stabilizer.original_generators
        )
        target_stabilizer = schreier_stabilizer_chain(target_stabilizer_generators or (identity(k),))
        for generator in target_stabilizer.original_generators or (identity(k),):
            if not target_group.contains(generator):
                raise AssertionError("conjugated feature stabilizer escaped the certified target quotient image")
            if not _stabilizes(target, generator):
                raise AssertionError("conjugated target subgroup does not stabilize the target quotient feature string")
        if target_stabilizer.order != transported.source_stabilizer.order:
            raise AssertionError("source/target feature stabilizer orders differ under certified conjugation")

        return _result(
            STATUS_EXACT,
            exact=True,
            complete=True,
            block_count=k,
            quotient_group_order=source_group.order,
            partition_orbit_states=transported.orbit_states,
            target_stabilizer_order=target_stabilizer.order,
            coset=RightCoset(target_stabilizer, representative),
            provenance_digest=provenance_digest,
            factorization_digest=factorization_digest,
            reason="rev274/rev275/rev950 replayed; exact quotient ordered-feature transport returned one cross-coordinate witness and the complete target-feature stabilizer right coset",
        )
    except (AssertionError, TypeError, ValueError) as exc:
        return _result(
            STATUS_FAIL,
            exact=False,
            complete=False,
            block_count=provenance.block_count if isinstance(provenance.block_count, int) and not isinstance(provenance.block_count, bool) and provenance.block_count > 0 else 0,
            provenance_digest=provenance_digest,
            factorization_digest=factorization_digest,
            reason=str(exc),
        )


__all__ = [
    "HomogeneousBlockQuotientStringIsomorphism",
    "STATUS_EXACT",
    "STATUS_EMPTY_INVENTORY",
    "STATUS_EMPTY_ORBIT",
    "STATUS_UNDETERMINED_LIMIT",
    "STATUS_FAIL",
    "exact_homogeneous_block_quotient_string_isomorphism",
]
