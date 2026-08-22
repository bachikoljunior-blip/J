from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import isclose, isfinite, log2
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
from proof_dag_accounting_v1 import ProofDAGValidation, validate_execution_proof_dag
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode

STATUS_EXACT = "exact_homogeneous_block_quotient_string_isomorphism"
STATUS_EMPTY_INVENTORY = "exact_empty_homogeneous_block_quotient_feature_inventory"
STATUS_EMPTY_ORBIT = "exact_empty_homogeneous_block_quotient_string_isomorphism"
EXACT_STATUSES = frozenset((STATUS_EXACT, STATUS_EMPTY_INVENTORY, STATUS_EMPTY_ORBIT))


@dataclass(frozen=True)
class Rev1200QuotientSISnapshot:
    status: str
    exact: bool
    complete: bool
    block_count: int
    quotient_group_order: int
    partition_orbit_states: int
    target_stabilizer_order: int
    representative: Optional[tuple[int, ...]]
    target_stabilizer_generators: tuple[tuple[int, ...], ...]
    provenance_digest: str
    factorization_digest: str


@dataclass(frozen=True)
class HomogeneousBlockQuotientSIProofIdentity:
    schema: str
    solver_identity: tuple[str, str, int]
    provenance_digest: str
    factorization_digest: str
    root_n: int
    domain_size: int
    max_partition_states: int
    source_features: tuple[str, ...]
    target_features: tuple[str, ...]
    result_snapshot: Rev1200QuotientSISnapshot
    kernel_proof_identity: object
    external_log2_cost_bound: float
    replay_stable: bool


@dataclass(frozen=True)
class HomogeneousBlockQuotientSITerminalProof:
    status: str
    coset: object | None
    operation_kind: str
    root_n: int
    domain_size: int
    canonical: bool
    exact: bool
    local_cost_certified: bool
    local_log2_cost_bound: float
    terminal_certified: bool
    permutation_candidates_checked: int
    reason: str
    children: tuple
    accounting: RecurrenceAccountingNode
    proof_identity: HomogeneousBlockQuotientSIProofIdentity | None


@dataclass(frozen=True)
class HomogeneousBlockQuotientSIIdentityValidation:
    status: str
    certified: bool
    reason: str


@dataclass(frozen=True)
class HomogeneousBlockQuotientSIProofDAGConsumerResult:
    status: str
    proof: HomogeneousBlockQuotientSITerminalProof | None
    identity_validation: HomogeneousBlockQuotientSIIdentityValidation | None
    dag_validation: ProofDAGValidation | None
    snapshot: Rev1200QuotientSISnapshot | None
    reason: str

    @property
    def certified(self) -> bool:
        return bool(self.dag_validation is not None and self.dag_validation.certified)


def _strict_positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return int(value)


def _valid_digest(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        return False
    suffix = value[7:]
    return suffix == suffix.lower() and all(ch in "0123456789abcdef" for ch in suffix)


def _ordered_cells(values: tuple[str, ...], labels: tuple[str, ...]):
    positions = {label: [] for label in labels}
    for point, value in enumerate(values):
        positions[value].append(point)
    return tuple(tuple(positions[label]) for label in labels)


def _maps_cross(source: tuple[str, ...], target: tuple[str, ...], permutation) -> bool:
    return all(source[i] == target[permutation[i]] for i in range(len(source)))


def _stabilizes(values: tuple[str, ...], permutation) -> bool:
    return all(values[i] == values[permutation[i]] for i in range(len(values)))


def _canonical_generators(group) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(int(x) for x in generator) for generator in group.original_generators)


def _log2_sum(*values: float) -> float:
    values = tuple(float(value) for value in values)
    if not values:
        return 0.0
    if any(not isfinite(value) for value in values):
        return float("inf")
    top = max(values)
    return top + log2(sum(2.0 ** (value - top) for value in values))


def _quotient_replay_log2_cost(*, block_count: int, generator_count: int, max_partition_states: int) -> float:
    k = max(1, int(block_count))
    g = max(1, int(generator_count))
    states = max(1, int(max_partition_states))
    units = states * g * k * k * 256
    return log2(units) + 32.0


