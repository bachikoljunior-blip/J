from __future__ import annotations

from dataclasses import dataclass

from design_nested_primitive_johnson_resource_v1 import (
    NestedPrimitiveJohnsonResourceEnvelope,
    design_nested_primitive_johnson_resource_envelope,
)
from proof_carrying_si_v1 import ProofCarryingCoset
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode
from s1_structural_classifier_v1 import classify_s1_structure
from signed_johnson_ground_profile_partition_si_v1 import (
    signed_johnson_ground_profile_partition_si,
)


# The production profile implementation currently calls the relational lift with
# this exact robust-orbital cap.  The resource reservation must use the same gate.
ROBUST_ORBITAL_DEGREE = 128


@dataclass(frozen=True)
class ResourceBoundedPrimitiveJohnsonProof(ProofCarryingCoset):
    resource_envelope: NestedPrimitiveJohnsonResourceEnvelope | None = None
    structural_path_certified: bool = False
    johnson_path_certified: bool = False
    execution_charge_complete: bool = False
    charged_work_upper_bound: int = 0
    johnson_parameter_executed: tuple[int, int] | None = None
    partition_states_executed: int = 0
    partition_actions_executed: int = 0
    classification_status: str = ""

    @property
    def production_attempt_admitted(self) -> bool:
        return bool(
            self.resource_envelope is not None
            and self.resource_envelope.resource_admitted
            and self.structural_path_certified
            and self.johnson_path_certified
            and self.execution_charge_complete
        )


def _unresolved(
    status: str,
    *,
    root_n: int,
    degree: int,
    reason: str,
    classification_status: str = "",
    envelope: NestedPrimitiveJohnsonResourceEnvelope | None = None,
    structural_path_certified: bool = False,
) -> ResourceBoundedPrimitiveJohnsonProof:
    accounting = RecurrenceAccountingNode(
        n=root_n,
        m=max(1, degree),
        operation_kind="resource_bounded_primitive_johnson_unresolved",
        canonical=True,
        cost_certified=False,
        local_log2_cost_bound=0.0,
        children=(),
        terminal_certified=False,
        reason=reason,
    )
    return ResourceBoundedPrimitiveJohnsonProof(
        status=status,
        coset=None,
        operation_kind="resource_bounded_primitive_johnson_unresolved",
        root_n=root_n,
        domain_size=degree,
        canonical=True,
        exact=False,
        local_cost_certified=False,
        local_log2_cost_bound=0.0,
        terminal_certified=False,
        children=(),
        accounting=accounting,
        permutation_candidates_checked=0,
        reason=reason,
        resource_envelope=envelope,
        structural_path_certified=structural_path_certified,
        classification_status=classification_status,
    )


def _attach_execution(
    inner,
    envelope: NestedPrimitiveJohnsonResourceEnvelope,
    *,
    classification_status: str,
) -> ResourceBoundedPrimitiveJohnsonProof:
    states = int(getattr(inner, "partition_orbit_states", 0))
    actions = int(inner.permutation_candidates_checked)
    if states > int(envelope.partition_state_upper_bound):
        raise AssertionError("executed Johnson partition states exceeded the pre-admitted reservation")
    if actions > int(envelope.partition_action_upper_bound):
        raise AssertionError("executed Johnson partition actions exceeded the pre-admitted reservation")

    v = int(getattr(inner, "ground_size", 0))
    k = int(getattr(inner, "subset_size", 0))
    parameter = (v, k) if v > 0 and k > 0 else None
    # Every status after this one is reached only after the exact relational lift
    # has certified Johnson coordinates and re-induced every ambient generator.
    johnson_path = bool(
        inner.status != "undetermined_signed_ground_profile_lift"
        and parameter is not None
        and parameter in envelope.johnson_parameter_candidates
    )
    if johnson_path:
        if v > envelope.max_ground_size or k > envelope.max_subset_size:
            raise AssertionError("executed Johnson parameter exceeded the complete preflight family")

    return ResourceBoundedPrimitiveJohnsonProof(
        status=inner.status,
        coset=inner.coset,
        operation_kind=inner.operation_kind,
        root_n=inner.root_n,
        domain_size=inner.domain_size,
        canonical=inner.canonical,
        exact=inner.exact,
        local_cost_certified=inner.local_cost_certified,
        local_log2_cost_bound=inner.local_log2_cost_bound,
        terminal_certified=inner.terminal_certified,
        children=tuple(inner.children),
        accounting=inner.accounting,
        permutation_candidates_checked=inner.permutation_candidates_checked,
        reason=inner.reason,
        proof_identity=inner.proof_identity,
        resource_envelope=envelope,
        structural_path_certified=True,
        johnson_path_certified=johnson_path,
        execution_charge_complete=True,
        charged_work_upper_bound=int(envelope.work_upper_bound),
        johnson_parameter_executed=parameter if johnson_path else None,
        partition_states_executed=states,
        partition_actions_executed=actions,
        classification_status=classification_status,
    )


