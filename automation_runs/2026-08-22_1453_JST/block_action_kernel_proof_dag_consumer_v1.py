from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite, log2
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "2026-08-19_0851_JST"
if str(LEGACY) not in sys.path:
    sys.path.insert(0, str(LEGACY))

from homogeneous_block_action_kernel_v1 import (
    BlockActionKernelFactorization,
    replay_block_action_kernel_factorization,
)
from homogeneous_block_action_provenance_v1 import BlockActionProvenance
from proof_dag_accounting_v1 import ProofDAGValidation, validate_execution_proof_dag
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


@dataclass(frozen=True)
class BlockActionKernelProofIdentity:
    schema: str
    solver_identity: tuple[str, str, int]
    provenance_digest: str
    factorization_digest: str
    root_n: int
    domain_degree: int
    block_count: int
    generator_count: int
    work_identity: tuple[tuple[str, int], ...]
    order_identity: tuple[tuple[str, int], ...]
    source_kernel_generators: tuple[tuple[int, ...], ...]
    target_kernel_generators: tuple[tuple[int, ...], ...]
    external_log2_cost_bound: float
    replay_stable: bool


@dataclass(frozen=True)
class BlockActionKernelTerminalProof:
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
    proof_identity: BlockActionKernelProofIdentity | None


@dataclass(frozen=True)
class BlockActionKernelIdentityValidation:
    status: str
    certified: bool
    reason: str


@dataclass(frozen=True)
class BlockActionKernelProofDAGConsumerResult:
    status: str
    proof: BlockActionKernelTerminalProof | None
    identity_validation: BlockActionKernelIdentityValidation | None
    dag_validation: ProofDAGValidation | None
    reason: str

    @property
    def certified(self) -> bool:
        return bool(self.dag_validation is not None and self.dag_validation.certified)


