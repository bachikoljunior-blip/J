from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite, log2
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "2026-08-19_0851_JST"
if str(LEGACY) not in sys.path:
    sys.path.insert(0, str(LEGACY))

from homogeneous_block_action_provenance_v1 import (
    BlockActionProvenance,
    replay_group_block_action_equivariance,
)
from proof_dag_accounting_v1 import ProofDAGValidation, validate_execution_proof_dag
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


@dataclass(frozen=True)
class BlockActionProvenanceProofIdentity:
    schema: str
    solver_identity: tuple[str, str, int]
    certificate_digest: str
    root_n: int
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
    verification_work_units: int
    external_log2_cost_bound: float
    replay_stable: bool


@dataclass(frozen=True)
class BlockActionProvenanceTerminalProof:
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
    proof_identity: BlockActionProvenanceProofIdentity | None


@dataclass(frozen=True)
class BlockActionProvenanceIdentityValidation:
    status: str
    certified: bool
    reason: str


@dataclass(frozen=True)
class BlockActionProvenanceProofDAGConsumerResult:
    status: str
    proof: BlockActionProvenanceTerminalProof | None
    identity_validation: BlockActionProvenanceIdentityValidation | None
    dag_validation: ProofDAGValidation | None
    reason: str

    @property
    def certified(self) -> bool:
        return bool(self.dag_validation is not None and self.dag_validation.certified)


def _strict_positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return int(value)


