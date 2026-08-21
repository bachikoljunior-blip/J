from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from math import ceil, factorial, log2

from correlated_twl_resource_envelope_v1 import paired_correlated_twl_resource_envelope
from design_branch_materialization_resource_v1 import design_branch_materialization_resource_envelope
from design_tuple_transport_resource_envelope_v1 import design_tuple_transport_resource_envelope
from local_certificate_preimage_resource_v1 import _chain_bound, _sat_add, _sat_mul


@dataclass(frozen=True)
class DesignPipelineAdmissionLedger:
    status: str
    original_root_degree: int
    original_degree: int
    vertex_count: int
    arity: int
    ambient_group_order: int
    ambient_generator_count: int
    witness_count_per_side_upper_bound: int
    branch_count_upper_bound: int
    twl_work_upper_bound: int
    materialization_work_upper_bound: int
    tuple_transport_work_upper_bound: int
    child_si_work_per_branch_upper_bound: int
    child_si_work_upper_bound: int
    union_generator_inputs_upper_bound: int
    union_work_upper_bound: int
    work_upper_bound: int
    max_work: int
    root_lift_certified: bool
    admitted: bool
    charged_twl_work: int
    charged_materialization_work: int
    charged_tuple_transport_work: int
    charged_child_si_work: int
    charged_union_work: int
    charged_work: int
    complete: bool
    reason: str


def _falling(n: int, ell: int) -> int:
    out = 1
    for i in range(ell):
        out *= n - i
    return out


def _multiset_permutation_count(values) -> int:
    values = tuple(values)
    try:
        counts = Counter(values)
    except TypeError as exc:
        raise ValueError("string values must be hashable") from exc
    out = factorial(len(values))
    for count in counts.values():
        out //= factorial(count)
    return out