def _snapshot_from_components(
    *,
    status: str,
    block_count: int,
    quotient_group_order: int,
    partition_orbit_states: int,
    target_stabilizer_order: int,
    representative: Optional[tuple[int, ...]],
    target_stabilizer_generators: tuple[tuple[int, ...], ...],
    provenance_digest: str,
    factorization_digest: str,
) -> Rev1200QuotientSISnapshot:
    return Rev1200QuotientSISnapshot(
        status=status,
        exact=True,
        complete=True,
        block_count=int(block_count),
        quotient_group_order=int(quotient_group_order),
        partition_orbit_states=int(partition_orbit_states),
        target_stabilizer_order=int(target_stabilizer_order),
        representative=representative,
        target_stabilizer_generators=target_stabilizer_generators,
        provenance_digest=provenance_digest,
        factorization_digest=factorization_digest,
    )


def snapshot_public_rev1200_result(result: object) -> Rev1200QuotientSISnapshot:
    """Freeze only the public, replay-relevant rev1200 result fields."""
    required = (
        "status", "exact", "complete", "block_count", "quotient_group_order",
        "partition_orbit_states", "target_stabilizer_order", "coset",
        "provenance_digest", "factorization_digest",
    )
    missing = [field for field in required if not hasattr(result, field)]
    if missing:
        raise ValueError(f"public rev1200 result is missing fields: {missing}")
    status = getattr(result, "status")
    if status not in EXACT_STATUSES:
        raise ValueError("only exact complete rev1200 outcomes may enter the proof DAG")
    if getattr(result, "exact") is not True or getattr(result, "complete") is not True:
        raise ValueError("rev1200 public result must be literally exact=True and complete=True")
    integer_fields = {}
    for field, minimum in (
        ("block_count", 1), ("quotient_group_order", 1),
        ("partition_orbit_states", 0), ("target_stabilizer_order", 0),
    ):
        value = getattr(result, field)
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"rev1200 public field {field} is invalid")
        integer_fields[field] = int(value)
    provenance_digest = getattr(result, "provenance_digest")
    factorization_digest = getattr(result, "factorization_digest")
    if not _valid_digest(provenance_digest) or not _valid_digest(factorization_digest):
        raise ValueError("rev1200 public provenance/factorization digest is malformed")

    coset = getattr(result, "coset")
    representative = None
    stabilizer_generators: tuple[tuple[int, ...], ...] = ()
    if status == STATUS_EXACT:
        if coset is None:
            raise ValueError("exact nonempty rev1200 result omitted its quotient right coset")
        subgroup = getattr(coset, "subgroup", None)
        raw_representative = getattr(coset, "representative", None)
        if subgroup is None or raw_representative is None:
            raise ValueError("rev1200 quotient right coset is malformed")
        representative = tuple(int(x) for x in raw_representative)
        if len(representative) != integer_fields["block_count"] or set(representative) != set(range(integer_fields["block_count"])):
            raise ValueError("rev1200 quotient representative is not a block permutation")
        stabilizer_generators = _canonical_generators(subgroup)
        if getattr(subgroup, "order", None) != integer_fields["target_stabilizer_order"]:
            raise ValueError("rev1200 target stabilizer order disagrees with the quotient coset subgroup")
    else:
        if coset is not None:
            raise ValueError("exact-empty rev1200 result must not carry a quotient coset")
        if integer_fields["target_stabilizer_order"] != 0:
            raise ValueError("exact-empty rev1200 result must record target_stabilizer_order=0")

    return _snapshot_from_components(
        status=status,
        block_count=integer_fields["block_count"],
        quotient_group_order=integer_fields["quotient_group_order"],
        partition_orbit_states=integer_fields["partition_orbit_states"],
        target_stabilizer_order=integer_fields["target_stabilizer_order"],
        representative=representative,
        target_stabilizer_generators=stabilizer_generators,
        provenance_digest=provenance_digest,
        factorization_digest=factorization_digest,
    )


