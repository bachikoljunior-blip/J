from __future__ import annotations

from dataclasses import dataclass, replace
from math import isclose, isfinite, log2
from numbers import Integral

from proof_dag_accounting_v1 import ProofDAGValidation, validate_execution_proof_dag
from s1_proof_identity_v1 import _contains_opaque, _freeze_group, _freeze_identity_value
from signed_johnson_ground_relational_si_v1 import (
    SignedJohnsonGroundRelationalProof,
    signed_johnson_ground_relational_small_order_terminal,
)


_EXACT_STATUSES = frozenset(
    {
        "exact_signed_johnson_ground_relation_coset",
        "exact_empty_signed_johnson_ground_relation",
    }
)


@dataclass(frozen=True)
class SignedJohnsonGroundProofIdentity:
    schema: str
    solver_identity: tuple[str, str, int]
    group_identity: tuple
    source_identity: tuple[object, ...]
    target_identity: tuple[object, ...]
    root_n: int
    domain_size: int
    ground_size: int
    subset_size: int
    certified_signed_group_order: int
    signed_elements_checked: int
    recognition_search_nodes: int
    local_log2_cost_bound: float
    terminal_status: str
    resource_identity: tuple[tuple[str, int], ...]
    replay_stable: bool


@dataclass(frozen=True)
class SignedJohnsonGroundIdentityValidation:
    status: str
    certified: bool
    reason: str


@dataclass(frozen=True)
class SignedJohnsonGroundProofDAGConsumerResult:
    status: str
    proof: SignedJohnsonGroundRelationalProof
    identity_validation: SignedJohnsonGroundIdentityValidation | None
    dag_validation: ProofDAGValidation | None
    reason: str