def design_pipeline_admission_ledger(
    *,
    original_root_degree: int,
    original_degree: int,
    vertex_count: int,
    arity: int,
    ambient_group_order: int,
    ambient_generator_count: int,
    target_values,
    group_order_poly_power: int = 2,
    max_group_order: int = 256,
    max_work: int = 10**30,
) -> DesignPipelineAdmissionLedger:
    """Reserve the whole exact Design pipeline before the first t-WL run.

    The reservation deliberately ignores early successful individualization and
    later branch pruning.  It charges every ordered individualization through
    length ``arity-1``, the largest possible first-success witness Cartesian
    cover, tuple transport for every such pair, a guaranteed exact full-string
    terminal for every surviving branch, and the final exact union
    reconstruction.  All arithmetic is arbitrary precision and the composed
    total saturates only at caller ``cap+1``.
    """
    root, n, v, k, order, gens, power, impl_cap, cap = map(int, (
        original_root_degree, original_degree, vertex_count, arity,
        ambient_group_order, ambient_generator_count, group_order_poly_power,
        max_group_order, max_work,
    ))
    if min(root, n, v, k, order, power, impl_cap, cap) <= 0 or gens < 0:
        raise ValueError("invalid Design pipeline admission parameters")
    target = tuple(target_values)
    if len(target) != n:
        raise ValueError("target string/Design pipeline degree mismatch")
    if k > v:
        raise ValueError("Design arity exceeds the auxiliary ground")

    stop = cap + 1
    arity_cap = max(1, ceil(log2(max(2, root))))
    root_lift = n <= root and v <= root and k <= arity_cap

    twl = paired_correlated_twl_resource_envelope(root, v, k, max(cap, 1))
    twl_work = int(twl.paired_work_upper_bound)

    ell_max = max(0, k - 1)
    witnesses = _falling(v, ell_max)
    branches = witnesses * witnesses
    materialization = design_branch_materialization_resource_envelope(
        root, v, ell_max, witnesses, witnesses, max(cap, 1)
    )
    materialization_work = int(materialization.work_upper_bound)

    transport = design_tuple_transport_resource_envelope(
        root, n, v, ell_max, branches, order, max(1, gens), max(cap, 1)
    )
    transport_work = int(transport.work_upper_bound)

    multiset_states = _multiset_permutation_count(target)
    state_bound = min(order, multiset_states)
    g = max(1, gens)
    state_action = _sat_mul(state_bound, _sat_mul(g, max(1, n), stop), stop)
    state_chain = _chain_bound(n, state_bound * g, order, n, stop)
    state_terminal_work = _sat_add(state_action, state_chain, stop)

    small_order_gate = min(impl_cap, root ** power, order)
    small_order_scale = max(2, n) ** 12 * (2 ** 24)
    small_order_terminal_work = _sat_mul(small_order_gate, small_order_scale, stop)
    child_per_branch = max(state_terminal_work, small_order_terminal_work)
    child_work = _sat_mul(branches, child_per_branch, stop)

    # A child stabilizer can always be represented by at most |G| elements;
    # the state-orbit path can emit at most one Schreier generator per
    # state-generator edge.  Reserve the larger bound plus one inter-branch
    # representative delta for every possible nonempty branch.
    child_generators = max(order, state_bound * g)
    union_inputs = _sat_mul(branches, child_generators + 1, stop)
    verification_per_input = _sat_mul(16 * n * n, order, stop)
    union_verification = _sat_mul(union_inputs, verification_per_input, stop)
    union_chain = _chain_bound(n, max(1, union_inputs), order, n, stop)
    union_work = _sat_add(union_verification, union_chain, stop)

    total = 0
    for work in (twl_work, materialization_work, transport_work, child_work, union_work):
        total = _sat_add(total, int(work), stop)

    admitted = root_lift and total <= cap
    if not root_lift:
        status = "design_pipeline_original_root_lift_unavailable"
        reason = "the Design ground, full-string degree, or correlated-tWL arity exceeds the original-root lift gate"
    elif total > cap:
        status = "design_pipeline_work_cap_exceeded"
        reason = "the complete correlated-tWL through union-reconstruction reservation exceeds the finite budget before the first t-WL run"
    else:
        status = "certified_design_pipeline_admission_ledger"
        reason = "correlated t-WL, maximal witness materialization, tuple transport, every full-string child terminal, and final union reconstruction are reserved in one original-root ledger before execution"

    return DesignPipelineAdmissionLedger(
        status, root, n, v, k, order, g, witnesses, branches,
        twl_work, materialization_work, transport_work, child_per_branch,
        child_work, union_inputs, union_work, total, cap, root_lift, admitted,
        0, 0, 0, 0, 0, 0, False, reason,
    )


def record_design_pipeline_execution(
    ledger: DesignPipelineAdmissionLedger,
    *,
    twl_work: int,
    materialization_work: int,
    tuple_transport_work: int,
    child_si_work: int,
    union_work: int,
    complete: bool,
) -> DesignPipelineAdmissionLedger:
    if not ledger.admitted:
        raise ValueError("cannot record a rejected Design pipeline ledger")
    charges = tuple(map(int, (
        twl_work, materialization_work, tuple_transport_work, child_si_work, union_work,
    )))
    if min(charges) < 0:
        raise ValueError("Design pipeline charges must be nonnegative")
    limits = (
        ledger.twl_work_upper_bound,
        ledger.materialization_work_upper_bound,
        ledger.tuple_transport_work_upper_bound,
        ledger.child_si_work_upper_bound,
        ledger.union_work_upper_bound,
    )
    if any(charge > limit for charge, limit in zip(charges, limits)):
        raise ValueError("executed Design pipeline phase exceeds its reservation")
    total = sum(charges)
    if total > ledger.work_upper_bound:
        raise ValueError("executed Design pipeline exceeds the shared reservation")
    return replace(
        ledger,
        charged_twl_work=charges[0],
        charged_materialization_work=charges[1],
        charged_tuple_transport_work=charges[2],
        charged_child_si_work=charges[3],
        charged_union_work=charges[4],
        charged_work=total,
        complete=bool(complete),
    )


__all__ = [
    "DesignPipelineAdmissionLedger",
    "design_pipeline_admission_ledger",
    "record_design_pipeline_execution",
]
