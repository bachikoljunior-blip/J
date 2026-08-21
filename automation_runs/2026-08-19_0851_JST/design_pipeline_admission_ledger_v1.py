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
    branch_subgroup_generator_count_upper_bound: int = 0
    child_state_image_upper_bound: int = 0
    child_generator_count_upper_bound: int = 0
    executed_source_runs: int = 0
    executed_target_runs: int = 0
    executed_source_work: int = 0
    executed_target_work: int = 0
    materialized_branch_count: int = 0
    transported_branch_count: int = 0
    transported_orbit_states: int = 0
    transported_action_steps: int = 0
    executed_child_count: int = 0
    permutation_candidates_checked: int = 0
    union_generator_count: int = 0
    phases_recorded: tuple[str, ...] = ()


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

    The exact first-successful witness level and later child subgroups are not
    known at this boundary.  The ledger reserves every ordered t-WL
    individualization, the largest first-success witness Cartesian cover,
    ambient tuple transport, every exact production child path, and final union
    reconstruction from input-only ambient bounds.

    Tuple transport can emit one subgroup generator per ambient
    state/generator edge.  A state-orbit child can in turn emit one generator
    per state/candidate-generator edge.  The already-certified intransitive
    small-image path is separately bounded, so the production child's choice
    between small-order, intransitive, and state-orbit terminals cannot escape
    the shared envelope.

    All cross-phase arithmetic saturates only at caller ``cap+1``.  Existing
    per-phase/runtime caps remain stricter fail-closed guards.
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
    g = max(1, gens)

    twl = paired_correlated_twl_resource_envelope(root, v, k, cap)
    twl_work = min(stop, int(twl.paired_work_upper_bound))

    ell_max = max(0, k - 1)
    witnesses = _falling(v, ell_max)
    branches = witnesses * witnesses
    materialization = design_branch_materialization_resource_envelope(
        root, v, ell_max, witnesses, witnesses, cap,
    )
    materialization_work = min(stop, int(materialization.work_upper_bound))

    transport = design_tuple_transport_resource_envelope(
        root, n, v, ell_max, branches, order, g, cap,
    )
    transport_work = min(stop, int(transport.work_upper_bound))

    # The tuple-transporter Schreier orbit has at most |G| states and one
    # action edge per ambient generator.  Every actual branch subgroup
    # generator family is bounded by this complete edge family.
    branch_candidate_gens = max(1, _sat_mul(order, g, stop))

    multiset_states = _multiset_permutation_count(target)
    state_bound = min(order, multiset_states)
    state_edges = _sat_mul(state_bound, branch_candidate_gens, stop)
    state_action = _sat_mul(state_edges, max(1, n), stop)
    state_chain = _chain_bound(n, state_edges, order, n, stop)
    state_terminal_work = _sat_add(state_action, state_chain, stop)

    small_order_gate = min(impl_cap, root ** power, order)
    small_order_scale = _sat_mul(max(2, n) ** 12, 2 ** 24, stop)
    small_order_terminal_work = _sat_mul(
        small_order_gate, small_order_scale, stop,
    )

    # Bound the rev237 intransitive-small-image production path without
    # predicting the actual orbit partition.  There are at most n orbits; each
    # certified image has order at most the same small-order gate.
    audit_orbit = _sat_mul(8 * n * n, max(branch_candidate_gens, order), stop)
    audit_chains = _sat_mul(
        n, _chain_bound(n, branch_candidate_gens, order, n, stop), stop,
    )
    legacy_work = _sat_mul(
        2, _sat_add(audit_orbit, audit_chains, stop), stop,
    )
    image_child = _sat_mul(small_order_gate, small_order_scale, stop)
    paired = _chain_bound(n, branch_candidate_gens, order, 2 * n, stop)
    kernel = _chain_bound(n, order, order, n, stop)
    lifts = _sat_mul(
        small_order_gate,
        _sat_mul(n, _sat_mul(order, 8 * n, stop), stop),
        stop,
    )
    preimage = _chain_bound(
        n, order + small_order_gate, order, n, stop,
    )
    one_orbit = 0
    for part in (image_child, paired, kernel, lifts, preimage):
        one_orbit = _sat_add(one_orbit, part, stop)
    legacy_work = _sat_add(
        legacy_work, _sat_mul(n, one_orbit, stop), stop,
    )

    child_per_branch = max(
        state_terminal_work, small_order_terminal_work, legacy_work,
    )
    child_work = _sat_mul(branches, child_per_branch, stop)

    # Small-order output is bounded by |G|.  State-orbit output is bounded by
    # one stabilizer generator per state/candidate-generator edge.  The legacy
    # preimage chains deduplicate inside the ambient group.
    child_generators = max(1, order, state_edges)
    union_inputs = _sat_mul(
        branches, _sat_add(child_generators, 1, stop), stop,
    )
    verification_per_input = _sat_mul(16 * n * n, order, stop)
    union_verification = _sat_mul(
        union_inputs, verification_per_input, stop,
    )
    union_chain = _chain_bound(
        n, max(1, union_inputs), order, n, stop,
    )
    union_work = _sat_add(union_verification, union_chain, stop)

    total = 0
    for work in (
        twl_work, materialization_work, transport_work, child_work, union_work,
    ):
        total = _sat_add(total, int(work), stop)

    admitted = root_lift and total <= cap
    if not root_lift:
        status = "design_pipeline_original_root_lift_unavailable"
        reason = (
            "the Design ground, full-string degree, or correlated-tWL arity "
            "exceeds the original-root lift gate"
        )
    elif total > cap:
        status = "design_pipeline_work_cap_exceeded"
        reason = (
            "the complete correlated-tWL through union-reconstruction "
            "reservation exceeds the finite budget before the first t-WL run"
        )
    else:
        status = "certified_design_pipeline_admission_ledger"
        reason = (
            "correlated t-WL, maximal witness materialization, tuple transport, "
            "every production full-string child path, and final union "
            "reconstruction are reserved in one original-root ledger"
        )

    return DesignPipelineAdmissionLedger(
        status, root, n, v, k, order, g, witnesses, branches,
        twl_work, materialization_work, transport_work, child_per_branch,
        child_work, union_inputs, union_work, total, cap, root_lift, admitted,
        0, 0, 0, 0, 0, 0, False, reason,
        branch_candidate_gens, state_bound, child_generators,
    )


