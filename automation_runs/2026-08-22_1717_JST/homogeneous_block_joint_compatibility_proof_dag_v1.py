from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from math import isclose, isfinite, log2
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "2026-08-19_0851_JST"
if str(LEGACY) not in sys.path:
    sys.path.insert(0, str(LEGACY))

from homogeneous_block_action_kernel_v1 import (
    BlockActionKernelFactorization,
    replay_block_action_kernel_factorization,
)
from homogeneous_block_action_provenance_v1 import (
    BlockActionProvenance,
    replay_group_block_action_equivariance,
)
from homogeneous_block_relation_provenance_v1 import (
    BlockProvenanceResult,
    HomogeneousBlockTransportCertificate,
    RelationStructure,
    certify_homogeneous_block_transport,
)
from proof_dag_accounting_v1 import ProofDAGValidation, validate_execution_proof_dag
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode

_SCHEMA = "homogeneous-block-joint-compatibility-proof-identity-v1"
_SOLVER_IDENTITY = (
    "homogeneous_block_joint_compatibility_proof_dag_v1",
    "proof_dag_accounting_v1",
    2000,
)
_OPERATION = "homogeneous_block_joint_reduction_compatibility_terminal"
_STATUS = "certified_homogeneous_block_joint_reduction_compatibility_proof_dag"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class HomogeneousBlockJointCompatibilityIdentity:
    schema: str
    solver_identity: tuple[str, str, int]
    relation_transcript_digest: str
    action_provenance_digest: str
    kernel_factorization_digest: str
    source_partition: tuple[tuple[int, ...], ...]
    target_partition: tuple[tuple[int, ...], ...]
    block_map: tuple[int, ...]
    domain_degree: int
    block_count: int
    block_size: int
    relation_count: int
    generator_count: int
    source_group_order: int
    target_group_order: int
    quotient_image_order: int
    source_kernel_order: int
    target_kernel_order: int
    verification_work_units: int
    root_n: int
    replay_stable: bool


@dataclass(frozen=True)
class HomogeneousBlockJointCompatibilityTerminalProof:
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
    proof_identity: HomogeneousBlockJointCompatibilityIdentity | None


@dataclass(frozen=True)
class HomogeneousBlockJointCompatibilityIdentityValidation:
    status: str
    certified: bool
    reason: str


@dataclass(frozen=True)
class HomogeneousBlockJointCompatibilityResult:
    status: str
    proof: HomogeneousBlockJointCompatibilityTerminalProof | None
    identity_validation: HomogeneousBlockJointCompatibilityIdentityValidation | None
    dag_validation: ProofDAGValidation | None
    semantic_si_exactness_certified: bool
    reason: str

    @property
    def certified(self) -> bool:
        return bool(
            self.identity_validation is not None
            and self.identity_validation.certified
            and self.dag_validation is not None
            and self.dag_validation.certified
        )


def _strict_positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return int(value)


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _freeze_structure(structure: RelationStructure) -> tuple:
    if not isinstance(structure, RelationStructure):
        raise ValueError("source and target must use the main-integrated rev273 RelationStructure type")
    if isinstance(structure.domain_size, bool) or not isinstance(structure.domain_size, int) or structure.domain_size < 1:
        raise ValueError("joint compatibility requires a positive relation domain")
    relations = []
    seen = set()
    for relation in structure.relations:
        key = (relation.name, relation.arity)
        if not isinstance(relation.name, str) or not relation.name or relation.arity not in (1, 2) or key in seen:
            raise ValueError("relation signature is not canonical unary/binary rev273 input")
        seen.add(key)
        tuples = tuple(sorted(tuple(item) for item in relation.tuples))
        for item in tuples:
            if len(item) != relation.arity:
                raise ValueError("relation tuple arity drifted")
            if any(isinstance(point, bool) or not isinstance(point, int) for point in item):
                raise ValueError("relation tuple contains a non-integer point")
            if any(point < 0 or point >= structure.domain_size for point in item):
                raise ValueError("relation tuple contains an out-of-domain point")
        relations.append((relation.name, int(relation.arity), tuples))
    return (int(structure.domain_size), tuple(relations))


def _freeze_quotient(quotient) -> tuple:
    return (
        int(quotient.block_count),
        tuple(int(size) for size in quotient.block_sizes),
        tuple(
            (
                relation.name,
                int(relation.arity),
                tuple(sorted(tuple(item) for item in relation.tuples)),
            )
            for relation in quotient.relations
        ),
    )


