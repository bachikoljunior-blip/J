from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite, log2
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "2026-08-19_0851_JST"
if str(LEGACY) not in sys.path:
    sys.path.insert(0, str(LEGACY))

from homogeneous_block_relation_provenance_v1 import (
    BlockProvenanceResult,
    HomogeneousBlockTransportCertificate,
    RelationStructure,
    certify_homogeneous_block_transport,
)
from proof_dag_accounting_v1 import ProofDAGValidation, validate_execution_proof_dag
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


@dataclass(frozen=True)
class BlockRelationProvenanceProofIdentity:
    schema: str
    solver_identity: tuple[str, str, int]
    source_identity: tuple
    target_identity: tuple
    certificate_identity: tuple
    root_n: int
    domain_size: int
    block_count: int
    unary_relation_count: int
    binary_relation_count: int
    verification_work_units: int
    external_log2_cost_bound: float
    replay_stable: bool


@dataclass(frozen=True)
class BlockRelationProvenanceTerminalProof:
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
    proof_identity: BlockRelationProvenanceProofIdentity | None


@dataclass(frozen=True)
class BlockRelationProvenanceIdentityValidation:
    status: str
    certified: bool
    reason: str


@dataclass(frozen=True)
class BlockRelationProvenanceProofDAGConsumerResult:
    status: str
    proof: BlockRelationProvenanceTerminalProof | None
    identity_validation: BlockRelationProvenanceIdentityValidation | None
    dag_validation: ProofDAGValidation | None
    reason: str

    @property
    def certified(self) -> bool:
        return bool(self.dag_validation is not None and self.dag_validation.certified)


def _strict_positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return int(value)


def _freeze_structure(structure: RelationStructure) -> tuple:
    if not isinstance(structure, RelationStructure):
        raise ValueError("source and target must be rev273 RelationStructure values")
    if isinstance(structure.domain_size, bool) or not isinstance(structure.domain_size, int) or structure.domain_size < 0:
        raise ValueError("relation domain size must be a nonnegative integer")
    signatures = []
    seen = set()
    for relation in structure.relations:
        key = (relation.name, relation.arity)
        if not isinstance(relation.name, str) or not relation.name:
            raise ValueError("relation names must be nonempty strings")
        if relation.arity not in (1, 2):
            raise ValueError("only unary/binary rev273 relations are admissible")
        if key in seen:
            raise ValueError("relation signatures must be unique")
        seen.add(key)
        tuples = tuple(sorted(tuple(item) for item in relation.tuples))
        for item in tuples:
            if len(item) != relation.arity:
                raise ValueError("relation tuple arity drifted")
            if any(isinstance(point, bool) or not isinstance(point, int) for point in item):
                raise ValueError("relation tuple contains a non-integer point")
            if any(point < 0 or point >= structure.domain_size for point in item):
                raise ValueError("relation tuple contains an out-of-domain point")
        signatures.append((relation.name, int(relation.arity), tuples))
    return (int(structure.domain_size), tuple(signatures))


def _freeze_quotient(quotient) -> tuple:
    if quotient is None:
        raise ValueError("exact rev273 certificate requires quotient structures")
    relations = []
    for relation in quotient.relations:
        relations.append((relation.name, int(relation.arity), tuple(sorted(tuple(item) for item in relation.tuples))))
    return (
        int(quotient.block_count),
        tuple(int(size) for size in quotient.block_sizes),
        tuple(relations),
    )


def _freeze_certificate(certificate: HomogeneousBlockTransportCertificate) -> tuple:
    if not isinstance(certificate, HomogeneousBlockTransportCertificate):
        raise ValueError("rev273 exact result must carry a transport certificate")
    return (
        tuple(tuple(int(point) for point in block) for block in certificate.source_partition),
        tuple(tuple(int(point) for point in block) for block in certificate.target_partition),
        tuple(int(index) for index in certificate.block_map),
        tuple(int(point) for point in certificate.point_map),
        _freeze_quotient(certificate.source_quotient),
        _freeze_quotient(certificate.target_quotient),
    )


def _verification_work_units(source: RelationStructure, target: RelationStructure, certificate: HomogeneousBlockTransportCertificate) -> int:
    n = source.domain_size
    if target.domain_size != n:
        raise ValueError("source and target domains differ")
    unary_count = sum(1 for relation in source.relations if relation.arity == 1)
    binary_count = sum(1 for relation in source.relations if relation.arity == 2)
    source_tuple_volume = sum(len(relation.tuples) * max(1, relation.arity) for relation in source.relations)
    target_tuple_volume = sum(len(relation.tuples) * max(1, relation.arity) for relation in target.relations)
    block_count = len(certificate.source_partition)
    # Conservative explicit replay charge for partition validation, all unary
    # block fibres, all binary block-pair fibres, quotient transport, canonical
    # point lift, and the final full-relation transport comparison.
    units = (
        1
        + 8 * max(1, n)
        + 8 * max(1, block_count)
        + 8 * unary_count * max(1, n)
        + 8 * binary_count * max(1, n * n)
        + 8 * (source_tuple_volume + target_tuple_volume)
        + 8 * max(1, block_count * block_count) * max(1, binary_count)
    )
    return int(units)


