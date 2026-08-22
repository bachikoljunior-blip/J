from __future__ import annotations

from dataclasses import dataclass, replace
from math import factorial

from literal_giant_candidate_si_v1 import exact_literal_giant_string_isomorphism
from proof_dag_accounting_v1 import validate_execution_proof_dag
from s1_proof_identity_v1 import _contains_opaque, _freeze_group, _freeze_identity_value


_EXACT_STATUSES = frozenset(
    {
        "exact_literal_giant_string_isomorphism",
        "exact_empty_literal_giant_value_multiplicity",
        "exact_empty_literal_alternating_parity",
    }
)


@dataclass(frozen=True)
class LiteralGiantProofIdentity:
    schema: str
    solver_identity: tuple[str, str, int]
    group_identity: tuple
    group_type: str
    source_identity: tuple[object, ...]
    target_identity: tuple[object, ...]
    root_n: int
    domain_size: int
    resource_identity: tuple[tuple[str, object], ...]
    replay_stable: bool


@dataclass(frozen=True)
class LiteralGiantIdentityValidation:
    status: str
    certified: bool
    reason: str


@dataclass(frozen=True)
class LiteralGiantProofDAGAdmission:
    status: str
    certified: bool
    proof: object
    dag_validation: object | None
    reason: str


def _literal_group_type(group) -> str:
    n = int(group.degree)
    if n < 5:
        return "none"
    full = factorial(n)
    if int(group.order) == full:
        return "S_n"
    if int(group.order) * 2 == full:
        return "A_n"
    return "none"


def build_literal_giant_proof_identity(
    group,
    source_values,
    target_values,
    *,
    root_n: int,
) -> LiteralGiantProofIdentity:
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    root_n = int(root_n)
    if len(source) != n or len(target) != n:
        raise ValueError("literal giant proof identity requires full domain strings")
    if root_n < n or root_n < 1:
        raise ValueError("root_n must be positive and dominate the literal giant degree")

    source_identity = tuple(_freeze_identity_value(value) for value in source)
    target_identity = tuple(_freeze_identity_value(value) for value in target)
    resources = (
        ("minimum_literal_giant_degree", 5),
        ("local_cost_formula", "40*log2(max(2,n))+48"),
        ("producer_schema", "literal_giant_candidate_si_v1"),
        ("proof_dag_schema", "proof_dag_accounting_v1"),
    )
    return LiteralGiantProofIdentity(
        "literal-giant-proof-identity-v1",
        ("literal_giant_candidate_si_v1", "exact_literal_giant_string_isomorphism", 1),
        _freeze_group(group),
        _literal_group_type(group),
        source_identity,
        target_identity,
        root_n,
        n,
        resources,
        not any(_contains_opaque(value) for value in source_identity + target_identity),
    )


def _attach_identity_if_exact(proof, identity: LiteralGiantProofIdentity):
    if proof.status not in _EXACT_STATUSES:
        return proof
    if not (
        proof.exact
        and proof.canonical
        and proof.local_cost_certified
        and proof.terminal_certified
        and proof.operation_kind == "literal_giant_color_transport"
    ):
        return proof
    return replace(proof, proof_identity=identity)


