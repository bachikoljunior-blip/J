from __future__ import annotations

from dataclasses import dataclass, replace

from primitive_johnson_ground_terminal_v1 import (
    PrimitiveJohnsonGroundProof,
    primitive_johnson_ground_string_isomorphism_terminal,
)
from proof_dag_accounting_v1 import ProofDAGValidation, validate_execution_proof_dag
from s1_proof_identity_v1 import _contains_opaque, _freeze_group, _freeze_identity_value


@dataclass(frozen=True)
class PrimitiveJohnsonGroundProofIdentity:
    schema: str
    solver_identity: tuple[str, str, int]
    group_identity: tuple
    source_identity: tuple[object, ...]
    target_identity: tuple[object, ...]
    root_n: int
    domain_size: int
    resource_identity: tuple[tuple[str, int], ...]
    replay_stable: bool


@dataclass(frozen=True)
class PrimitiveJohnsonIdentityValidation:
    status: str
    certified: bool
    reason: str


@dataclass(frozen=True)
class PrimitiveJohnsonProofDAGConsumerResult:
    status: str
    proof: PrimitiveJohnsonGroundProof
    identity_validation: PrimitiveJohnsonIdentityValidation | None
    dag_validation: ProofDAGValidation | None
    reason: str


def build_primitive_johnson_ground_identity(
    group,
    source_values,
    target_values,
    *,
    root_n: int,
    polylog_power: int = 2,
    max_ground_degree: int = 8,
    max_recognition_nodes: int = 500000,
) -> PrimitiveJohnsonGroundProofIdentity:
    """Freeze the complete deterministic input/resource identity for the terminal."""
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    if len(source) != n or len(target) != n:
        raise ValueError("primitive Johnson identity requires full domain strings")
    if root_n < n or root_n <= 0:
        raise ValueError("root_n must dominate the primitive Johnson identity domain")
    if polylog_power < 1 or max_ground_degree < 1 or max_recognition_nodes < 1:
        raise ValueError("invalid primitive Johnson identity resource parameter")

    source_identity = tuple(_freeze_identity_value(x) for x in source)
    target_identity = tuple(_freeze_identity_value(x) for x in target)
    resources = (
        ("polylog_power", int(polylog_power)),
        ("max_ground_degree", int(max_ground_degree)),
        ("max_recognition_nodes", int(max_recognition_nodes)),
    )
    return PrimitiveJohnsonGroundProofIdentity(
        "primitive-johnson-ground-proof-identity-v1",
        ("primitive_johnson_ground_terminal_v1", "proof_dag_accounting_v1", 264),
        _freeze_group(group),
        source_identity,
        target_identity,
        int(root_n),
        n,
        resources,
        not any(_contains_opaque(x) for x in source_identity + target_identity),
    )