def _valid_digest(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        return False
    suffix = value[7:]
    return suffix == suffix.lower() and all(ch in "0123456789abcdef" for ch in suffix)


def _valid_permutation(perm, degree: int) -> bool:
    try:
        return len(perm) == degree and set(perm) == set(range(degree))
    except (TypeError, ValueError):
        return False


def _verification_work_units(certificate: BlockActionProvenance) -> int:
    n = int(certificate.domain_degree)
    m = int(certificate.block_count)
    b = int(certificate.block_size)
    g = len(certificate.source_generators)
    return int(
        1
        + 8 * max(1, n)
        + 8 * max(1, m * b)
        + 8 * max(1, m)
        + 8 * max(1, g * n)
        + 8 * max(1, g * m)
        + 8 * max(1, m * m)
    )


def _local_log2_cost(identity: BlockActionProvenanceProofIdentity) -> float:
    width = max(2, identity.domain_degree + identity.block_count + len(identity.source_generators))
    return log2(max(1, identity.verification_work_units)) + 8.0 * log2(width) + 32.0


def _external_replay_log2_cost(identity: BlockActionProvenanceProofIdentity) -> float:
    return _local_log2_cost(identity) + log2(max(2, len(identity.source_generators) + 1)) + 8.0


def build_block_action_provenance_proof_identity(
    certificate: BlockActionProvenance,
    *,
    root_n: int | None = None,
) -> BlockActionProvenanceProofIdentity:
    if not isinstance(certificate, BlockActionProvenance):
        raise ValueError("certificate must be a rev274 BlockActionProvenance")
    if not certificate.exact or not certificate.complete:
        raise ValueError("only exact complete rev274 block-action provenance may enter the proof DAG")
    if not replay_group_block_action_equivariance(certificate):
        raise ValueError("rev274 block-action provenance does not replay exactly")
    if not _valid_digest(certificate.certificate_digest):
        raise ValueError("rev274 deterministic digest is malformed")

    n = _strict_positive_int(certificate.domain_degree)
    m = _strict_positive_int(certificate.block_count)
    b = _strict_positive_int(certificate.block_size)
    if n is None or m is None or b is None or m * b != n:
        raise ValueError("rev274 domain/block measures are invalid")
    resolved_root = n if root_n is None else _strict_positive_int(root_n)
    if resolved_root is None or resolved_root < n:
        raise ValueError("root_n must be a positive integer dominating the original domain")

    source_blocks = tuple(tuple(int(x) for x in block) for block in certificate.source_blocks)
    target_blocks = tuple(tuple(int(x) for x in block) for block in certificate.target_blocks)
    block_bijection = tuple(int(x) for x in certificate.block_bijection)
    source_generators = tuple(tuple(int(x) for x in perm) for perm in certificate.source_generators)
    target_generators = tuple(tuple(int(x) for x in perm) for perm in certificate.target_generators)
    source_quotient = tuple(tuple(int(x) for x in perm) for perm in certificate.source_quotient_generators)
    target_quotient = tuple(tuple(int(x) for x in perm) for perm in certificate.target_quotient_generators)

    if len(source_blocks) != m or len(target_blocks) != m:
        raise ValueError("rev274 partition block counts drifted")
    if any(len(block) != b for block in source_blocks + target_blocks):
        raise ValueError("rev274 uniform block size drifted")
    if set(x for block in source_blocks for x in block) != set(range(n)):
        raise ValueError("rev274 source partition does not cover the original domain")
    if set(x for block in target_blocks for x in block) != set(range(n)):
        raise ValueError("rev274 target partition does not cover the original domain")
    if not _valid_permutation(block_bijection, m):
        raise ValueError("rev274 block bijection transcript is malformed")
    if len(source_generators) != len(target_generators):
        raise ValueError("rev274 original-domain generator lists are not paired")
    if len(source_quotient) != len(source_generators) or len(target_quotient) != len(target_generators):
        raise ValueError("rev274 quotient generator transcript does not match paired generators")
    if any(not _valid_permutation(perm, n) for perm in source_generators + target_generators):
        raise ValueError("rev274 original-domain generator transcript contains a malformed permutation")
    if any(not _valid_permutation(perm, m) for perm in source_quotient + target_quotient):
        raise ValueError("rev274 quotient generator transcript contains a malformed permutation")

    units = _verification_work_units(certificate)
    provisional = BlockActionProvenanceProofIdentity(
        schema="block-action-provenance-proof-identity-v1",
        solver_identity=("homogeneous_block_action_provenance_v1", "proof_dag_accounting_v1", 1600),
        certificate_digest=certificate.certificate_digest,
        root_n=resolved_root,
        domain_degree=n,
        block_count=m,
        block_size=b,
        source_blocks=source_blocks,
        target_blocks=target_blocks,
        block_bijection=block_bijection,
        source_generators=source_generators,
        target_generators=target_generators,
        source_quotient_generators=source_quotient,
        target_quotient_generators=target_quotient,
        verification_work_units=units,
        external_log2_cost_bound=0.0,
        replay_stable=True,
    )
    external = _external_replay_log2_cost(provisional)
    if not isfinite(external) or external < 0.0:
        raise ValueError("rev274 replay charge is not finite and nonnegative")
    return BlockActionProvenanceProofIdentity(
        **{**provisional.__dict__, "external_log2_cost_bound": external}
    )


def _terminal_proof(identity: BlockActionProvenanceProofIdentity) -> BlockActionProvenanceTerminalProof:
    local = _local_log2_cost(identity)
    accounting = RecurrenceAccountingNode(
        n=identity.root_n,
        m=identity.domain_degree,
        operation_kind="homogeneous_block_action_provenance_terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local,
        children=(),
        terminal_certified=True,
        reason="rev274 exact block-action equivariance replays from explicit partitions and paired original/quotient generators",
    )
    return BlockActionProvenanceTerminalProof(
        status="exact_homogeneous_block_action_provenance_proof_terminal",
        coset=None,
        operation_kind="homogeneous_block_action_provenance_terminal",
        root_n=identity.root_n,
        domain_size=identity.domain_degree,
        canonical=True,
        exact=True,
        local_cost_certified=True,
        local_log2_cost_bound=local,
        terminal_certified=True,
        permutation_candidates_checked=identity.verification_work_units,
        reason="rev274 homogeneous block-action provenance replays exactly under one immutable execution identity",
        children=(),
        accounting=accounting,
        proof_identity=identity,
    )


def validate_block_action_provenance_proof_identity(
    proof: BlockActionProvenanceTerminalProof,
    certificate: BlockActionProvenance,
    expected: BlockActionProvenanceProofIdentity,
) -> BlockActionProvenanceIdentityValidation:
    if not isinstance(proof, BlockActionProvenanceTerminalProof):
        return BlockActionProvenanceIdentityValidation(
            "wrong_block_action_provenance_proof_type", False, "proof is not the rev1600 terminal proof type"
        )
    if proof.proof_identity != expected:
        return BlockActionProvenanceIdentityValidation(
            "mismatched_block_action_provenance_proof_identity",
            False,
            "attached rev1600 identity differs from the replay-derived identity",
        )
    if not expected.replay_stable or not isfinite(expected.external_log2_cost_bound) or expected.external_log2_cost_bound < 0.0:
        return BlockActionProvenanceIdentityValidation(
            "unstable_block_action_provenance_proof_identity",
            False,
            "identity replay charge is not finite and nonnegative",
        )
    try:
        replayed = build_block_action_provenance_proof_identity(certificate, root_n=expected.root_n)
    except (TypeError, ValueError) as exc:
        return BlockActionProvenanceIdentityValidation("block_action_provenance_replay_failed", False, str(exc))
    if replayed != expected:
        return BlockActionProvenanceIdentityValidation(
            "block_action_provenance_identity_replay_drift",
            False,
            "independent rev274 replay produced a different proof identity",
        )
    local = _local_log2_cost(expected)
    if not (
        proof.status == "exact_homogeneous_block_action_provenance_proof_terminal"
        and proof.operation_kind == "homogeneous_block_action_provenance_terminal"
        and proof.canonical
        and proof.exact
        and proof.local_cost_certified
        and proof.terminal_certified
        and proof.coset is None
        and not proof.children
        and proof.root_n == expected.root_n
        and proof.domain_size == expected.domain_degree
        and proof.permutation_candidates_checked == expected.verification_work_units
        and isfinite(proof.local_log2_cost_bound)
        and isclose(proof.local_log2_cost_bound, local, rel_tol=0.0, abs_tol=1e-12)
    ):
        return BlockActionProvenanceIdentityValidation(
            "inconsistent_block_action_provenance_terminal_payload",
            False,
            "terminal proof payload differs from the replay-stable rev274 identity",
        )
    accounting = proof.accounting
    if not (
        accounting.n == expected.root_n
        and accounting.m == expected.domain_degree
        and accounting.operation_kind == proof.operation_kind
        and accounting.canonical
        and accounting.cost_certified
        and accounting.terminal_certified
        and not accounting.children
        and isclose(accounting.local_log2_cost_bound, local, rel_tol=0.0, abs_tol=1e-12)
    ):
        return BlockActionProvenanceIdentityValidation(
            "inconsistent_block_action_provenance_accounting",
            False,
            "terminal recurrence leaf differs from the replay-stable rev274 identity",
        )
    return BlockActionProvenanceIdentityValidation(
        "verified_block_action_provenance_proof_identity",
        True,
        "canonical source/target partitions, block bijection, paired original and quotient generators, intertwining digest, and conservative replay charge share one immutable identity",
    )


def block_action_provenance_proof_dag_consumer(
    certificate: BlockActionProvenance,
    *,
    root_n: int | None = None,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> BlockActionProvenanceProofDAGConsumerResult:
    try:
        identity = build_block_action_provenance_proof_identity(certificate, root_n=root_n)
    except (TypeError, ValueError) as exc:
        return BlockActionProvenanceProofDAGConsumerResult(
            "rejected_block_action_provenance_identity", None, None, None, str(exc)
        )
    proof = _terminal_proof(identity)
    identity_validation = validate_block_action_provenance_proof_identity(proof, certificate, identity)
    if not identity_validation.certified:
        return BlockActionProvenanceProofDAGConsumerResult(
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
        return BlockActionProvenanceProofDAGConsumerResult(
            dag.status, proof, identity_validation, dag, dag.reason
        )
    return BlockActionProvenanceProofDAGConsumerResult(
        "certified_homogeneous_block_action_provenance_proof_dag",
        proof,
        identity_validation,
        dag,
        "main-integrated rev274 exact homogeneous block-action provenance is replay-stably named and conservatively occurrence-charged by the shared execution proof DAG",
    )


__all__ = [
    "BlockActionProvenanceIdentityValidation",
    "BlockActionProvenanceProofDAGConsumerResult",
    "BlockActionProvenanceProofIdentity",
    "BlockActionProvenanceTerminalProof",
    "block_action_provenance_proof_dag_consumer",
    "build_block_action_provenance_proof_identity",
    "validate_block_action_provenance_proof_identity",
]
