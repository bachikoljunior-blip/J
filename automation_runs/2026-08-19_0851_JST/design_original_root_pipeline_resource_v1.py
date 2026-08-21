from __future__ import annotations

from dataclasses import dataclass, replace

from correlated_twl_resource_envelope_v1 import paired_correlated_twl_resource_envelope
from design_branch_materialization_resource_v1 import design_branch_materialization_resource_envelope
from design_nested_primitive_johnson_resource_v1 import design_nested_primitive_johnson_resource_envelope
from design_tuple_transport_resource_envelope_v1 import design_tuple_transport_resource_envelope
from local_certificate_preimage_resource_v1 import _chain_bound, _sat_add, _sat_mul


PHASES = ("twl", "materialization", "transport", "children", "union")


@dataclass(frozen=True)
class DesignOriginalRootPipelineResourceEnvelope:
    status: str
    original_root_degree: int
    original_degree: int
    vertex_count: int
    arity: int
    branch_count_upper_bound: int
    phase_work_upper_bounds: tuple[int, ...]
    work_upper_bound: int
    max_work: int
    root_lift_certified: bool
    admitted: bool
    completed_phases: tuple[str, ...]
    phase_charges: tuple[int, ...]
    charged_work: int
    unexecuted_suffix: tuple[str, ...]
    complete: bool
    reason: str


def design_original_root_pipeline_resource_envelope(
    group,
    *,
    original_root_degree: int,
    vertex_count: int,
    arity: int,
    target_values,
    group_order_poly_power: int,
    max_group_order: int,
    max_work: int,
) -> DesignOriginalRootPipelineResourceEnvelope:
    """Reserve the complete Design pipeline before its first correlated t-WL run.

    The child phase reserves a uniform upper bound for every exact production
    terminal that may be selected only after tuple transport fixes the branch
    subgroup: small-order scan, complete state orbit, transitive-imprimitive
    quotient/kernel recursion, and the rev243 primitive-Johnson recognition /
    profile / partition / original-root-lift path.  Later branch-specific
    preflights must fit inside this immutable pre-tWL envelope.
    """
    root = int(original_root_degree)
    n = int(group.degree)
    v = int(vertex_count)
    k = int(arity)
    order = int(group.order)
    power = int(group_order_poly_power)
    implementation_cap = int(max_group_order)
    cap = int(max_work)
    target = tuple(target_values)
    if min(root, n, v, k, order, power, implementation_cap, cap) <= 0:
        raise ValueError("invalid Design original-root pipeline parameters")
    if len(target) != n:
        raise ValueError("target string/Design pipeline degree mismatch")

    stop = cap + 1
    twl = paired_correlated_twl_resource_envelope(root, v, k, cap)
    runs = int(twl.individualization_runs_per_side_upper_bound)
    material = design_branch_materialization_resource_envelope(
        root, v, k, runs, runs, cap,
    )
    branches = int(material.branch_count)
    generators = max(1, len(tuple(group.original_generators)))
    transport = design_tuple_transport_resource_envelope(
        root, n, v, k, branches, order, generators, cap,
    )

    gate = min(implementation_cap, root ** power)
    small_candidates = min(order, gate)
    small = _sat_mul(small_candidates, max(2, n) ** 12 * (2 ** 24), stop)
    counts = {}
    for value in target:
        counts[value] = counts.get(value, 0) + 1
    multiset_states = 1
    remaining = n
    from math import comb
    for count in counts.values():
        multiset_states = _sat_mul(multiset_states, comb(remaining, count), stop)
        remaining -= count
    states = min(order, multiset_states)
    action = _sat_mul(_sat_mul(states, order, stop), n, stop)
    state_chain = _chain_bound(n, max(1, states * order), order, n, stop)
    state_orbit = _sat_add(action, state_chain, stop)

    imprimitive_universal = _sat_mul(
        (2 ** 26) * (max(2, n) ** 12), order ** 3, stop,
    )

    # This call is used only as a monotone work envelope.  Its semantic
    # resource_admitted flag may be false because the ambient |G| is deliberately
    # looser than the later exact branch subgroup.  work_upper_bound nevertheless
    # dominates the same rev243 computation for every H <= G, with the identical
    # production recognition/partition caps used by rev254/rev246.
    primitive_universal_envelope = design_nested_primitive_johnson_resource_envelope(
        original_root_degree=root,
        original_degree=n,
        image_degree=n,
        parent_order_upper_bound=order,
        image_order_upper_bound=order,
        generator_upper_bound=max(1, generators),
        max_recognition_nodes=500000,
        max_robust_orbital_degree=128,
        partition_state_poly_power=2,
        max_partition_states=4096,
        max_work=cap,
    )
    primitive_johnson_universal = int(primitive_universal_envelope.work_upper_bound)

    child_per_branch = max(
        small,
        state_orbit,
        imprimitive_universal,
        primitive_johnson_universal,
    )
    children = _sat_mul(branches, child_per_branch, stop)

    union_inputs = _sat_mul(branches, order + 1, stop)
    verify_per_input = _sat_mul(16 * n * n, order, stop)
    union_verify = _sat_mul(union_inputs, verify_per_input, stop)
    union_chain = _chain_bound(n, max(1, union_inputs), order, n, stop)
    union = _sat_add(union_verify, union_chain, stop)

    phase_bounds = (
        int(twl.paired_work_upper_bound),
        int(material.work_upper_bound),
        int(transport.work_upper_bound),
        int(children),
        int(union),
    )
    total = 0
    for bound in phase_bounds:
        total = _sat_add(total, bound, stop)
    root_lift = bool(
        twl.root_lift_certified
        and material.root_lift_certified
        and transport.root_lift_certified
        and n <= root
    )
    admitted = root_lift and total <= cap
    if not root_lift:
        status = "design_original_root_pipeline_lift_unavailable"
        reason = "a Design phase exceeds the original-root degree or logarithmic arity lift gate"
    elif total > cap:
        status = "design_original_root_pipeline_work_cap_exceeded"
        reason = "the sum of all Design phase reservations exceeds the finite budget before the first correlated t-WL run"
    else:
        status = "certified_design_original_root_pipeline_work_bound"
        reason = "correlated t-WL, complete branch materialization and transport, all reserved exact child terminals including primitive-Johnson, and union reconstruction fit one original-root budget"
    return DesignOriginalRootPipelineResourceEnvelope(
        status, root, n, v, k, branches, phase_bounds, total, cap,
        root_lift, admitted, (), (), 0, PHASES, False, reason,
    )