def _strict_int(value, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError("resource parameters must be strict integers")
    value = int(value)
    if value < minimum:
        raise ValueError("resource parameter is below its minimum")
    return value


def _expected_local_log2_cost(*, group_order: int, domain_size: int, subset_size: int, ground_size: int) -> float:
    execution_units = max(1, group_order * max(1, domain_size) * max(1, subset_size))
    return (
        log2(execution_units)
        + 16.0 * log2(max(2, ground_size))
        + 12.0 * log2(max(2, domain_size))
        + 32.0
    )


def build_signed_johnson_ground_identity(
    group,
    source_values,
    target_values,
    proof: SignedJohnsonGroundRelationalProof,
    *,
    root_n: int,
    group_order_poly_power: int = 2,
    max_group_order: int = 4096,
    max_recognition_nodes: int = 500000,
) -> SignedJohnsonGroundProofIdentity:
    """Freeze the deterministic input, resource, and exact rev176 terminal payload."""
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    root_n = _strict_int(root_n, minimum=1)
    group_order_poly_power = _strict_int(group_order_poly_power, minimum=1)
    max_group_order = _strict_int(max_group_order, minimum=1)
    max_recognition_nodes = _strict_int(max_recognition_nodes, minimum=1)
    if len(source) != n or len(target) != n:
        raise ValueError("signed Johnson identity requires full domain strings")
    if root_n < n:
        raise ValueError("root_n must dominate the signed Johnson point domain")
    if proof.status not in _EXACT_STATUSES or not proof.exact:
        raise ValueError("only an exact rev176 terminal may receive a proof-DAG identity")

    source_identity = tuple(_freeze_identity_value(x) for x in source)
    target_identity = tuple(_freeze_identity_value(x) for x in target)
    local_bound = float(proof.local_log2_cost_bound)
    replay_stable = (
        not any(_contains_opaque(x) for x in source_identity + target_identity)
        and isfinite(local_bound)
    )
    return SignedJohnsonGroundProofIdentity(
        "signed-johnson-ground-proof-identity-v1",
        ("signed_johnson_ground_relational_si_v1", "proof_dag_accounting_v1", 295),
        _freeze_group(group),
        source_identity,
        target_identity,
        root_n,
        n,
        int(proof.ground_size),
        int(proof.subset_size),
        int(proof.certified_signed_group_order),
        int(proof.signed_elements_checked),
        int(proof.recognition_search_nodes),
        local_bound,
        str(proof.status),
        (
            ("group_order_poly_power", group_order_poly_power),
            ("max_group_order", max_group_order),
            ("max_recognition_nodes", max_recognition_nodes),
        ),
        replay_stable,
    )


def validate_signed_johnson_ground_identity(
    proof: SignedJohnsonGroundRelationalProof,
    expected: SignedJohnsonGroundProofIdentity,
) -> SignedJohnsonGroundIdentityValidation:
    """Replay the exact rev176 terminal shape against its immutable execution identity."""
    actual = getattr(proof, "proof_identity", None)
    if actual is None:
        return SignedJohnsonGroundIdentityValidation(
            "missing_signed_johnson_ground_proof_identity",
            False,
            "the signed Johnson terminal proof has no execution-linked identity",
        )
    if not isinstance(actual, SignedJohnsonGroundProofIdentity):
        return SignedJohnsonGroundIdentityValidation(
            "wrong_signed_johnson_ground_proof_identity_type",
            False,
            "the attached identity is not SignedJohnsonGroundProofIdentity v1",
        )
    if actual != expected:
        return SignedJohnsonGroundIdentityValidation(
            "mismatched_signed_johnson_ground_proof_identity",
            False,
            "group, strings, root, solver version, resource gates, or exact terminal payload differs",
        )
    if not actual.replay_stable:
        return SignedJohnsonGroundIdentityValidation(
            "unstable_signed_johnson_ground_proof_identity",
            False,
            "opaque values or a non-finite terminal charge cannot name a replay-stable shared proof",
        )
    if proof.status not in _EXACT_STATUSES or not proof.exact:
        return SignedJohnsonGroundIdentityValidation(
            "nonexact_signed_johnson_ground_execution",
            False,
            "only the complete exact rev176 signed-ground terminal may enter the shared proof DAG",
        )
    if not (
        proof.canonical
        and proof.local_cost_certified
        and proof.terminal_certified
        and proof.operation_kind == "signed_johnson_ground_relational_terminal"
        and not proof.children
    ):
        return SignedJohnsonGroundIdentityValidation(
            "uncertified_signed_johnson_ground_execution",
            False,
            "the signed-ground terminal lacks canonical exact execution/accounting certification",
        )
    if (
        proof.root_n != actual.root_n
        or proof.domain_size != actual.domain_size
        or proof.ground_size != actual.ground_size
        or proof.subset_size != actual.subset_size
        or proof.certified_signed_group_order != actual.certified_signed_group_order
        or proof.signed_elements_checked != actual.signed_elements_checked
        or proof.recognition_search_nodes != actual.recognition_search_nodes
        or proof.status != actual.terminal_status
    ):
        return SignedJohnsonGroundIdentityValidation(
            "inconsistent_signed_johnson_ground_proof_measure",
            False,
            "the exposed exact proof fields differ from the frozen execution identity",
        )
    if actual.certified_signed_group_order < 1 or actual.ground_size < 1 or actual.subset_size < 1:
        return SignedJohnsonGroundIdentityValidation(
            "invalid_signed_johnson_ground_structural_payload",
            False,
            "the exact terminal must expose positive certified group and Johnson-ground parameters",
        )
    if actual.subset_size > actual.ground_size:
        return SignedJohnsonGroundIdentityValidation(
            "invalid_signed_johnson_ground_structural_payload",
            False,
            "the Johnson subset size cannot exceed the certified ground size",
        )

    resources = dict(actual.resource_identity)
    allowed_order = min(
        int(resources["max_group_order"]),
        int(actual.root_n) ** int(resources["group_order_poly_power"]),
    )
    if actual.certified_signed_group_order > allowed_order:
        return SignedJohnsonGroundIdentityValidation(
            "signed_johnson_ground_order_gate_drift",
            False,
            "an exact execution cannot exceed the frozen polynomial/hard group-order gate",
        )

    expected_checked = actual.certified_signed_group_order
    if actual.terminal_status == "exact_signed_johnson_ground_relation_coset":
        expected_checked *= 2
        if proof.coset is None or proof.coset.subgroup.degree != actual.domain_size:
            return SignedJohnsonGroundIdentityValidation(
                "invalid_signed_johnson_ground_nonempty_coset",
                False,
                "the exact nonempty status must carry an original-domain right coset",
            )
    elif proof.coset is not None:
        return SignedJohnsonGroundIdentityValidation(
            "invalid_signed_johnson_ground_empty_coset",
            False,
            "the exact-empty status must not carry a right coset",
        )
    if actual.signed_elements_checked != expected_checked:
        return SignedJohnsonGroundIdentityValidation(
            "signed_johnson_ground_execution_count_drift",
            False,
            "the recorded exact execution count no longer matches rev176's full scan/audit contract",
        )

    expected_local = _expected_local_log2_cost(
        group_order=actual.certified_signed_group_order,
        domain_size=actual.domain_size,
        subset_size=actual.subset_size,
        ground_size=actual.ground_size,
    )
    if not (
        isfinite(actual.local_log2_cost_bound)
        and isclose(actual.local_log2_cost_bound, expected_local, rel_tol=0.0, abs_tol=1e-10)
        and isclose(float(proof.local_log2_cost_bound), expected_local, rel_tol=0.0, abs_tol=1e-10)
    ):
        return SignedJohnsonGroundIdentityValidation(
            "signed_johnson_ground_local_cost_drift",
            False,
            "the terminal charge differs from rev176's mechanically derived full signed-group scan bound",
        )

    accounting = proof.accounting
    if not (
        accounting.n == actual.root_n
        and accounting.m == actual.ground_size
        and accounting.operation_kind == "signed_johnson_ground_relational_terminal"
        and accounting.canonical
        and accounting.cost_certified
        and accounting.terminal_certified
        and not accounting.children
        and isclose(float(accounting.local_log2_cost_bound), expected_local, rel_tol=0.0, abs_tol=1e-10)
    ):
        return SignedJohnsonGroundIdentityValidation(
            "inconsistent_signed_johnson_ground_accounting",
            False,
            "the recurrence leaf differs from the exact terminal identity or mechanical charge",
        )
    return SignedJohnsonGroundIdentityValidation(
        "verified_signed_johnson_ground_proof_identity",
        True,
        "the exact rev176 signed-ground terminal carries a complete replay-stable execution and cost identity",
    )


def signed_johnson_ground_proof_dag_consumer(
    group,
    source_values,
    target_values,
    *,
    root_n: int,
    group_order_poly_power: int = 2,
    max_group_order: int = 4096,
    max_recognition_nodes: int = 500000,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> SignedJohnsonGroundProofDAGConsumerResult:
    """Run rev176 and admit only replay-stable exact outcomes to the shared proof DAG."""
    source = tuple(source_values)
    target = tuple(target_values)
    proof = signed_johnson_ground_relational_small_order_terminal(
        group,
        source,
        target,
        root_n=root_n,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_recognition_nodes=max_recognition_nodes,
    )
    if not proof.exact:
        return SignedJohnsonGroundProofDAGConsumerResult(
            "underlying_signed_johnson_ground_terminal_not_exact",
            proof,
            None,
            None,
            "rev176 did not produce complete exact evidence; no reusable proof identity is attached",
        )

    expected = build_signed_johnson_ground_identity(
        group,
        source,
        target,
        proof,
        root_n=root_n,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_recognition_nodes=max_recognition_nodes,
    )
    attached = replace(proof, proof_identity=expected)
    identity_validation = validate_signed_johnson_ground_identity(attached, expected)
    if not identity_validation.certified:
        return SignedJohnsonGroundProofDAGConsumerResult(
            identity_validation.status,
            proof,
            identity_validation,
            None,
            identity_validation.reason,
        )

    dag_validation = validate_execution_proof_dag(
        attached,
        original_root_n=root_n,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not dag_validation.certified:
        return SignedJohnsonGroundProofDAGConsumerResult(
            dag_validation.status,
            attached,
            identity_validation,
            dag_validation,
            dag_validation.reason,
        )
    return SignedJohnsonGroundProofDAGConsumerResult(
        "certified_signed_johnson_ground_proof_dag",
        attached,
        identity_validation,
        dag_validation,
        "the exact rev176 signed Johnson ground terminal is replay-stably identified and conservatively occurrence-charged by the shared execution proof DAG",
    )


__all__ = [
    "SignedJohnsonGroundProofIdentity",
    "SignedJohnsonGroundIdentityValidation",
    "SignedJohnsonGroundProofDAGConsumerResult",
    "build_signed_johnson_ground_identity",
    "validate_signed_johnson_ground_identity",
    "signed_johnson_ground_proof_dag_consumer",
]