def _local_log2_cost(identity: BlockRelationProvenanceProofIdentity) -> float:
    width = max(2, identity.domain_size + identity.block_count + identity.unary_relation_count + identity.binary_relation_count)
    return log2(max(1, identity.verification_work_units)) + 8.0 * log2(width) + 32.0


def _external_replay_log2_cost(identity: BlockRelationProvenanceProofIdentity) -> float:
    return _local_log2_cost(identity) + log2(max(2, identity.block_count + 1)) + 8.0


def build_block_relation_provenance_proof_identity(
    source: RelationStructure,
    target: RelationStructure,
    result: BlockProvenanceResult,
    *,
    root_n: int | None = None,
) -> BlockRelationProvenanceProofIdentity:
    if not isinstance(result, BlockProvenanceResult) or not result.exact or result.certificate is None:
        raise ValueError("only exact rev273 block-relation provenance may enter the proof DAG")
    certificate = result.certificate
    replayed = certify_homogeneous_block_transport(
        source,
        target,
        certificate.source_partition,
        certificate.target_partition,
        certificate.block_map,
    )
    if replayed != result:
        raise ValueError("rev273 homogeneous block provenance does not replay exactly")

    source_identity = _freeze_structure(source)
    target_identity = _freeze_structure(target)
    certificate_identity = _freeze_certificate(certificate)
    n = source.domain_size
    if n < 1 or target.domain_size != n:
        raise ValueError("proof-DAG admission requires matching positive source/target domains")
    resolved_root = n if root_n is None else _strict_positive_int(root_n)
    if resolved_root is None or resolved_root < n:
        raise ValueError("root_n must be a positive integer dominating the relation domain")
    block_count = len(certificate.source_partition)
    if block_count < 1 or block_count != len(certificate.target_partition):
        raise ValueError("rev273 certificate block counts are invalid")
    unary_count = sum(1 for relation in source.relations if relation.arity == 1)
    binary_count = sum(1 for relation in source.relations if relation.arity == 2)
    units = _verification_work_units(source, target, certificate)

    provisional = BlockRelationProvenanceProofIdentity(
        schema="block-relation-provenance-proof-identity-v1",
        solver_identity=("homogeneous_block_relation_provenance_v1", "proof_dag_accounting_v1", 952),
        source_identity=source_identity,
        target_identity=target_identity,
        certificate_identity=certificate_identity,
        root_n=int(resolved_root),
        domain_size=int(n),
        block_count=int(block_count),
        unary_relation_count=int(unary_count),
        binary_relation_count=int(binary_count),
        verification_work_units=units,
        external_log2_cost_bound=0.0,
        replay_stable=True,
    )
    external = _external_replay_log2_cost(provisional)
    if not isfinite(external) or external < 0.0:
        raise ValueError("rev273 replay charge is not finite and nonnegative")
    return BlockRelationProvenanceProofIdentity(
        **{**provisional.__dict__, "external_log2_cost_bound": external}
    )


def _terminal_proof(identity: BlockRelationProvenanceProofIdentity) -> BlockRelationProvenanceTerminalProof:
    local = _local_log2_cost(identity)
    accounting = RecurrenceAccountingNode(
        n=identity.root_n,
        m=identity.domain_size,
        operation_kind="homogeneous_block_relation_provenance_terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local,
        children=(),
        terminal_certified=True,
        reason="rev273 exact unary/binary homogeneous block transport is replayed from explicit source/target relations and charged conservatively",
    )
    return BlockRelationProvenanceTerminalProof(
        status="exact_homogeneous_block_relation_provenance_proof_terminal",
        coset=None,
        operation_kind="homogeneous_block_relation_provenance_terminal",
        root_n=identity.root_n,
        domain_size=identity.domain_size,
        canonical=True,
        exact=True,
        local_cost_certified=True,
        local_log2_cost_bound=local,
        terminal_certified=True,
        permutation_candidates_checked=identity.verification_work_units,
        reason="rev273 homogeneous block relation provenance replays exactly under one explicit immutable identity",
        children=(),
        accounting=accounting,
        proof_identity=identity,
    )