def record_design_original_root_pipeline_phase(
    envelope: DesignOriginalRootPipelineResourceEnvelope,
    phase: str,
    *,
    charged_work: int,
) -> DesignOriginalRootPipelineResourceEnvelope:
    """Append exactly one phase charge and retain the unexecuted suffix."""
    if not envelope.admitted:
        raise ValueError("cannot charge a rejected Design pipeline")
    index = len(envelope.completed_phases)
    if index >= len(PHASES) or phase != PHASES[index]:
        raise ValueError("Design pipeline phases must be charged once in canonical order")
    charge = int(charged_work)
    if charge < 0 or charge > envelope.phase_work_upper_bounds[index]:
        raise ValueError("Design phase charge exceeds its reserved upper bound")
    charges = envelope.phase_charges + (charge,)
    total = sum(charges)
    if total > envelope.work_upper_bound or total > envelope.max_work:
        raise ValueError("Design pipeline cumulative charge exceeds the reservation")
    completed = envelope.completed_phases + (phase,)
    suffix = PHASES[len(completed):]
    complete = not suffix
    return replace(
        envelope,
        completed_phases=completed,
        phase_charges=charges,
        charged_work=total,
        unexecuted_suffix=suffix,
        complete=complete,
    )


__all__ = [
    "DesignOriginalRootPipelineResourceEnvelope",
    "design_original_root_pipeline_resource_envelope",
    "record_design_original_root_pipeline_phase",
]