def _freeze_relation_certificate(certificate: HomogeneousBlockTransportCertificate) -> tuple:
    if not isinstance(certificate, HomogeneousBlockTransportCertificate):
        raise ValueError("exact rev273 result must carry HomogeneousBlockTransportCertificate")
    return (
        tuple(tuple(int(point) for point in block) for block in certificate.source_partition),
        tuple(tuple(int(point) for point in block) for block in certificate.target_partition),
        tuple(int(index) for index in certificate.block_map),
        tuple(int(point) for point in certificate.point_map),
        _freeze_quotient(certificate.source_quotient),
        _freeze_quotient(certificate.target_quotient),
    )


def _relation_transcript_digest(
    source: RelationStructure,
    target: RelationStructure,
    result: BlockProvenanceResult,
) -> str:
    if not isinstance(result, BlockProvenanceResult) or result.exact is not True or result.certificate is None:
        raise ValueError("only exact rev273 block relation provenance can be joined")
    certificate = result.certificate
    replay = certify_homogeneous_block_transport(
        source,
        target,
        certificate.source_partition,
        certificate.target_partition,
        certificate.block_map,
    )
    if replay != result:
        raise ValueError("rev273 block relation provenance does not replay exactly")
    payload = (
        _freeze_structure(source),
        _freeze_structure(target),
        result.reason,
        _freeze_relation_certificate(certificate),
    )
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _relation_work_units(source: RelationStructure, target: RelationStructure) -> int:
    n = source.domain_size
    if target.domain_size != n:
        raise ValueError("source and target relation domains differ")
    unary = sum(1 for relation in source.relations if relation.arity == 1)
    binary = sum(1 for relation in source.relations if relation.arity == 2)
    volume = sum(len(relation.tuples) * max(1, relation.arity) for relation in source.relations + target.relations)
    return int(1 + 16 * n + 16 * unary * n + 16 * binary * n * n + 16 * volume)


def _compatibility_inputs(
    source: RelationStructure,
    target: RelationStructure,
    relation_result: BlockProvenanceResult,
    action: BlockActionProvenance,
    kernel: BlockActionKernelFactorization,
) -> tuple[HomogeneousBlockTransportCertificate, str]:
    relation_digest = _relation_transcript_digest(source, target, relation_result)
    if not isinstance(action, BlockActionProvenance) or not replay_group_block_action_equivariance(action):
        raise ValueError("rev274 block-action provenance does not replay exactly")
    if not _valid_digest(action.certificate_digest):
        raise ValueError("rev274 action provenance digest is not canonical sha256")
    if not isinstance(kernel, BlockActionKernelFactorization) or not replay_block_action_kernel_factorization(kernel, action):
        raise ValueError("rev275 block-action kernel factorization does not replay exactly")
    if not _valid_digest(kernel.certificate_digest):
        raise ValueError("rev275 kernel factorization digest is not canonical sha256")
    certificate = relation_result.certificate
    assert certificate is not None

    if certificate.source_partition != action.source_blocks:
        raise ValueError("rev273 source partition and rev274 canonical source blocks differ")
    if certificate.target_partition != action.target_blocks:
        raise ValueError("rev273 target partition and rev274 canonical target blocks differ")
    if certificate.block_map != action.block_bijection:
        raise ValueError("rev273 block map and rev274 block bijection differ")
    if source.domain_size != action.domain_degree or target.domain_size != action.domain_degree:
        raise ValueError("relation and action domain degrees differ")
    if certificate.source_quotient.block_count != action.block_count or certificate.target_quotient.block_count != action.block_count:
        raise ValueError("relation quotient and action block counts differ")
    expected_sizes = (action.block_size,) * action.block_count
    if certificate.source_quotient.block_sizes != expected_sizes or certificate.target_quotient.block_sizes != expected_sizes:
        raise ValueError("relation quotient block sizes differ from rev274 action blocks")
    if kernel.provenance_digest != action.certificate_digest:
        raise ValueError("rev275 kernel is not bound to the supplied rev274 provenance digest")
    if kernel.domain_degree != action.domain_degree or kernel.block_count != action.block_count:
        raise ValueError("rev275 kernel factorization degree/block count differs from rev274")
    if kernel.generator_count != len(action.source_generators) or len(action.source_generators) != len(action.target_generators):
        raise ValueError("rev274/rev275 paired generator counts differ")
    if kernel.quotient_image_order < 1 or kernel.source_kernel_order < 1 or kernel.target_kernel_order < 1:
        raise ValueError("rev275 factorization orders must be positive")
    if kernel.source_kernel_order * kernel.quotient_image_order != kernel.source_group_order:
        raise ValueError("rev275 source order factorization drifted")
    if kernel.target_kernel_order * kernel.quotient_image_order != kernel.target_group_order:
        raise ValueError("rev275 target order factorization drifted")
    return certificate, relation_digest


def _local_log2_cost(identity: HomogeneousBlockJointCompatibilityIdentity) -> float:
    width = max(2, identity.domain_degree + identity.block_count + identity.generator_count + identity.relation_count)
    return log2(max(1, identity.verification_work_units)) + 12.0 * log2(width) + 48.0