def resource_bounded_primitive_johnson_string_isomorphism(
    group,
    source_values,
    target_values,
    *,
    root_n: int | None = None,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    parent_order_upper_bound: int | None = None,
    image_order_upper_bound: int | None = None,
    generator_upper_bound: int | None = None,
    max_recognition_nodes: int = 500000,
    max_partition_states: int = 4096,
    max_primitive_johnson_work: int,
) -> ResourceBoundedPrimitiveJohnsonProof:
    """Execute one primitive-non-giant Johnson/profile attempt under rev243's cap.

    This is the executable half of the rev243 resource contract.  The exact S1
    structural classifier first certifies that the now-known child is primitive
    non-giant.  Before Johnson recognition begins, the complete rev243 envelope
    is instantiated from caller-supplied pre-child order/generator upper bounds.
    Only an admitted envelope may invoke the existing signed Johnson profile
    solver.  The returned proof is then linked to that exact reservation and its
    observable partition execution is checked against the reserved state/action
    counts.

    The wrapper deliberately does not modify the shared Design caller or choose a
    future child before its subgroup exists.  A later complete-cover integration
    may pass the same pre-reserved bounds into this operator.  Recognition or
    profile failure remains a typed fail-closed result; resource admission never
    upgrades an unresolved semantic proof to exact SI.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(group.degree)
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n is None:
        root_n = n
    root_n = int(root_n)
    if root_n < n:
        raise ValueError("root_n must dominate current degree")
    if max_primitive_johnson_work <= 0:
        raise ValueError("max_primitive_johnson_work must be positive")
    if max_recognition_nodes <= 0 or max_partition_states <= 0:
        raise ValueError("Johnson recognition and partition caps must be positive")

    classification = classify_s1_structure(
        group,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
    )
    if classification.status != "primitive_non_giant" or not classification.canonical:
        return _unresolved(
            "not_primitive_non_giant_resource_bounded_johnson_case",
            root_n=root_n,
            degree=n,
            classification_status=classification.status,
            reason=(
                "the exact S1 structural classifier did not select the primitive "
                "non-giant branch; this operator must not steal another terminal"
            ),
        )

    actual_order = int(group.order)
    actual_generators = max(1, len(tuple(group.original_generators)))
    parent_bound = actual_order if parent_order_upper_bound is None else int(parent_order_upper_bound)
    image_bound = actual_order if image_order_upper_bound is None else int(image_order_upper_bound)
    generator_bound = actual_generators if generator_upper_bound is None else int(generator_upper_bound)
    if parent_bound < actual_order or image_bound < actual_order or generator_bound < actual_generators:
        return _unresolved(
            "primitive_johnson_prechild_bound_below_actual_execution",
            root_n=root_n,
            degree=n,
            classification_status=classification.status,
            structural_path_certified=True,
            reason=(
                "a caller-supplied pre-child order/generator upper bound is below "
                "the now-known subgroup execution; fail closed rather than charge "
                "work outside the reservation"
            ),
        )

    envelope = design_nested_primitive_johnson_resource_envelope(
        original_root_degree=root_n,
        original_degree=n,
        image_degree=n,
        parent_order_upper_bound=parent_bound,
        image_order_upper_bound=image_bound,
        generator_upper_bound=generator_bound,
        max_recognition_nodes=max_recognition_nodes,
        max_robust_orbital_degree=ROBUST_ORBITAL_DEGREE,
        partition_state_poly_power=2,
        max_partition_states=max_partition_states,
        max_work=max_primitive_johnson_work,
    )
    if not envelope.resource_admitted:
        return _unresolved(
            envelope.status,
            root_n=root_n,
            degree=n,
            classification_status=classification.status,
            envelope=envelope,
            structural_path_certified=True,
            reason=envelope.reason,
        )

    inner = signed_johnson_ground_profile_partition_si(
        group,
        source,
        target,
        root_n=root_n,
        partition_state_poly_power=2,
        max_partition_states=max_partition_states,
        max_recognition_nodes=max_recognition_nodes,
    )
    return _attach_execution(
        inner,
        envelope,
        classification_status=classification.status,
    )


__all__ = [
    "ResourceBoundedPrimitiveJohnsonProof",
    "resource_bounded_primitive_johnson_string_isomorphism",
]