def replay_homogeneous_block_quotient_si_snapshot(
    provenance: BlockActionProvenance,
    factorization: BlockActionKernelFactorization,
    source_features: Sequence[str],
    target_features: Sequence[str],
    *,
    max_partition_states: int = 200_000,
) -> Rev1200QuotientSISnapshot:
    """Independently replay the exact public rev1200 quotient-domain semantics."""
    cap = _strict_positive_int(max_partition_states)
    if cap is None or cap > 10_000_000:
        raise ValueError("max_partition_states must be a positive integer at most 10,000,000")
    if not isinstance(provenance, BlockActionProvenance):
        raise ValueError("provenance must be a main-integrated rev274 BlockActionProvenance")
    if not isinstance(factorization, BlockActionKernelFactorization):
        raise ValueError("factorization must be a main-integrated rev275 BlockActionKernelFactorization")
    if not replay_group_block_action_equivariance(provenance):
        raise ValueError("rev274 block-action provenance does not replay exactly")
    if not replay_block_action_kernel_factorization(factorization, provenance):
        raise ValueError("rev275 block-action factorization does not replay exactly")
    if factorization.provenance_digest != provenance.certificate_digest:
        raise ValueError("rev274/rev275 provenance digest mismatch")
    if not _valid_digest(provenance.certificate_digest) or not _valid_digest(factorization.certificate_digest):
        raise ValueError("rev274/rev275 deterministic digest is malformed")

    k = provenance.block_count
    if factorization.block_count != k or factorization.quotient_image_order < 1:
        raise ValueError("rev274/rev275 quotient measures disagree")
    source = tuple(source_features)
    target = tuple(target_features)
    if len(source) != k or len(target) != k:
        raise ValueError("source_features and target_features must have one string per quotient block")
    if any(not isinstance(value, str) for value in source + target):
        raise ValueError("quotient String-Isomorphism features must be literal strings")

    source_group = schreier_stabilizer_chain(provenance.source_quotient_generators or (identity(k),))
    target_group = schreier_stabilizer_chain(provenance.target_quotient_generators or (identity(k),))
    if source_group.order != factorization.quotient_image_order or target_group.order != factorization.quotient_image_order:
        raise ValueError("reconstructed quotient image order differs from rev275")

    bijection = tuple(provenance.block_bijection)
    if len(bijection) != k or set(bijection) != set(range(k)):
        raise ValueError("rev274 block bijection is not a quotient permutation")
    pulled_target = tuple(target[bijection[i]] for i in range(k))
    if Counter(source) != Counter(pulled_target):
        return _snapshot_from_components(
            status=STATUS_EMPTY_INVENTORY, block_count=k,
            quotient_group_order=source_group.order, partition_orbit_states=0,
            target_stabilizer_order=0, representative=None,
            target_stabilizer_generators=(), provenance_digest=provenance.certificate_digest,
            factorization_digest=factorization.certificate_digest,
        )

    labels = tuple(sorted(set(source)))
    transported = canonical_partition_transporter(
        source_group,
        tuple((i,) for i in range(k)),
        _ordered_cells(source, labels),
        _ordered_cells(pulled_target, labels),
        max_states=cap,
    )
    if transported.status == "undetermined_partition_orbit_limit":
        raise ValueError("rev1200 quotient partition orbit is undetermined under the supplied state cap")
    if transported.status in {"partition_shape_mismatch", "no_partition_transporter"}:
        return _snapshot_from_components(
            status=STATUS_EMPTY_ORBIT, block_count=k,
            quotient_group_order=source_group.order,
            partition_orbit_states=transported.orbit_states,
            target_stabilizer_order=0, representative=None,
            target_stabilizer_generators=(), provenance_digest=provenance.certificate_digest,
            factorization_digest=factorization.certificate_digest,
        )
    if transported.status != "partition_transporter_coset":
        raise ValueError(f"unexpected canonical partition-transporter status: {transported.status}")
    if transported.transporter is None or transported.source_stabilizer is None:
        raise ValueError("exact quotient partition transporter omitted its witness or stabilizer")

    source_witness = tuple(transported.transporter)
    representative = tuple(compose(source_witness, bijection))
    if not source_group.contains(source_witness):
        raise ValueError("quotient partition witness escaped the certified source image")
    if not _maps_cross(source, target, representative):
        raise ValueError("cross-coordinate quotient representative does not transport the feature string")

    rinv = inverse(representative)
    target_stabilizer_generators = tuple(
        compose(rinv, compose(generator, representative))
        for generator in transported.source_stabilizer.original_generators
    )
    target_stabilizer = schreier_stabilizer_chain(target_stabilizer_generators or (identity(k),))
    for generator in target_stabilizer.original_generators or (identity(k),):
        if not target_group.contains(generator):
            raise ValueError("conjugated target stabilizer escaped the certified target quotient image")
        if not _stabilizes(target, generator):
            raise ValueError("conjugated target subgroup does not stabilize the target feature string")
    if target_stabilizer.order != transported.source_stabilizer.order:
        raise ValueError("source/target quotient feature-stabilizer orders differ after conjugation")

    return _snapshot_from_components(
        status=STATUS_EXACT, block_count=k,
        quotient_group_order=source_group.order,
        partition_orbit_states=transported.orbit_states,
        target_stabilizer_order=target_stabilizer.order,
        representative=representative,
        target_stabilizer_generators=_canonical_generators(target_stabilizer),
        provenance_digest=provenance.certificate_digest,
        factorization_digest=factorization.certificate_digest,
    )