def build_homogeneous_block_joint_compatibility_identity(
    source: RelationStructure,
    target: RelationStructure,
    relation_result: BlockProvenanceResult,
    action: BlockActionProvenance,
    kernel: BlockActionKernelFactorization,
    *,
    root_n: int | None = None,
) -> HomogeneousBlockJointCompatibilityIdentity:
    certificate, relation_digest = _compatibility_inputs(source, target, relation_result, action, kernel)
    n = action.domain_degree
    resolved_root = n if root_n is None else _strict_positive_int(root_n)
    if resolved_root is None or resolved_root < n:
        raise ValueError("root_n must be a positive integer dominating the original domain")
    relation_count = len(source.relations)
    if tuple((rel.name, rel.arity) for rel in source.relations) != tuple((rel.name, rel.arity) for rel in target.relations):
        raise ValueError("source and target relation signatures differ")
    work = _relation_work_units(source, target)
    action_work = 1 + 16 * max(1, len(action.source_generators)) * max(1, action.domain_degree + action.block_count)
    work += action_work + max(1, kernel.estimated_schreier_work_units)
    return HomogeneousBlockJointCompatibilityIdentity(
        schema=_SCHEMA,
        solver_identity=_SOLVER_IDENTITY,
        relation_transcript_digest=relation_digest,
        action_provenance_digest=action.certificate_digest,
        kernel_factorization_digest=kernel.certificate_digest,
        source_partition=certificate.source_partition,
        target_partition=certificate.target_partition,
        block_map=certificate.block_map,
        domain_degree=int(n),
        block_count=int(action.block_count),
        block_size=int(action.block_size),
        relation_count=int(relation_count),
        generator_count=int(len(action.source_generators)),
        source_group_order=int(kernel.source_group_order),
        target_group_order=int(kernel.target_group_order),
        quotient_image_order=int(kernel.quotient_image_order),
        source_kernel_order=int(kernel.source_kernel_order),
        target_kernel_order=int(kernel.target_kernel_order),
        verification_work_units=int(work),
        root_n=int(resolved_root),
        replay_stable=True,
    )


def _terminal_proof(identity: HomogeneousBlockJointCompatibilityIdentity) -> HomogeneousBlockJointCompatibilityTerminalProof:
    local = _local_log2_cost(identity)
    accounting = RecurrenceAccountingNode(
        n=identity.root_n,
        m=identity.domain_degree,
        operation_kind=_OPERATION,
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local,
        children=(),
        terminal_certified=True,
        reason=(
            "rev273 relation provenance, rev274 action equivariance, and rev275 kernel factorization replay under one common block reduction; "
            "this structural terminal does not compute quotient String-Isomorphism or any original-domain transporter"
        ),
    )
    return HomogeneousBlockJointCompatibilityTerminalProof(
        status="certified_homogeneous_block_joint_reduction_compatibility_evidence",
        coset=None,
        operation_kind=_OPERATION,
        root_n=identity.root_n,
        domain_size=identity.domain_degree,
        canonical=True,
        exact=False,
        local_cost_certified=True,
        local_log2_cost_bound=local,
        terminal_certified=True,
        permutation_candidates_checked=0,
        reason=(
            "three main-integrated homogeneous-block contracts are replay-consistent on one canonical partition/map; "
            "semantic String-Isomorphism exactness is intentionally not promoted"
        ),
        children=(),
        accounting=accounting,
        proof_identity=identity,
    )