def validate_primitive_johnson_ground_identity(
    proof: PrimitiveJohnsonGroundProof,
    expected: PrimitiveJohnsonGroundProofIdentity,
) -> PrimitiveJohnsonIdentityValidation:
    """Validate that an exact terminal proof carries exactly the frozen execution identity."""
    actual = getattr(proof, "proof_identity", None)
    if actual is None:
        return PrimitiveJohnsonIdentityValidation(
            "missing_primitive_johnson_proof_identity",
            False,
            "the primitive Johnson terminal proof has no execution-linked identity",
        )
    if not isinstance(actual, PrimitiveJohnsonGroundProofIdentity):
        return PrimitiveJohnsonIdentityValidation(
            "wrong_primitive_johnson_proof_identity_type",
            False,
            "the attached identity is not PrimitiveJohnsonGroundProofIdentity v1",
        )
    if actual != expected:
        return PrimitiveJohnsonIdentityValidation(
            "mismatched_primitive_johnson_proof_identity",
            False,
            "group, strings, root, solver version, or a resource gate differs",
        )
    if not actual.replay_stable:
        return PrimitiveJohnsonIdentityValidation(
            "unstable_opaque_primitive_johnson_identity",
            False,
            "opaque values do not have a process-stable mathematical snapshot; DAG reuse fails closed",
        )
    if not proof.exact:
        return PrimitiveJohnsonIdentityValidation(
            "nonexact_primitive_johnson_execution",
            False,
            "only an exact primitive Johnson execution may enter the shared proof DAG",
        )
    if not (
        proof.canonical
        and proof.local_cost_certified
        and proof.terminal_certified
        and proof.operation_kind == "primitive_johnson_ground_terminal"
    ):
        return PrimitiveJohnsonIdentityValidation(
            "uncertified_primitive_johnson_execution",
            False,
            "the terminal lacks canonical exact execution/accounting certification",
        )
    if proof.root_n != actual.root_n or proof.domain_size != actual.domain_size:
        return PrimitiveJohnsonIdentityValidation(
            "inconsistent_primitive_johnson_proof_measure",
            False,
            "the proof recurrence measure differs from its frozen execution identity",
        )
    return PrimitiveJohnsonIdentityValidation(
        "verified_primitive_johnson_proof_identity",
        True,
        "the exact bounded primitive Johnson terminal carries the complete expected execution identity",
    )


def primitive_johnson_ground_proof_dag_consumer(
    group,
    source_values,
    target_values,
    *,
    root_n: int,
    polylog_power: int = 2,
    max_ground_degree: int = 8,
    max_recognition_nodes: int = 500000,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> PrimitiveJohnsonProofDAGConsumerResult:
    """Run the exact terminal and admit only replay-stable exact proofs to rev220's DAG.

    The mathematical terminal is unchanged. This wrapper freezes the input and every
    terminal resource gate before execution, attaches that identity only to an exact,
    replay-stable result, validates the attachment, and then delegates conservative
    occurrence charging to ``validate_execution_proof_dag``.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    expected = build_primitive_johnson_ground_identity(
        group,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_ground_degree=max_ground_degree,
        max_recognition_nodes=max_recognition_nodes,
    )
    proof = primitive_johnson_ground_string_isomorphism_terminal(
        group,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_ground_degree=max_ground_degree,
        max_recognition_nodes=max_recognition_nodes,
    )
    if not proof.exact:
        return PrimitiveJohnsonProofDAGConsumerResult(
            "underlying_primitive_johnson_terminal_not_exact",
            proof,
            None,
            None,
            "the bounded primitive Johnson terminal did not produce exact evidence; no DAG identity is attached",
        )

    attached = replace(proof, proof_identity=expected)
    identity_validation = validate_primitive_johnson_ground_identity(attached, expected)
    if not identity_validation.certified:
        # Do not expose an unstable or otherwise invalid identity as a reusable proof object.
        return PrimitiveJohnsonProofDAGConsumerResult(
            identity_validation.status,
            proof,
            identity_validation,
            None,
            identity_validation.reason,
        )

    dag_validation = validate_execution_proof_dag(
        attached,
        original_root_n=int(root_n),
        quasipoly_power=int(quasipoly_power),
        quasipoly_constant=float(quasipoly_constant),
    )
    if not dag_validation.certified:
        return PrimitiveJohnsonProofDAGConsumerResult(
            dag_validation.status,
            attached,
            identity_validation,
            dag_validation,
            dag_validation.reason,
        )
    return PrimitiveJohnsonProofDAGConsumerResult(
        "certified_primitive_johnson_proof_dag",
        attached,
        identity_validation,
        dag_validation,
        "the exact primitive Johnson terminal is replay-stably identified and conservatively charged by the shared execution proof DAG",
    )


__all__ = [
    "PrimitiveJohnsonGroundProofIdentity",
    "PrimitiveJohnsonIdentityValidation",
    "PrimitiveJohnsonProofDAGConsumerResult",
    "build_primitive_johnson_ground_identity",
    "validate_primitive_johnson_ground_identity",
    "primitive_johnson_ground_proof_dag_consumer",
]
