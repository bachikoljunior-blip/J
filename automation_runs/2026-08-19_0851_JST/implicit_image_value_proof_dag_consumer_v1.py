from __future__ import annotations

from dataclasses import dataclass, replace
from math import log2

from implicit_relation_image_action_v1 import ImplicitRelationImageAction
from implicit_relation_image_value_coset_v2 import (
    ImplicitRelationImageValueCoset,
    exact_implicit_relation_image_value_coset,
)
from proof_carrying_si_v1 import ProofCarryingCoset
from proof_dag_accounting_v1 import ProofDAGValidation, validate_execution_proof_dag
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from s1_proof_identity_v1 import _contains_opaque, _freeze_group, _freeze_identity_value


@dataclass(frozen=True)
class ImplicitImageValueProofIdentity:
    schema: str
    solver_identity: tuple[str, str, int]
    image_group_identity: tuple
    source_identity: tuple[object, ...]
    target_identity: tuple[object, ...]
    original_root_n: int
    auxiliary_degree: int
    resource_identity: tuple[tuple[str, int], ...]
    replay_stable: bool


@dataclass(frozen=True)
class ImplicitImageValueIdentityValidation:
    status: str
    certified: bool
    reason: str


@dataclass(frozen=True)
class ImplicitImageValueProofDAGConsumerResult:
    status: str
    value_coset: ImplicitRelationImageValueCoset | None
    proof: ProofCarryingCoset | None
    identity_validation: ImplicitImageValueIdentityValidation | None
    dag_validation: ProofDAGValidation | None
    reason: str


_EXACT_VALUE_STATUSES = {
    "exact_implicit_relation_image_value_coset",
    "exact_empty_feature_inventory_mismatch",
    "exact_empty_implicit_image_value_coset",
}


def build_implicit_image_value_identity(
    action: ImplicitRelationImageAction,
    *,
    original_root_n: int,
    max_partition_states: int = 200_000,
) -> ImplicitImageValueProofIdentity:
    """Freeze the exact rev262 value-coset phase input and resource gate."""
    if not isinstance(action, ImplicitRelationImageAction):
        raise TypeError("action must be an ImplicitRelationImageAction")
    if action.status != "exact_implicit_relation_image_paired_action" or action.image_group is None:
        raise ValueError("proof-DAG value-coset admission requires the exact rev257 image action")
    if isinstance(original_root_n, bool) or not isinstance(original_root_n, int) or original_root_n < 1:
        raise ValueError("original_root_n must be a positive integer")
    if (
        isinstance(max_partition_states, bool)
        or not isinstance(max_partition_states, int)
        or max_partition_states < 1
    ):
        raise ValueError("max_partition_states must be a positive integer")

    m = int(action.auxiliary_degree)
    if m < 1 or m > original_root_n + original_root_n * original_root_n:
        raise ValueError("auxiliary degree must fit the explicit n+n^2 polynomial lift")
    source_identity = tuple(_freeze_identity_value(x) for x in action.source_features)
    target_identity = tuple(_freeze_identity_value(x) for x in action.target_features)
    resources = (("max_partition_states", int(max_partition_states)),)
    return ImplicitImageValueProofIdentity(
        "implicit-image-value-proof-identity-v1",
        ("implicit_relation_image_value_coset_v2", "proof_dag_accounting_v1", 271),
        _freeze_group(action.image_group),
        source_identity,
        target_identity,
        int(original_root_n),
        m,
        resources,
        not any(_contains_opaque(x) for x in source_identity + target_identity),
    )


def _local_log2_cost_bound(action: ImplicitRelationImageAction, result: ImplicitRelationImageValueCoset) -> float:
    """Conservatively charge the bounded ordered-partition phase only.

    The rev257 image action is an already-constructed input.  For rev262, every
    recorded partition state is processed through the supplied image generators
    on an auxiliary domain of size m; the deliberately loose m^32 factor also
    dominates Schreier membership/stabilizer reconstruction bookkeeping.
    """
    m = max(2, int(action.auxiliary_degree))
    generator_count = max(1, len(action.image_group.original_generators))
    states = max(1, int(result.partition_orbit_states))
    return log2(states) + log2(generator_count) + 32.0 * log2(m) + 64.0


def _proof_from_exact_result(
    action: ImplicitRelationImageAction,
    result: ImplicitRelationImageValueCoset,
    identity: ImplicitImageValueProofIdentity,
) -> ProofCarryingCoset:
    if result.status not in _EXACT_VALUE_STATUSES or not result.exact or not result.complete:
        raise ValueError("only a complete exact rev262 value-coset result may become a DAG proof")
    if result.auxiliary_degree != identity.auxiliary_degree:
        raise ValueError("rev262 result auxiliary degree differs from the frozen identity")
    local_bound = _local_log2_cost_bound(action, result)
    accounting = RecurrenceAccountingNode(
        n=identity.auxiliary_degree,
        m=identity.auxiliary_degree,
        operation_kind="implicit_image_value_coset_terminal",
        canonical=True,
        cost_certified=True,
        local_log2_cost_bound=local_bound,
        children=(),
        terminal_certified=True,
        reason="complete bounded ordered-partition transporter phase with execution-linked state count",
    )
    return ProofCarryingCoset(
        result.status,
        result.coset,
        "implicit_image_value_coset_terminal",
        identity.auxiliary_degree,
        identity.auxiliary_degree,
        True,
        True,
        True,
        local_bound,
        True,
        (),
        accounting,
        int(result.partition_orbit_states),
        result.reason,
        identity,
    )