def _coset_from_snapshot(snapshot: Rev1200QuotientSISnapshot):
    if snapshot.status != STATUS_EXACT:
        return None
    if snapshot.representative is None:
        raise ValueError("nonempty quotient snapshot omitted its representative")
    subgroup = schreier_stabilizer_chain(snapshot.target_stabilizer_generators or (identity(snapshot.block_count),))
    if subgroup.order != snapshot.target_stabilizer_order:
        raise ValueError("snapshot target-stabilizer generators do not realize the recorded order")
    return RightCoset(subgroup, snapshot.representative)


def build_homogeneous_block_quotient_si_proof_identity(
    provenance: BlockActionProvenance,
    factorization: BlockActionKernelFactorization,
    source_features: Sequence[str],
    target_features: Sequence[str],
    public_result: object,
    *,
    root_n: int | None = None,
    max_partition_states: int = 200_000,
) -> tuple[HomogeneousBlockQuotientSIProofIdentity, Rev1200QuotientSISnapshot]:
    cap = _strict_positive_int(max_partition_states)
    if cap is None or cap > 10_000_000:
        raise ValueError("max_partition_states must be a positive integer at most 10,000,000")
    actual = snapshot_public_rev1200_result(public_result)
    expected = replay_homogeneous_block_quotient_si_snapshot(
        provenance, factorization, source_features, target_features,
        max_partition_states=cap,
    )
    if actual != expected:
        raise ValueError("public rev1200 result differs from the independent quotient-domain replay")

    root = provenance.domain_degree if root_n is None else _strict_positive_int(root_n)
    if root is None or root < provenance.domain_degree:
        raise ValueError("root_n must be a positive integer dominating the rev274 original domain")
    source = tuple(source_features)
    target = tuple(target_features)

    kernel_proof = block_action_kernel_proof_dag_consumer(provenance, factorization, root_n=root)
    if not kernel_proof.certified or kernel_proof.proof is None or kernel_proof.dag_validation is None:
        raise ValueError(f"main-integrated rev950 block-action proof-DAG rejected: {kernel_proof.status}")
    kernel_identity = kernel_proof.proof.proof_identity
    if kernel_identity is None or not getattr(kernel_identity, "replay_stable", False):
        raise ValueError("rev950 block-action proof identity is missing or unstable")

    local = _quotient_replay_log2_cost(
        block_count=provenance.block_count,
        generator_count=max(1, len(provenance.source_quotient_generators)),
        max_partition_states=cap,
    )
    external = _log2_sum(float(kernel_proof.dag_validation.log2_work_bound), local)
    if not isfinite(local) or not isfinite(external):
        raise ValueError("quotient SI proof accounting bound is not finite")

    identity = HomogeneousBlockQuotientSIProofIdentity(
        schema="homogeneous-block-quotient-si-proof-identity-v1",
        solver_identity=("homogeneous_block_quotient_string_isomorphism_v1-public-contract", "proof_dag_accounting_v1", 1800),
        provenance_digest=provenance.certificate_digest,
        factorization_digest=factorization.certificate_digest,
        root_n=int(root),
        domain_size=provenance.block_count,
        max_partition_states=cap,
        source_features=source,
        target_features=target,
        result_snapshot=expected,
        kernel_proof_identity=kernel_identity,
        external_log2_cost_bound=external,
        replay_stable=True,
    )
    return identity, expected