def validate_homogeneous_block_joint_compatibility_identity(
    proof: HomogeneousBlockJointCompatibilityTerminalProof,
    source: RelationStructure,
    target: RelationStructure,
    relation_result: BlockProvenanceResult,
    action: BlockActionProvenance,
    kernel: BlockActionKernelFactorization,
    expected: HomogeneousBlockJointCompatibilityIdentity,
) -> HomogeneousBlockJointCompatibilityIdentityValidation:
    if not isinstance(proof, HomogeneousBlockJointCompatibilityTerminalProof):
        return HomogeneousBlockJointCompatibilityIdentityValidation("wrong_joint_compatibility_proof_type", False, "proof is not the rev2000 terminal proof runtime type")
    if proof.proof_identity != expected:
        return HomogeneousBlockJointCompatibilityIdentityValidation("mismatched_joint_compatibility_identity", False, "attached identity differs from the expected immutable joint identity")
    if expected.schema != _SCHEMA or expected.solver_identity != _SOLVER_IDENTITY or expected.replay_stable is not True:
        return HomogeneousBlockJointCompatibilityIdentityValidation("malformed_joint_compatibility_identity", False, "identity schema, solver identity, or replay-stability flag drifted")
    for digest in (expected.relation_transcript_digest, expected.action_provenance_digest, expected.kernel_factorization_digest):
        if not _valid_digest(digest):
            return HomogeneousBlockJointCompatibilityIdentityValidation("malformed_joint_compatibility_identity", False, "identity contains a noncanonical digest")
    try:
        replayed = build_homogeneous_block_joint_compatibility_identity(
            source, target, relation_result, action, kernel, root_n=expected.root_n
        )
    except (AssertionError, TypeError, ValueError) as exc:
        return HomogeneousBlockJointCompatibilityIdentityValidation("joint_compatibility_replay_failed", False, str(exc))
    if replayed != expected:
        return HomogeneousBlockJointCompatibilityIdentityValidation("joint_compatibility_identity_replay_drift", False, "independent rev273/rev274/rev275 replay produced a different immutable identity")
    try:
        hash(expected)
    except TypeError:
        return HomogeneousBlockJointCompatibilityIdentityValidation("unhashable_joint_compatibility_identity", False, "identity must be immutable and hashable")
    local = _local_log2_cost(expected)
    accounting = proof.accounting
    if not (
        proof.status == "certified_homogeneous_block_joint_reduction_compatibility_evidence"
        and proof.operation_kind == _OPERATION
        and proof.root_n == expected.root_n
        and proof.domain_size == expected.domain_degree
        and proof.canonical is True
        and proof.exact is False
        and proof.local_cost_certified is True
        and proof.terminal_certified is True
        and proof.coset is None
        and proof.permutation_candidates_checked == 0
        and not proof.children
        and isfinite(proof.local_log2_cost_bound)
        and isclose(proof.local_log2_cost_bound, local, rel_tol=0.0, abs_tol=1e-12)
        and isinstance(accounting, RecurrenceAccountingNode)
        and accounting.n == expected.root_n
        and accounting.m == expected.domain_degree
        and accounting.operation_kind == _OPERATION
        and accounting.canonical is True
        and accounting.cost_certified is True
        and accounting.terminal_certified is True
        and not accounting.children
        and isfinite(accounting.local_log2_cost_bound)
        and isclose(accounting.local_log2_cost_bound, local, rel_tol=0.0, abs_tol=1e-12)
    ):
        return HomogeneousBlockJointCompatibilityIdentityValidation("inconsistent_joint_compatibility_terminal_payload", False, "proof/accounting payload differs from the replay-derived conservative terminal")
    return HomogeneousBlockJointCompatibilityIdentityValidation(
        "verified_homogeneous_block_joint_compatibility_identity",
        True,
        "relation quotient, block action, and kernel factorization share one canonical block reduction and replay-stable transcript",
    )


def homogeneous_block_joint_compatibility_proof_dag_consumer(
    source: RelationStructure,
    target: RelationStructure,
    relation_result: BlockProvenanceResult,
    action: BlockActionProvenance,
    kernel: BlockActionKernelFactorization,
    *,
    root_n: int | None = None,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> HomogeneousBlockJointCompatibilityResult:
    try:
        identity = build_homogeneous_block_joint_compatibility_identity(
            source, target, relation_result, action, kernel, root_n=root_n
        )
    except (AssertionError, TypeError, ValueError) as exc:
        return HomogeneousBlockJointCompatibilityResult(
            "rejected_homogeneous_block_joint_compatibility",
            None,
            None,
            None,
            False,
            str(exc),
        )
    proof = _terminal_proof(identity)
    identity_validation = validate_homogeneous_block_joint_compatibility_identity(
        proof, source, target, relation_result, action, kernel, identity
    )
    if not identity_validation.certified:
        return HomogeneousBlockJointCompatibilityResult(
            identity_validation.status, proof, identity_validation, None, False, identity_validation.reason
        )
    external = _local_log2_cost(identity) + 16.0
    dag = validate_execution_proof_dag(
        proof,
        original_root_n=identity.root_n,
        external_log2_cost_bound=external,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not dag.certified:
        return HomogeneousBlockJointCompatibilityResult(
            dag.status, proof, identity_validation, dag, False, dag.reason
        )
    return HomogeneousBlockJointCompatibilityResult(
        _STATUS,
        proof,
        identity_validation,
        dag,
        False,
        "rev273/rev274/rev275 replay is jointly compatible and conservatively cost-certified; quotient SI and transporter lifting remain outside this scope",
    )


__all__ = [
    "HomogeneousBlockJointCompatibilityIdentity",
    "HomogeneousBlockJointCompatibilityIdentityValidation",
    "HomogeneousBlockJointCompatibilityResult",
    "HomogeneousBlockJointCompatibilityTerminalProof",
    "build_homogeneous_block_joint_compatibility_identity",
    "homogeneous_block_joint_compatibility_proof_dag_consumer",
    "validate_homogeneous_block_joint_compatibility_identity",
]