def validate_literal_giant_proof_identity(
    proof,
    expected: LiteralGiantProofIdentity,
) -> LiteralGiantIdentityValidation:
    actual = getattr(proof, "proof_identity", None)
    if actual is None:
        return LiteralGiantIdentityValidation(
            "missing_literal_giant_proof_identity",
            False,
            "only a complete exact literal-giant terminal may carry the proof-DAG identity",
        )
    if not isinstance(actual, LiteralGiantProofIdentity):
        return LiteralGiantIdentityValidation(
            "wrong_literal_giant_proof_identity_type",
            False,
            "the attached identity is not the rev280 literal-giant identity schema",
        )
    if actual != expected:
        return LiteralGiantIdentityValidation(
            "mismatched_literal_giant_proof_identity",
            False,
            "group, string orientation, root, solver version, or resource identity differs",
        )
    if not actual.replay_stable:
        return LiteralGiantIdentityValidation(
            "unstable_opaque_literal_giant_identity",
            False,
            "opaque values do not have a process-stable mathematical identity and cannot be shared in the proof DAG",
        )
    if actual.group_type not in {"S_n", "A_n"}:
        return LiteralGiantIdentityValidation(
            "nonliteral_group_identity",
            False,
            "the frozen represented group is not a literal natural-domain symmetric or alternating giant",
        )
    if proof.status not in _EXACT_STATUSES:
        return LiteralGiantIdentityValidation(
            "nonexact_literal_giant_status",
            False,
            "the producer status is not one of the complete exact literal-giant terminals",
        )
    if not (
        proof.exact
        and proof.canonical
        and proof.local_cost_certified
        and proof.terminal_certified
        and proof.operation_kind == "literal_giant_color_transport"
    ):
        return LiteralGiantIdentityValidation(
            "incomplete_literal_giant_terminal_certificate",
            False,
            "exactness, canonicality, local cost, terminality, and operation kind must all match the rev208 terminal contract",
        )
    if int(proof.root_n) != actual.root_n or int(proof.domain_size) != actual.domain_size:
        return LiteralGiantIdentityValidation(
            "literal_giant_measure_mismatch",
            False,
            "the exposed proof recurrence measure differs from the frozen identity",
        )
    if proof.accounting.n != proof.root_n or proof.accounting.m != max(1, proof.domain_size):
        return LiteralGiantIdentityValidation(
            "literal_giant_accounting_measure_mismatch",
            False,
            "the producer accounting root/domain does not match the proof object",
        )
    if proof.accounting.operation_kind != proof.operation_kind:
        return LiteralGiantIdentityValidation(
            "literal_giant_accounting_operation_mismatch",
            False,
            "the accounting node is not execution-linked to the literal-giant operation",
        )
    if abs(float(proof.accounting.local_log2_cost_bound) - float(proof.local_log2_cost_bound)) > 1e-12:
        return LiteralGiantIdentityValidation(
            "literal_giant_accounting_cost_mismatch",
            False,
            "the proof and accounting objects disagree on the certified local execution charge",
        )
    if proof.children or proof.accounting.children:
        return LiteralGiantIdentityValidation(
            "literal_giant_terminal_has_children",
            False,
            "the direct literal-giant terminal must remain a leaf in both proof and accounting trees",
        )
    if proof.status == "exact_literal_giant_string_isomorphism" and proof.coset is None:
        return LiteralGiantIdentityValidation(
            "literal_giant_nonempty_status_without_coset",
            False,
            "the exact nonempty literal-giant status requires a complete right coset",
        )
    if proof.status.startswith("exact_empty_") and proof.coset is not None:
        return LiteralGiantIdentityValidation(
            "literal_giant_empty_status_with_coset",
            False,
            "an exact-empty literal-giant status must not carry a coset",
        )
    return LiteralGiantIdentityValidation(
        "verified_literal_giant_proof_identity",
        True,
        "the complete exact rev208 literal-giant terminal is bound to the expected replay-stable execution identity",
    )


def certify_literal_giant_execution_proof_dag(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    external_log2_cost_bound: float = 0.0,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> LiteralGiantProofDAGAdmission:
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    if root_n is None:
        root_n = n
    root_n = int(root_n)

    proof = exact_literal_giant_string_isomorphism(
        group,
        source,
        target,
        root_n=root_n,
    )
    expected = build_literal_giant_proof_identity(
        group,
        source,
        target,
        root_n=root_n,
    )
    proof = _attach_identity_if_exact(proof, expected)
    identity_validation = validate_literal_giant_proof_identity(proof, expected)
    if not identity_validation.certified:
        return LiteralGiantProofDAGAdmission(
            identity_validation.status,
            False,
            proof,
            None,
            identity_validation.reason,
        )

    dag_validation = validate_execution_proof_dag(
        proof,
        original_root_n=root_n,
        external_log2_cost_bound=float(external_log2_cost_bound),
        quasipoly_power=int(quasipoly_power),
        quasipoly_constant=float(quasipoly_constant),
    )
    return LiteralGiantProofDAGAdmission(
        dag_validation.status,
        bool(dag_validation.certified),
        proof,
        dag_validation,
        dag_validation.reason,
    )


__all__ = [
    "LiteralGiantIdentityValidation",
    "LiteralGiantProofDAGAdmission",
    "LiteralGiantProofIdentity",
    "build_literal_giant_proof_identity",
    "certify_literal_giant_execution_proof_dag",
    "validate_literal_giant_proof_identity",
]