def _valid_digest(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        return False
    suffix = value[7:]
    return suffix == suffix.lower() and all(ch in "0123456789abcdef" for ch in suffix)


def _strict_positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return int(value)


def _valid_permutation_family(family, degree: int) -> bool:
    target = set(range(degree))
    try:
        return all(len(perm) == degree and set(perm) == target for perm in family)
    except (TypeError, ValueError):
        return False


def _local_log2_cost(certificate: BlockActionKernelFactorization) -> float:
    units = max(1, int(certificate.estimated_schreier_work_units))
    width = max(2, int(certificate.domain_degree) + int(certificate.block_count))
    return log2(units) + 8.0 * log2(width) + 32.0


def _external_replay_log2_cost(certificate: BlockActionKernelFactorization) -> float:
    # rev275 replay reconstructs the complete factorization.  Charge another
    # conservative copy of the mechanical preflight bound plus polynomial
    # transcript comparison overhead rather than treating replay as free.
    return _local_log2_cost(certificate) + log2(max(2, certificate.generator_count + 1)) + 8.0


def build_block_action_kernel_proof_identity(
    certificate: BlockActionKernelFactorization,
    provenance: BlockActionProvenance,
    *,
    root_n: int | None = None,
) -> BlockActionKernelProofIdentity:
    if not isinstance(certificate, BlockActionKernelFactorization):
        raise ValueError("certificate must be a rev275 BlockActionKernelFactorization")
    if not isinstance(provenance, BlockActionProvenance):
        raise ValueError("provenance must be a rev274 BlockActionProvenance")
    if not certificate.exact or not certificate.complete:
        raise ValueError("only exact complete rev275 factorization evidence may enter the proof DAG")
    if not replay_block_action_kernel_factorization(certificate, provenance):
        raise ValueError("rev275 block-action kernel factorization does not replay exactly")
    if certificate.provenance_digest != provenance.certificate_digest:
        raise ValueError("factorization and provenance digests differ")
    if not _valid_digest(certificate.certificate_digest) or not _valid_digest(provenance.certificate_digest):
        raise ValueError("rev274/rev275 deterministic digests are malformed")

    n = _strict_positive_int(certificate.domain_degree)
    k = _strict_positive_int(certificate.block_count)
    if n is None or k is None or k > n:
        raise ValueError("rev275 domain/block measures are invalid")
    resolved_root = n if root_n is None else _strict_positive_int(root_n)
    if resolved_root is None or resolved_root < n:
        raise ValueError("root_n must be a positive integer dominating the original domain")
    if isinstance(certificate.generator_count, bool) or not isinstance(certificate.generator_count, int) or certificate.generator_count < 0:
        raise ValueError("generator count must be a nonnegative integer")
    if isinstance(certificate.estimated_schreier_work_units, bool) or not isinstance(certificate.estimated_schreier_work_units, int) or certificate.estimated_schreier_work_units < 0:
        raise ValueError("estimated Schreier work must be a nonnegative integer")
    if _strict_positive_int(certificate.work_cap) is None:
        raise ValueError("work cap must be a positive integer")
    if certificate.estimated_schreier_work_units > certificate.work_cap:
        raise ValueError("recorded Schreier work exceeds the frozen rev275 work cap")

    positive_orders = (
        certificate.source_group_order,
        certificate.target_group_order,
        certificate.quotient_image_order,
        certificate.source_kernel_order,
        certificate.target_kernel_order,
    )
    if any(_strict_positive_int(value) is None for value in positive_orders):
        raise ValueError("all source/target/kernel/image orders must be positive integers")
    if certificate.source_kernel_order * certificate.quotient_image_order != certificate.source_group_order:
        raise ValueError("source |G|=|ker||im| identity drifted")
    if certificate.target_kernel_order * certificate.quotient_image_order != certificate.target_group_order:
        raise ValueError("target |G|=|ker||im| identity drifted")
    if not _valid_permutation_family(certificate.source_kernel_generators, n):
        raise ValueError("source kernel generator transcript is not an original-domain permutation family")
    if not _valid_permutation_family(certificate.target_kernel_generators, n):
        raise ValueError("target kernel generator transcript is not an original-domain permutation family")

    external = _external_replay_log2_cost(certificate)
    stable = isfinite(external) and external >= 0.0
    return BlockActionKernelProofIdentity(
        schema="block-action-kernel-proof-identity-v1",
        solver_identity=("homogeneous_block_action_kernel_v1", "proof_dag_accounting_v1", 950),
        provenance_digest=provenance.certificate_digest,
        factorization_digest=certificate.certificate_digest,
        root_n=resolved_root,
        domain_degree=n,
        block_count=k,
        generator_count=int(certificate.generator_count),
        work_identity=(
            ("estimated_schreier_work_units", int(certificate.estimated_schreier_work_units)),
            ("work_cap", int(certificate.work_cap)),
            ("source_sift_levels", int(certificate.source_sift_levels)),
            ("target_sift_levels", int(certificate.target_sift_levels)),
        ),
        order_identity=(
            ("source_group_order", int(certificate.source_group_order)),
            ("target_group_order", int(certificate.target_group_order)),
            ("quotient_image_order", int(certificate.quotient_image_order)),
            ("source_kernel_order", int(certificate.source_kernel_order)),
            ("target_kernel_order", int(certificate.target_kernel_order)),
        ),
        source_kernel_generators=tuple(tuple(int(x) for x in perm) for perm in certificate.source_kernel_generators),
        target_kernel_generators=tuple(tuple(int(x) for x in perm) for perm in certificate.target_kernel_generators),
        external_log2_cost_bound=external,
        replay_stable=stable,
    )


def _terminal_proof(
    certificate: BlockActionKernelFactorization,
    identity: BlockActionKernelProofIdentity,
) -> BlockActionKernelTerminalProof:
    local = _local_log2_cost(certificate)
    accounting = RecurrenceAccountingNode(
        n=identity.root_n,
        m=identity.domain_degree,
        operation_kind="block_action_kernel_factorization_terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local,
        children=(),
        terminal_certified=True,
        reason="rev275 exact paired-Schreier factorization carries a preflight mechanical work bound",
    )
    return BlockActionKernelTerminalProof(
        status="exact_block_action_kernel_factorization_proof_terminal",
        coset=None,
        operation_kind="block_action_kernel_factorization_terminal",
        root_n=identity.root_n,
        domain_size=identity.domain_degree,
        canonical=True,
        exact=True,
        local_cost_certified=True,
        local_log2_cost_bound=local,
        terminal_certified=True,
        permutation_candidates_checked=int(certificate.estimated_schreier_work_units),
        reason="rev274 provenance and rev275 complete source/target kernel-image factorization replay exactly",
        children=(),
        accounting=accounting,
        proof_identity=identity,
    )


def validate_block_action_kernel_proof_identity(
    proof: BlockActionKernelTerminalProof,
    certificate: BlockActionKernelFactorization,
    provenance: BlockActionProvenance,
    expected: BlockActionKernelProofIdentity,
) -> BlockActionKernelIdentityValidation:
    if not isinstance(proof, BlockActionKernelTerminalProof):
        return BlockActionKernelIdentityValidation("wrong_block_action_kernel_proof_type", False, "proof is not the rev950 terminal proof type")
    actual = proof.proof_identity
    if actual is None:
        return BlockActionKernelIdentityValidation("missing_block_action_kernel_proof_identity", False, "proof has no execution-linked identity")
    if actual != expected:
        return BlockActionKernelIdentityValidation("mismatched_block_action_kernel_proof_identity", False, "attached rev950 identity differs from the replay-derived identity")
    if not actual.replay_stable or not isfinite(actual.external_log2_cost_bound) or actual.external_log2_cost_bound < 0.0:
        return BlockActionKernelIdentityValidation("unstable_block_action_kernel_proof_identity", False, "identity replay charge is not finite and nonnegative")
    if not replay_block_action_kernel_factorization(certificate, provenance):
        return BlockActionKernelIdentityValidation("block_action_kernel_replay_failed", False, "rev275 factorization no longer replays against rev274 provenance")
    local = _local_log2_cost(certificate)
    if not (
        proof.status == "exact_block_action_kernel_factorization_proof_terminal"
        and proof.operation_kind == "block_action_kernel_factorization_terminal"
        and proof.canonical
        and proof.exact
        and proof.local_cost_certified
        and proof.terminal_certified
        and not proof.children
        and proof.coset is None
        and proof.root_n == actual.root_n
        and proof.domain_size == actual.domain_degree
        and proof.permutation_candidates_checked == certificate.estimated_schreier_work_units
        and isfinite(proof.local_log2_cost_bound)
        and isclose(proof.local_log2_cost_bound, local, rel_tol=0.0, abs_tol=1e-12)
    ):
        return BlockActionKernelIdentityValidation("inconsistent_block_action_kernel_terminal_payload", False, "terminal proof payload differs from the frozen rev275 execution identity")
    accounting = proof.accounting
    if not (
        accounting.n == actual.root_n
        and accounting.m == actual.domain_degree
        and accounting.operation_kind == proof.operation_kind
        and accounting.canonical
        and accounting.cost_certified
        and accounting.terminal_certified
        and not accounting.children
        and isclose(accounting.local_log2_cost_bound, local, rel_tol=0.0, abs_tol=1e-12)
    ):
        return BlockActionKernelIdentityValidation("inconsistent_block_action_kernel_accounting", False, "terminal recurrence leaf differs from the replay-stable factorization identity")
    return BlockActionKernelIdentityValidation(
        "verified_block_action_kernel_proof_identity",
        True,
        "rev274 provenance, rev275 factorization digest/order/kernel transcript, mechanical work cap, and terminal accounting share one replay-stable identity",
    )


def block_action_kernel_proof_dag_consumer(
    provenance: BlockActionProvenance,
    certificate: BlockActionKernelFactorization,
    *,
    root_n: int | None = None,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> BlockActionKernelProofDAGConsumerResult:
    try:
        identity = build_block_action_kernel_proof_identity(certificate, provenance, root_n=root_n)
    except (TypeError, ValueError) as exc:
        return BlockActionKernelProofDAGConsumerResult(
            "rejected_block_action_kernel_identity",
            None,
            None,
            None,
            str(exc),
        )
    proof = _terminal_proof(certificate, identity)
    validation = validate_block_action_kernel_proof_identity(proof, certificate, provenance, identity)
    if not validation.certified:
        return BlockActionKernelProofDAGConsumerResult(validation.status, proof, validation, None, validation.reason)
    dag = validate_execution_proof_dag(
        proof,
        original_root_n=identity.root_n,
        external_log2_cost_bound=identity.external_log2_cost_bound,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not dag.certified:
        return BlockActionKernelProofDAGConsumerResult(dag.status, proof, validation, dag, dag.reason)
    return BlockActionKernelProofDAGConsumerResult(
        "certified_block_action_kernel_proof_dag",
        proof,
        validation,
        dag,
        "the main-integrated rev275 exact block-action kernel factorization is replay-stably named and conservatively occurrence-charged by the shared execution proof DAG, with independent replay charged externally",
    )


__all__ = [
    "BlockActionKernelProofIdentity",
    "BlockActionKernelTerminalProof",
    "BlockActionKernelIdentityValidation",
    "BlockActionKernelProofDAGConsumerResult",
    "build_block_action_kernel_proof_identity",
    "validate_block_action_kernel_proof_identity",
    "block_action_kernel_proof_dag_consumer",
]