def validate_implicit_image_value_identity(
    proof: ProofCarryingCoset,
    expected: ImplicitImageValueProofIdentity,
) -> ImplicitImageValueIdentityValidation:
    actual = getattr(proof, "proof_identity", None)
    if actual is None:
        return ImplicitImageValueIdentityValidation(
            "missing_implicit_image_value_proof_identity", False,
            "the rev262 terminal proof has no execution-linked identity",
        )
    if not isinstance(actual, ImplicitImageValueProofIdentity):
        return ImplicitImageValueIdentityValidation(
            "wrong_implicit_image_value_proof_identity_type", False,
            "the attached identity is not ImplicitImageValueProofIdentity v1",
        )
    if actual != expected:
        return ImplicitImageValueIdentityValidation(
            "mismatched_implicit_image_value_proof_identity", False,
            "image group, feature strings, root, auxiliary lift, solver version, or partition cap differs",
        )
    if not actual.replay_stable:
        return ImplicitImageValueIdentityValidation(
            "unstable_opaque_implicit_image_value_identity", False,
            "opaque feature values do not provide a replay-stable proof-DAG identity",
        )
    if proof.status not in _EXACT_VALUE_STATUSES or not proof.exact:
        return ImplicitImageValueIdentityValidation(
            "nonexact_implicit_image_value_execution", False,
            "only the three complete exact rev262 value-coset statuses are admissible",
        )
    if not (
        proof.canonical
        and proof.local_cost_certified
        and proof.terminal_certified
        and proof.operation_kind == "implicit_image_value_coset_terminal"
    ):
        return ImplicitImageValueIdentityValidation(
            "uncertified_implicit_image_value_execution", False,
            "the value-coset phase lacks canonical terminal execution/accounting certification",
        )
    if proof.root_n != actual.auxiliary_degree or proof.domain_size != actual.auxiliary_degree:
        return ImplicitImageValueIdentityValidation(
            "inconsistent_implicit_image_value_proof_measure", False,
            "the proof recurrence measure differs from its frozen auxiliary-domain identity",
        )
    return ImplicitImageValueIdentityValidation(
        "verified_implicit_image_value_proof_identity", True,
        "the complete exact rev262 value-coset phase carries the expected replay-stable execution identity",
    )


def implicit_image_value_proof_dag_consumer(
    action: ImplicitRelationImageAction,
    *,
    original_root_n: int,
    max_partition_states: int = 200_000,
    external_log2_cost_bound: float = 0.0,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> ImplicitImageValueProofDAGConsumerResult:
    """Run rev262 and admit only its exact value-coset phase to the shared DAG.

    This wrapper deliberately does not charge or certify construction of the
    supplied rev257 action.  A caller may add a separately certified prefix via
    ``external_log2_cost_bound``.  The rev262 auxiliary lift is accepted only
    when it fits n+n^2, and nonexact, incomplete, or opaque executions fail closed.
    """
    expected = build_implicit_image_value_identity(
        action,
        original_root_n=original_root_n,
        max_partition_states=max_partition_states,
    )
    if not expected.replay_stable:
        return ImplicitImageValueProofDAGConsumerResult(
            "unstable_opaque_implicit_image_value_identity", None, None, None, None,
            "opaque feature values are rejected before executing the proof-DAG value-coset phase",
        )
    if external_log2_cost_bound < 0:
        raise ValueError("external_log2_cost_bound must be nonnegative")

    result = exact_implicit_relation_image_value_coset(
        action, max_partition_states=max_partition_states
    )
    if result.status not in _EXACT_VALUE_STATUSES or not result.exact or not result.complete:
        return ImplicitImageValueProofDAGConsumerResult(
            "underlying_implicit_image_value_phase_not_exact",
            result,
            None,
            None,
            None,
            "rev262 did not return one of its complete exact value-coset outcomes; no DAG identity is attached",
        )

    proof = _proof_from_exact_result(action, result, expected)
    identity_validation = validate_implicit_image_value_identity(proof, expected)
    if not identity_validation.certified:
        return ImplicitImageValueProofDAGConsumerResult(
            identity_validation.status, result, replace(proof, proof_identity=None),
            identity_validation, None, identity_validation.reason,
        )

    dag_validation = validate_execution_proof_dag(
        proof,
        original_root_n=int(original_root_n),
        polynomial_lift_degree=(
            expected.auxiliary_degree
            if expected.auxiliary_degree > int(original_root_n)
            else None
        ),
        external_log2_cost_bound=float(external_log2_cost_bound),
        quasipoly_power=int(quasipoly_power),
        quasipoly_constant=float(quasipoly_constant),
    )
    if not dag_validation.certified:
        return ImplicitImageValueProofDAGConsumerResult(
            dag_validation.status, result, proof, identity_validation,
            dag_validation, dag_validation.reason,
        )
    return ImplicitImageValueProofDAGConsumerResult(
        "certified_implicit_image_value_proof_dag",
        result,
        proof,
        identity_validation,
        dag_validation,
        "the complete exact rev262 value-coset phase is replay-stably identified and conservatively charged by the shared execution proof DAG",
    )


__all__ = [
    "ImplicitImageValueProofIdentity",
    "ImplicitImageValueIdentityValidation",
    "ImplicitImageValueProofDAGConsumerResult",
    "build_implicit_image_value_identity",
    "validate_implicit_image_value_identity",
    "implicit_image_value_proof_dag_consumer",
]
