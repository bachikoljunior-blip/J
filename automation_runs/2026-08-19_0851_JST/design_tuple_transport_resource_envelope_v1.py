from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil, log2


@dataclass(frozen=True)
class DesignTupleTransportResourceEnvelope:
    status: str
    original_root_degree: int
    original_degree: int
    ground_size: int
    individualization_length: int
    branch_count: int
    group_order: int
    generator_count: int
    orbit_states_per_branch_upper_bound: int
    generator_edges_per_branch_upper_bound: int
    work_per_branch_upper_bound: int
    work_upper_bound: int
    max_work: int
    root_lift_certified: bool
    admitted: bool
    executed_branches: int
    executed_orbit_states: int
    executed_action_steps: int
    charged_work_upper_bound: int
    complete: bool
    reason: str


def design_tuple_transport_resource_envelope(
    original_root_degree: int,
    original_degree: int,
    ground_size: int,
    individualization_length: int,
    branch_count: int,
    group_order: int,
    generator_count: int,
    max_work: int,
) -> DesignTupleTransportResourceEnvelope:
    """Reserve a complete Design witness Cartesian cover and tuple transport.

    An orbit contains at most ``|G|`` states.  For each branch we reserve every
    state/generator edge twice (orbit discovery and stabilizer generators),
    tuple/partition permutation work on both domains, and three conservative
    full-group Schreier passes (stabilizer, parity kernel, final coset chain).
    Runtime branch/state caps are intentionally absent from this theorem-side
    arbitrary-precision bound.
    """
    root, n, v, ell, branches, order, gens, cap = map(int, (
        original_root_degree, original_degree, ground_size,
        individualization_length, branch_count, group_order,
        generator_count, max_work,
    ))
    if min(root, n, v, order, cap) <= 0 or min(ell, branches, gens) < 0:
        raise ValueError("invalid Design tuple-transport resource parameters")
    arity_cap = max(1, ceil(log2(max(2, root))))
    root_lift = n <= root and v <= root and ell <= arity_cap
    orbit_states = order
    edges = orbit_states * max(1, gens)
    partition_work = 2 * v + 1
    orbit_and_stabilizer_work = 2 * edges * (n + v + 1)
    schreier_work = 3 * max(1, edges) * (order + 1) * (n + 1)
    per_branch = partition_work + orbit_and_stabilizer_work + schreier_work
    total = branches + branches * per_branch
    admitted = root_lift and total <= cap
    if not root_lift:
        status = "design_tuple_transport_original_root_lift_unavailable"
        reason = "Design tuple transport exceeds the original-root degree or logarithmic individualization gate"
    elif total > cap:
        status = "design_tuple_transport_work_cap_exceeded"
        reason = "the complete Cartesian branch and tuple-transport bound exceeds the finite budget before the first transport"
    else:
        status = "certified_design_tuple_transport_work_bound"
        reason = "the complete Cartesian cover and all tuple-transporter Schreier primitives fit the finite original-root budget"
    return DesignTupleTransportResourceEnvelope(
        status, root, n, v, ell, branches, order, gens, orbit_states, edges,
        per_branch, total, cap, root_lift, admitted, 0, 0, 0, 0, False, reason,
    )


def record_design_tuple_transport_execution(
    envelope: DesignTupleTransportResourceEnvelope,
    *,
    executed_branches: int,
    executed_orbit_states: int,
    executed_action_steps: int,
    complete: bool,
) -> DesignTupleTransportResourceEnvelope:
    if not envelope.admitted:
        raise ValueError("cannot record execution for a rejected Design transport envelope")
    branches, states, steps = map(int, (
        executed_branches, executed_orbit_states, executed_action_steps,
    ))
    if min(branches, states, steps) < 0:
        raise ValueError("executed Design transport counts must be nonnegative")
    if branches > envelope.branch_count:
        raise ValueError("executed branch count exceeds the complete cover")
    if states > branches * envelope.orbit_states_per_branch_upper_bound:
        raise ValueError("executed orbit states exceed the proven bound")
    if steps > branches * envelope.generator_edges_per_branch_upper_bound:
        raise ValueError("executed generator edges exceed the proven bound")
    charged = branches + branches * envelope.work_per_branch_upper_bound
    if charged > envelope.work_upper_bound:
        raise ValueError("Design tuple-transport charge exceeds the proven bound")
    return replace(
        envelope,
        executed_branches=branches,
        executed_orbit_states=states,
        executed_action_steps=steps,
        charged_work_upper_bound=charged,
        complete=bool(complete),
    )


__all__ = [
    "DesignTupleTransportResourceEnvelope",
    "design_tuple_transport_resource_envelope",
    "record_design_tuple_transport_execution",
]