def _terminal_proof(identity: HomogeneousBlockQuotientSIProofIdentity, local: float) -> HomogeneousBlockQuotientSITerminalProof:
    snapshot = identity.result_snapshot
    operation_kind = "homogeneous_block_quotient_string_isomorphism_terminal"
    accounting = RecurrenceAccountingNode(
        n=identity.root_n,
        m=identity.domain_size,
        operation_kind=operation_kind,
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local,
        children=(),
        terminal_certified=True,
        reason="independent bounded ordered-partition orbit replay exactly matches the public rev1200 quotient-domain result",
    )
    return HomogeneousBlockQuotientSITerminalProof(
        status="exact_homogeneous_block_quotient_si_proof_terminal",
        coset=_coset_from_snapshot(snapshot),
        operation_kind=operation_kind,
        root_n=identity.root_n,
        domain_size=identity.domain_size,
        canonical=True,
        exact=True,
        local_cost_certified=True,
        local_log2_cost_bound=local,
        terminal_certified=True,
        permutation_candidates_checked=snapshot.partition_orbit_states,
        reason="rev274/rev275/rev950 replay and an independent rev1200 public-contract quotient SI replay agree exactly",
        children=(),
        accounting=accounting,
        proof_identity=identity,
    )


def validate_homogeneous_block_quotient_si_proof_identity(
    proof: HomogeneousBlockQuotientSITerminalProof,
    identity: HomogeneousBlockQuotientSIProofIdentity,
    *,
    expected_local_log2_cost_bound: float,
) -> HomogeneousBlockQuotientSIIdentityValidation:
    if not isinstance(proof, HomogeneousBlockQuotientSITerminalProof):
        return HomogeneousBlockQuotientSIIdentityValidation("wrong_quotient_si_proof_type", False, "proof has the wrong rev1800 type")
    if proof.proof_identity != identity:
        return HomogeneousBlockQuotientSIIdentityValidation("mismatched_quotient_si_proof_identity", False, "attached proof identity differs from the replay-derived identity")
    if not identity.replay_stable or not isfinite(identity.external_log2_cost_bound) or identity.external_log2_cost_bound < 0.0:
        return HomogeneousBlockQuotientSIIdentityValidation("unstable_quotient_si_proof_identity", False, "identity replay cost is not finite/nonnegative")
    if not (
        proof.status == "exact_homogeneous_block_quotient_si_proof_terminal"
        and proof.operation_kind == "homogeneous_block_quotient_string_isomorphism_terminal"
        and proof.root_n == identity.root_n
        and proof.domain_size == identity.domain_size
        and proof.canonical and proof.exact and proof.local_cost_certified and proof.terminal_certified
        and not proof.children
        and proof.permutation_candidates_checked == identity.result_snapshot.partition_orbit_states
        and isclose(proof.local_log2_cost_bound, expected_local_log2_cost_bound, rel_tol=0.0, abs_tol=1e-12)
    ):
        return HomogeneousBlockQuotientSIIdentityValidation("inconsistent_quotient_si_terminal_payload", False, "terminal proof payload differs from the frozen quotient SI execution identity")
    accounting = proof.accounting
    if not (
        accounting.n == identity.root_n and accounting.m == identity.domain_size
        and accounting.operation_kind == proof.operation_kind and accounting.canonical
        and accounting.cost_certified and accounting.terminal_certified and not accounting.children
        and isclose(accounting.local_log2_cost_bound, expected_local_log2_cost_bound, rel_tol=0.0, abs_tol=1e-12)
    ):
        return HomogeneousBlockQuotientSIIdentityValidation("inconsistent_quotient_si_accounting", False, "terminal recurrence leaf differs from the frozen quotient SI identity")
    snapshot = identity.result_snapshot
    if snapshot.status == STATUS_EXACT:
        if proof.coset is None or snapshot.representative is None:
            return HomogeneousBlockQuotientSIIdentityValidation("missing_quotient_si_coset", False, "exact nonempty snapshot did not produce its quotient coset")
        if tuple(proof.coset.representative) != snapshot.representative or proof.coset.subgroup.order != snapshot.target_stabilizer_order:
            return HomogeneousBlockQuotientSIIdentityValidation("mismatched_quotient_si_coset", False, "proof coset disagrees with the replay-frozen public result")
    elif proof.coset is not None:
        return HomogeneousBlockQuotientSIIdentityValidation("nonempty_exact_empty_quotient_si_proof", False, "exact-empty snapshot unexpectedly carries a quotient coset")
    return HomogeneousBlockQuotientSIIdentityValidation(
        "verified_homogeneous_block_quotient_si_proof_identity", True,
        "public rev1200 exact result, independent quotient replay, rev274/rev275 provenance and rev950 proof identity share one replay-stable terminal identity",
    )


