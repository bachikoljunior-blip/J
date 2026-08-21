from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log2

from proof_dag_accounting_v1 import (
    ProofDAGNode,
    build_proof_dag_artifact,
    validate_execution_proof_dag,
)
from quasipoly_recurrence_accounting_v1 import _log2_sum_exp


@dataclass(frozen=True)
class DesignChildProofDAGCoverValidation:
    status: str
    certified: bool
    branch_count: int
    validated_branch_count: int
    failed_branch_index: int | None
    unique_nodes: int
    execution_occurrences: int
    reused_occurrences: int
    cross_branch_reused_nodes: int
    branch_log2_work_bounds: tuple[float, ...]
    combined_child_log2_work_bound: float
    external_log2_cost_bound: float
    total_log2_work_bound: float
    allowed_log2_work: float
    reason: str


def _result(
    status: str,
    certified: bool,
    *,
    branch_count: int,
    validated_branch_count: int = 0,
    failed_branch_index: int | None = None,
    unique_nodes: int = 0,
    execution_occurrences: int = 0,
    reused_occurrences: int = 0,
    cross_branch_reused_nodes: int = 0,
    branch_log2_work_bounds: tuple[float, ...] = (),
    combined_child_log2_work_bound: float = 0.0,
    external_log2_cost_bound: float = 0.0,
    total_log2_work_bound: float = 0.0,
    allowed_log2_work: float = 0.0,
    reason: str,
) -> DesignChildProofDAGCoverValidation:
    return DesignChildProofDAGCoverValidation(
        status,
        certified,
        int(branch_count),
        int(validated_branch_count),
        failed_branch_index,
        int(unique_nodes),
        int(execution_occurrences),
        int(reused_occurrences),
        int(cross_branch_reused_nodes),
        tuple(float(value) for value in branch_log2_work_bounds),
        float(combined_child_log2_work_bound),
        float(external_log2_cost_bound),
        float(total_log2_work_bound),
        float(allowed_log2_work),
        reason,
    )