def record_design_pipeline_execution(
    ledger: DesignPipelineAdmissionLedger,
    *,
    twl_work: int | None = None,
    materialization_work: int | None = None,
    tuple_transport_work: int | None = None,
    child_si_work: int | None = None,
    union_work: int | None = None,
    twl_resource=None,
    materialization_resource=None,
    transport_resource=None,
    child_preflight=None,
    union_resource=None,
    complete: bool,
) -> DesignPipelineAdmissionLedger:
    """Record each executed phase once and verify it against the shared ledger.

    Numeric phase charges retain the original rev242 API.  Production callers
    pass the execution-linked rev232/rev234/rev233/rev235--240/rev241 objects;
    their actual counts are copied into the immutable outer record.
    """
    if not ledger.admitted:
        raise ValueError("cannot record a rejected Design pipeline ledger")

    phases = []
    sr = tr = sw = tw = 0
    materialized = transported = orbit_states = action_steps = 0
    child_count = scans = union_generators = 0

    if twl_resource is not None:
        sr = int(twl_resource.executed_source_runs)
        tr = int(twl_resource.executed_target_runs)
        sw = int(twl_resource.executed_source_work)
        tw = int(twl_resource.executed_target_work)
        derived_twl = int(twl_resource.charged_paired_work)
        twl_work = derived_twl if twl_work is None else int(twl_work)
        if twl_work != derived_twl:
            raise ValueError("t-WL charge does not match the execution proof")
        phases.append("twl")
    if materialization_resource is not None:
        materialized = int(materialization_resource.materialized_branch_count)
        derived_materialization = int(
            materialization_resource.charged_work_upper_bound
        )
        materialization_work = (
            derived_materialization
            if materialization_work is None else int(materialization_work)
        )
        if materialization_work != derived_materialization:
            raise ValueError(
                "materialization charge does not match the execution proof"
            )
        phases.append("materialization")
    if transport_resource is not None:
        transported = int(transport_resource.executed_branches)
        orbit_states = int(transport_resource.executed_orbit_states)
        action_steps = int(transport_resource.executed_action_steps)
        derived_transport = int(transport_resource.charged_work_upper_bound)
        tuple_transport_work = (
            derived_transport
            if tuple_transport_work is None else int(tuple_transport_work)
        )
        if tuple_transport_work != derived_transport:
            raise ValueError(
                "tuple-transport charge does not match the execution proof"
            )
        phases.append("transport")
    if child_preflight is not None:
        child_count = int(child_preflight.executed_branch_count)
        scans = int(child_preflight.permutation_candidates_checked)
        derived_child = 0
        stop = ledger.max_work + 1
        for work in child_preflight.work_per_branch_upper_bounds[:child_count]:
            derived_child = _sat_add(derived_child, int(work), stop)
        child_si_work = (
            derived_child if child_si_work is None else int(child_si_work)
        )
        if child_si_work != derived_child:
            raise ValueError("child-SI charge does not match the execution proof")
        phases.append("child")
    if union_resource is not None:
        union_generators = int(union_resource.executed_generator_count)
        derived_union = (
            int(union_resource.work_upper_bound)
            if bool(union_resource.complete) else 0
        )
        union_work = (
            derived_union if union_work is None else int(union_work)
        )
        if union_work != derived_union:
            raise ValueError("union charge does not match the execution proof")
        phases.append("union")

    charges = tuple(int(0 if value is None else value) for value in (
        twl_work, materialization_work, tuple_transport_work,
        child_si_work, union_work,
    ))
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

    if materialized > ledger.branch_count_upper_bound:
        raise ValueError("materialized branches exceed the shared reservation")
    if transported > ledger.branch_count_upper_bound:
        raise ValueError("transported branches exceed the shared reservation")
    if orbit_states > transported * ledger.ambient_group_order:
        raise ValueError("tuple-transport orbit states exceed the ambient bound")
    if action_steps > (
        transported
        * ledger.ambient_group_order
        * max(1, ledger.ambient_generator_count)
    ):
        raise ValueError("tuple-transport action steps exceed the ambient bound")
    if child_count > ledger.branch_count_upper_bound:
        raise ValueError("executed children exceed the shared reservation")
    scan_limit = ledger.branch_count_upper_bound * max(
        ledger.child_state_image_upper_bound,
        2 * ledger.original_degree * ledger.ambient_group_order,
    )
    if scans > scan_limit:
        raise ValueError("child candidate scans exceed the shared reservation")
    if union_generators > ledger.union_generator_inputs_upper_bound:
        raise ValueError("union generator inputs exceed the shared reservation")

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
        executed_source_runs=sr,
        executed_target_runs=tr,
        executed_source_work=sw,
        executed_target_work=tw,
        materialized_branch_count=materialized,
        transported_branch_count=transported,
        transported_orbit_states=orbit_states,
        transported_action_steps=action_steps,
        executed_child_count=child_count,
        permutation_candidates_checked=scans,
        union_generator_count=union_generators,
        phases_recorded=tuple(phases),
    )


__all__ = [
    "DesignPipelineAdmissionLedger",
    "design_pipeline_admission_ledger",
    "record_design_pipeline_execution",
]