def homogeneous_block_quotient_si_proof_dag_consumer(
    provenance: BlockActionProvenance,
    factorization: BlockActionKernelFactorization,
    source_features: Sequence[str],
    target_features: Sequence[str],
    public_result: object,
    *,
    root_n: int | None = None,
    max_partition_states: int = 200_000,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> HomogeneousBlockQuotientSIProofDAGConsumerResult:
    try:
        identity, snapshot = build_homogeneous_block_quotient_si_proof_identity(
            provenance, factorization, source_features, target_features, public_result,
            root_n=root_n, max_partition_states=max_partition_states,
        )
        local = _quotient_replay_log2_cost(
            block_count=provenance.block_count,
            generator_count=max(1, len(provenance.source_quotient_generators)),
            max_partition_states=identity.max_partition_states,
        )
        proof = _terminal_proof(identity, local)
    except (AttributeError, AssertionError, TypeError, ValueError) as exc:
        return HomogeneousBlockQuotientSIProofDAGConsumerResult(
            "rejected_homogeneous_block_quotient_si_identity", None, None, None, None, str(exc)
        )

    validation = validate_homogeneous_block_quotient_si_proof_identity(
        proof, identity, expected_local_log2_cost_bound=local,
    )
    if not validation.certified:
        return HomogeneousBlockQuotientSIProofDAGConsumerResult(
            validation.status, proof, validation, None, snapshot, validation.reason
        )
    dag = validate_execution_proof_dag(
        proof,
        original_root_n=identity.root_n,
        external_log2_cost_bound=identity.external_log2_cost_bound,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not dag.certified:
        return HomogeneousBlockQuotientSIProofDAGConsumerResult(
            dag.status, proof, validation, dag, snapshot, dag.reason
        )
    return HomogeneousBlockQuotientSIProofDAGConsumerResult(
        "certified_homogeneous_block_quotient_si_proof_dag",
        proof, validation, dag, snapshot,
        "the exact complete public rev1200 quotient-domain result is independently replayed and conservatively occurrence-charged by the shared execution proof DAG; no original-domain transporter lift is claimed",
    )


__all__ = [
    "Rev1200QuotientSISnapshot",
    "HomogeneousBlockQuotientSIProofIdentity",
    "HomogeneousBlockQuotientSITerminalProof",
    "HomogeneousBlockQuotientSIIdentityValidation",
    "HomogeneousBlockQuotientSIProofDAGConsumerResult",
    "STATUS_EXACT", "STATUS_EMPTY_INVENTORY", "STATUS_EMPTY_ORBIT",
    "snapshot_public_rev1200_result",
    "replay_homogeneous_block_quotient_si_snapshot",
    "build_homogeneous_block_quotient_si_proof_identity",
    "validate_homogeneous_block_quotient_si_proof_identity",
    "homogeneous_block_quotient_si_proof_dag_consumer",
]