def validate_design_child_proof_dag_cover(
    design_result,
    *,
    original_root_n: int,
    external_log2_cost_bound: float = 0.0,
    polynomial_lift_degree: int | None = None,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 32768.0,
) -> DesignChildProofDAGCoverValidation:
    """Validate a complete Design child cover without replaying any child solver.

    Every branch is validated against its execution-linked proof DAG.  Stable
    identities may deduplicate proof storage across branches only when their full
    proof/accounting payloads and child edges agree.  Cost is never memoized: every
    branch contributes its complete occurrence-expanded recurrence bound to the
    combined cover charge.

    ``external_log2_cost_bound`` is reserved for caller work outside the child
    proofs (for example tuple planning, preflight, and union reconstruction).  It
    must not include the child recurrence work already charged here.
    """
    root = int(original_root_n)
    power = int(quasipoly_power)
    constant = float(quasipoly_constant)
    external = float(external_log2_cost_bound)
    allowed = (
        constant * (log2(max(2, root)) ** power)
        if root > 0 and power >= 1 and constant > 0
        else 0.0
    )

    branches = tuple(getattr(design_result, "branch_results", ()))
    branch_count = len(branches)
    if (
        root <= 0
        or power < 1
        or not isfinite(constant)
        or constant <= 0
        or not isfinite(external)
        or external < 0
    ):
        return _result(
            "invalid_design_child_proof_dag_envelope",
            False,
            branch_count=branch_count,
            external_log2_cost_bound=external,
            allowed_log2_work=allowed,
            reason=(
                "the original root, quasipolynomial envelope, and external "
                "log2 cost must be finite and positive/nonnegative"
            ),
        )

    if not bool(getattr(design_result, "exact", False)) or not bool(
        getattr(design_result, "complete", False)
    ):
        return _result(
            "incomplete_or_nonexact_design_child_cover",
            False,
            branch_count=branch_count,
            external_log2_cost_bound=external,
            allowed_log2_work=allowed,
            reason=(
                "proof-DAG cover certification requires the complete exact "
                "Design child execution, not a partial or unresolved prefix"
            ),
        )

    branches_checked = int(getattr(design_result, "branches_checked", branch_count))
    if branches_checked != branch_count:
        return _result(
            "design_child_branch_count_mismatch",
            False,
            branch_count=branch_count,
            external_log2_cost_bound=external,
            allowed_log2_work=allowed,
            reason=(
                "the recorded Design branch count does not equal the attached "
                "execution-proof count"
            ),
        )

    resource_proof = getattr(design_result, "child_resource_proof", None)
    if branch_count:
        if resource_proof is None or not bool(getattr(resource_proof, "certified", False)):
            return _result(
                "missing_or_uncertified_design_child_resource_proof",
                False,
                branch_count=branch_count,
                external_log2_cost_bound=external,
                allowed_log2_work=allowed,
                reason=(
                    "a nonempty complete child cover must retain its existing "
                    "execution-linked recurrence resource certificate"
                ),
            )
        if (
            int(getattr(resource_proof, "expected_branch_count", -1)) != branch_count
            or int(getattr(resource_proof, "accounted_branch_count", -1))
            != branch_count
        ):
            return _result(
                "design_child_resource_branch_count_mismatch",
                False,
                branch_count=branch_count,
                external_log2_cost_bound=external,
                allowed_log2_work=allowed,
                reason=(
                    "the retained child resource certificate does not account "
                    "for the complete attached branch cover"
                ),
            )

    merged_nodes: dict[object, ProofDAGNode] = {}
    branch_bounds: list[float] = []
    execution_occurrences = 0
    intra_branch_reused_occurrences = 0
    cross_branch_reused_identities: set[object] = set()

    for branch_index, child in enumerate(branches):
        if not bool(getattr(child, "exact", False)) or not bool(
            getattr(child, "local_cost_certified", False)
        ):
            return _result(
                "uncertified_design_child_execution",
                False,
                branch_count=branch_count,
                validated_branch_count=branch_index,
                failed_branch_index=branch_index,
                unique_nodes=len(merged_nodes),
                execution_occurrences=execution_occurrences,
                reused_occurrences=intra_branch_reused_occurrences,
                cross_branch_reused_nodes=len(cross_branch_reused_identities),
                branch_log2_work_bounds=tuple(branch_bounds),
                combined_child_log2_work_bound=_log2_sum_exp(branch_bounds),
                external_log2_cost_bound=external,
                allowed_log2_work=allowed,
                reason=(
                    "every Design child must be the exact cost-certified proof "
                    "object produced by the recorded execution"
                ),
            )

        artifact = build_proof_dag_artifact(child)
        if artifact.status != "constructed_execution_proof_dag":
            return _result(
                artifact.status,
                False,
                branch_count=branch_count,
                validated_branch_count=branch_index,
                failed_branch_index=branch_index,
                unique_nodes=len(merged_nodes),
                execution_occurrences=execution_occurrences,
                reused_occurrences=intra_branch_reused_occurrences,
                cross_branch_reused_nodes=len(cross_branch_reused_identities),
                branch_log2_work_bounds=tuple(branch_bounds),
                combined_child_log2_work_bound=_log2_sum_exp(branch_bounds),
                external_log2_cost_bound=external,
                allowed_log2_work=allowed,
                reason=artifact.reason,
            )

        validation = validate_execution_proof_dag(
            child,
            original_root_n=root,
            polynomial_lift_degree=polynomial_lift_degree,
            quasipoly_power=power,
            quasipoly_constant=constant,
        )
        if not validation.certified:
            return _result(
                validation.status,
                False,
                branch_count=branch_count,
                validated_branch_count=branch_index,
                failed_branch_index=branch_index,
                unique_nodes=len(merged_nodes),
                execution_occurrences=execution_occurrences,
                reused_occurrences=intra_branch_reused_occurrences,
                cross_branch_reused_nodes=len(cross_branch_reused_identities),
                branch_log2_work_bounds=tuple(branch_bounds),
                combined_child_log2_work_bound=_log2_sum_exp(branch_bounds),
                external_log2_cost_bound=external,
                allowed_log2_work=allowed,
                reason=validation.reason,
            )

        branch_identities: set[object] = set()
        for node in artifact.nodes:
            prior = merged_nodes.get(node.identity)
            if prior is not None and prior != node:
                return _result(
                    "cross_branch_proof_identity_payload_collision",
                    False,
                    branch_count=branch_count,
                    validated_branch_count=branch_index,
                    failed_branch_index=branch_index,
                    unique_nodes=len(merged_nodes),
                    execution_occurrences=execution_occurrences,
                    reused_occurrences=intra_branch_reused_occurrences,
                    cross_branch_reused_nodes=len(cross_branch_reused_identities),
                    branch_log2_work_bounds=tuple(branch_bounds),
                    combined_child_log2_work_bound=_log2_sum_exp(branch_bounds),
                    external_log2_cost_bound=external,
                    allowed_log2_work=allowed,
                    reason=(
                        "one replay-stable proof identity names different proof, "
                        "accounting, or child-edge payloads in two Design branches"
                    ),
                )
            if prior is None:
                merged_nodes[node.identity] = node
            elif node.identity not in branch_identities:
                cross_branch_reused_identities.add(node.identity)
            branch_identities.add(node.identity)

        branch_bounds.append(float(validation.log2_work_bound))
        execution_occurrences += int(validation.execution_occurrences)
        intra_branch_reused_occurrences += int(validation.reused_occurrences)

    combined = _log2_sum_exp(branch_bounds)
    if resource_proof is not None:
        recorded_combined = float(
            getattr(resource_proof, "combined_log2_work_bound", combined)
        )
        if not isfinite(recorded_combined) or abs(recorded_combined - combined) > 1e-8:
            return _result(
                "design_child_tree_dag_charge_mismatch",
                False,
                branch_count=branch_count,
                validated_branch_count=branch_count,
                unique_nodes=len(merged_nodes),
                execution_occurrences=execution_occurrences,
                reused_occurrences=intra_branch_reused_occurrences,
                cross_branch_reused_nodes=len(cross_branch_reused_identities),
                branch_log2_work_bounds=tuple(branch_bounds),
                combined_child_log2_work_bound=combined,
                external_log2_cost_bound=external,
                total_log2_work_bound=external + combined,
                allowed_log2_work=allowed,
                reason=(
                    "the complete proof-DAG occurrence charge differs from the "
                    "existing independent Design child recurrence certificate"
                ),
            )

    total = external + combined
    if total > allowed + 1e-9:
        return _result(
            "design_child_proof_dag_envelope_exceeded",
            False,
            branch_count=branch_count,
            validated_branch_count=branch_count,
            unique_nodes=len(merged_nodes),
            execution_occurrences=execution_occurrences,
            reused_occurrences=intra_branch_reused_occurrences,
            cross_branch_reused_nodes=len(cross_branch_reused_identities),
            branch_log2_work_bounds=tuple(branch_bounds),
            combined_child_log2_work_bound=combined,
            external_log2_cost_bound=external,
            total_log2_work_bound=total,
            allowed_log2_work=allowed,
            reason=(
                "all child DAGs are valid, but their complete execution charge "
                "plus caller-external work exceeds the original-root envelope"
            ),
        )

    if not branches:
        status = "certified_empty_design_child_proof_dag_cover"
        reason = (
            "the complete exact Design result executed no child branches; the "
            "vacuous cover and caller-external work fit the root envelope"
        )
    else:
        status = "certified_design_child_proof_dag_cover"
        reason = (
            "every executed Design child has a valid execution-linked proof DAG; "
            "cross-branch identity reuse is payload-consistent, every execution "
            "occurrence is charged, and the complete cover fits the root envelope"
        )
    return _result(
        status,
        True,
        branch_count=branch_count,
        validated_branch_count=branch_count,
        unique_nodes=len(merged_nodes),
        execution_occurrences=execution_occurrences,
        reused_occurrences=intra_branch_reused_occurrences,
        cross_branch_reused_nodes=len(cross_branch_reused_identities),
        branch_log2_work_bounds=tuple(branch_bounds),
        combined_child_log2_work_bound=combined,
        external_log2_cost_bound=external,
        total_log2_work_bound=total,
        allowed_log2_work=allowed,
        reason=reason,
    )


__all__ = [
    "DesignChildProofDAGCoverValidation",
    "validate_design_child_proof_dag_cover",
]