def validate_block_relation_provenance_proof_identity(
    proof: BlockRelationProvenanceTerminalProof,
    source: RelationStructure,
    target: RelationStructure,
    result: BlockProvenanceResult,
    expected: BlockRelationProvenanceProofIdentity,
) -> BlockRelationProvenanceIdentityValidation:
    if not isinstance(proof, BlockRelationProvenanceTerminalProof):
        return BlockRelationProvenanceIdentityValidation("wrong_block_relation_proof_type", False, "proof is not the rev952 terminal proof type")
    if proof.proof_identity != expected:
        return BlockRelationProvenanceIdentityValidation("mismatched_block_relation_proof_identity", False, "attached rev952 identity differs from replay-derived identity")
    if not expected.replay_stable or not isfinite(expected.external_log2_cost_bound) or expected.external_log2_cost_bound < 0.0:
        return BlockRelationProvenanceIdentityValidation("unstable_block_relation_proof_identity", False, "identity replay charge is not finite and nonnegative")
    try:
        replayed = build_block_relation_provenance_proof_identity(source, target, result, root_n=expected.root_n)
    except (TypeError, ValueError) as exc:
        return BlockRelationProvenanceIdentityValidation("block_relation_replay_failed", False, str(exc))
    if replayed != expected:
        return BlockRelationProvenanceIdentityValidation("block_relation_identity_replay_drift", False, "independent rev273 replay produced a different proof identity")
    local = _local_log2_cost(expected)
    if not (
        proof.status == "exact_homogeneous_block_relation_provenance_proof_terminal"
        and proof.operation_kind == "homogeneous_block_relation_provenance_terminal"
        and proof.canonical
        and proof.exact
        and proof.local_cost_certified
        and proof.terminal_certified
        and proof.coset is None
        and not proof.children
        and proof.root_n == expected.root_n
        and proof.domain_size == expected.domain_size
        and proof.permutation_candidates_checked == expected.verification_work_units
        and isfinite(proof.local_log2_cost_bound)
        and isclose(proof.local_log2_cost_bound, local, rel_tol=0.0, abs_tol=1e-12)
    ):
        return BlockRelationProvenanceIdentityValidation("inconsistent_block_relation_terminal_payload", False, "terminal proof payload differs from the replay-stable rev273 identity")
    accounting = proof.accounting
    if not (
        accounting.n == expected.root_n
        and accounting.m == expected.domain_size
        and accounting.operation_kind == proof.operation_kind
        and accounting.canonical
        and accounting.cost_certified
        and accounting.terminal_certified
        and not accounting.children
        and isclose(accounting.local_log2_cost_bound, local, rel_tol=0.0, abs_tol=1e-12)
    ):
        return BlockRelationProvenanceIdentityValidation("inconsistent_block_relation_accounting", False, "terminal recurrence leaf differs from the replay-stable rev273 identity")
    return BlockRelationProvenanceIdentityValidation(
        "verified_block_relation_provenance_proof_identity",
        True,
        "source/target relation transcripts, partitions, block map, canonical point lift, quotient relations, and conservative replay charge share one immutable identity",
    )


def block_relation_provenance_proof_dag_consumer(
    source: RelationStructure,
    target: RelationStructure,
    result: BlockProvenanceResult,
    *,
    root_n: int | None = None,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> BlockRelationProvenanceProofDAGConsumerResult:
    try:
        identity = build_block_relation_provenance_proof_identity(source, target, result, root_n=root_n)
    except (TypeError, ValueError) as exc:
        return BlockRelationProvenanceProofDAGConsumerResult(
            "rejected_block_relation_provenance_identity", None, None, None, str(exc)
        )
    proof = _terminal_proof(identity)
    identity_validation = validate_block_relation_provenance_proof_identity(
        proof, source, target, result, identity
    )
    if not identity_validation.certified:
        return BlockRelationProvenanceProofDAGConsumerResult(
            identity_validation.status, proof, identity_validation, None, identity_validation.reason
        )
    dag = validate_execution_proof_dag(
        proof,
        original_root_n=identity.root_n,
        external_log2_cost_bound=identity.external_log2_cost_bound,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not dag.certified:
        return BlockRelationProvenanceProofDAGConsumerResult(
            dag.status, proof, identity_validation, dag, dag.reason
        )
    return BlockRelationProvenanceProofDAGConsumerResult(
        "certified_homogeneous_block_relation_provenance_proof_dag",
        proof,
        identity_validation,
        dag,
        "rev273 exact homogeneous block relation provenance is replay-stable and admitted to the shared execution proof DAG",
    )


__all__ = [
    "BlockRelationProvenanceIdentityValidation",
    "BlockRelationProvenanceProofDAGConsumerResult",
    "BlockRelationProvenanceProofIdentity",
    "BlockRelationProvenanceTerminalProof",
    "block_relation_provenance_proof_dag_consumer",
    "build_block_relation_provenance_proof_identity",
    "validate_block_relation_provenance_proof_identity",
]
