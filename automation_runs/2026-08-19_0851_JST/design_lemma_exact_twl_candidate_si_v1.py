from __future__ import annotations

from dataclasses import dataclass

from colored_subset_design_branch_plan_v1 import DesignBranchPlan
from colored_subset_exact_twl_branch_plan_v1 import build_exact_twl_design_branch_plan
from correlated_twl_resource_envelope_v1 import (
    PairedCorrelatedTWLResourceEnvelope,
    paired_correlated_twl_resource_envelope,
    record_paired_correlated_twl_execution,
)
from design_branch_tuple_transport_v1 import DesignTupleTransportPlan, transport_complete_design_tuple_branches
from design_lemma_branch_cost_certificate_v1 import DesignBranchCostCertificate, certify_design_branch_quasipoly_cost
from design_original_root_pipeline_resource_v1 import (
    DesignOriginalRootPipelineResourceEnvelope,
    design_original_root_pipeline_resource_envelope,
    record_design_original_root_pipeline_phase,
)
from design_tuple_full_string_union_si_v1 import DesignTupleFullStringSI, solve_design_tuple_transport_full_string
from design_tuple_transport_resource_envelope_v1 import (
    DesignTupleTransportResourceEnvelope,
    design_tuple_transport_resource_envelope,
    record_design_tuple_transport_execution,
)


@dataclass(frozen=True)
class ExactTWLDesignCandidateSI:
    status: str
    branch_plan: DesignBranchPlan | None
    branch_cost: DesignBranchCostCertificate | None
    transport_plan: DesignTupleTransportPlan | None
    full_string_result: DesignTupleFullStringSI | None
    theorem_hypotheses_certified: bool
    theorem_fidelity_certified: bool
    branch_cost_certified: bool
    exact: bool
    complete: bool
    reason: str
    twl_resource_envelope: PairedCorrelatedTWLResourceEnvelope | None = None
    transport_resource_envelope: DesignTupleTransportResourceEnvelope | None = None
    pipeline_resource_envelope: DesignOriginalRootPipelineResourceEnvelope | None = None


def exact_twl_design_candidate_string_isomorphism(
    group,
    lifted_generators,
    vertex_count: int,
    arity: int,
    source_relation,
    target_relation,
    source_values,
    target_values,
    *,
    root_n: int,
    alpha: float = 0.9,
    max_states: int = 200000,
    max_tuple_states: int = 250000,
    max_twl_rounds: int | None = None,
    max_twl_work_units: int = 500000000,
    max_paired_twl_work_units: int = 10**30,
    max_branch_pairs: int = 200000,
    max_design_branch_materialization_work: int = 10**30,
    max_partition_states: int = 200000,
    max_design_transport_work: int = 10**30,
    max_design_pipeline_work: int = 10**1000,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 256,
    max_depth: int = 64,
) -> ExactTWLDesignCandidateSI:
    """Compose exact standard k-WL Design branching through full ambient-string SI.

    Compared with the earlier incidence-2WL execution boundary, this path verifies
    the actual correlated-replacement k-WL + Split-or-UPCC witness mechanism before
    reusing the exact tuple transporter and branch-union machinery. The explicit
    tuple-pair branch multiplicity is also certified against the logarithmic arity
    gate. Recursive-child measure decrease remains a separate global recurrence
    obligation and is not inferred from an exact result here.
    """
    pipeline_resource = design_original_root_pipeline_resource_envelope(
        group,
        original_root_degree=root_n,
        vertex_count=vertex_count,
        arity=arity,
        target_values=target_values,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_work=max_design_pipeline_work,
    )
    if not pipeline_resource.admitted:
        return ExactTWLDesignCandidateSI(
            "undetermined_design_original_root_pipeline_preflight",
            None, None, None, None, False, False, False, False, False,
            pipeline_resource.reason, None, None, pipeline_resource,
        )

    twl_resource = paired_correlated_twl_resource_envelope(
        root_n, vertex_count, arity,
        min(max_paired_twl_work_units, pipeline_resource.phase_work_upper_bounds[0]),
    )
    if not twl_resource.admitted:
        return ExactTWLDesignCandidateSI(
            "undetermined_exact_twl_resource_preflight", None, None, None, None,
            False, False, False, False, False, twl_resource.reason, twl_resource,
            None, pipeline_resource,
        )

    plan = build_exact_twl_design_branch_plan(
        vertex_count,
        arity,
        source_relation,
        target_relation,
        alpha=alpha,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_rounds=max_twl_rounds,
        max_work_units=max_twl_work_units,
        max_branch_pairs=max_branch_pairs,
        original_root_degree=root_n,
        max_materialization_work=min(
            max_design_branch_materialization_work,
            pipeline_resource.phase_work_upper_bounds[1],
        ),
    )
    source_family = plan.source_family
    target_family = plan.target_family
    twl_resource = record_paired_correlated_twl_execution(
        twl_resource,
        executed_source_runs=int(getattr(source_family, "states_checked", 0)),
        executed_target_runs=int(getattr(target_family, "states_checked", 0)),
        executed_source_work=int(getattr(source_family, "work_units", 0)),
        executed_target_work=int(getattr(target_family, "work_units", 0)),
        complete=bool(
            getattr(source_family, "exact", False)
            and getattr(target_family, "exact", False)
        ),
    )
    pipeline_resource = record_design_original_root_pipeline_phase(
        pipeline_resource, "twl", charged_work=twl_resource.charged_paired_work,
    )
    source_gate = bool(
        getattr(plan.source_family, "theorem_parameter_gate", False)
        and getattr(plan.source_family, "symmetry_defect_gate", False)
    )
    target_gate = bool(
        getattr(plan.target_family, "theorem_parameter_gate", False)
        and getattr(plan.target_family, "symmetry_defect_gate", False)
    )
    theorem_gate = source_gate and target_gate
    fidelity = bool(
        getattr(plan.source_family, "status", "") == "certified_exact_twl_design_witness_family"
        and getattr(plan.target_family, "status", "") == "certified_exact_twl_design_witness_family"
        and plan.complete
    )

    if plan.exact_empty:
        return ExactTWLDesignCandidateSI(
            "exact_empty_exact_twl_design_branch_plan", plan, None, None, None,
            theorem_gate, False, False, True, True, plan.reason, twl_resource,
            None, pipeline_resource,
        )
    if not plan.complete or plan.status != "certified_complete_design_branch_plan":
        return ExactTWLDesignCandidateSI(
            "undetermined_exact_twl_design_branch_plan", plan, None, None, None,
            theorem_gate, False, False, False, False, plan.reason, twl_resource,
            None, pipeline_resource,
        )

    materialization_resource = getattr(plan, "materialization_resource_envelope", None)
    if materialization_resource is None or not materialization_resource.complete:
        return ExactTWLDesignCandidateSI(
            "undetermined_exact_twl_design_materialization_ledger",
            plan, None, None, None, theorem_gate, fidelity, False, False, False,
            "a complete branch plan did not carry its complete materialization charge",
            twl_resource, None, pipeline_resource,
        )
    pipeline_resource = record_design_original_root_pipeline_phase(
        pipeline_resource,
        "materialization",
        charged_work=int(materialization_resource.charged_work_upper_bound),
    )

    branch_cost = certify_design_branch_quasipoly_cost(plan, root_n=root_n)
    if not branch_cost.certified:
        return ExactTWLDesignCandidateSI(
            "undetermined_exact_twl_design_branch_cost", plan, branch_cost, None, None,
            theorem_gate, fidelity, False, False, False, branch_cost.reason, twl_resource,
            None, pipeline_resource,
        )

    transport_resource = design_tuple_transport_resource_envelope(
        root_n,
        int(group.degree),
        vertex_count,
        int(plan.individualization_length or 0),
        int(plan.branch_count),
        int(group.order),
        max(1, len(tuple(group.original_generators))),
        min(max_design_transport_work, pipeline_resource.phase_work_upper_bounds[2]),
    )
    if not transport_resource.admitted:
        return ExactTWLDesignCandidateSI(
            "undetermined_exact_twl_design_transport_resource_preflight",
            plan, branch_cost, None, None, theorem_gate, fidelity, True,
            False, False, transport_resource.reason, twl_resource,
            transport_resource, pipeline_resource,
        )

    transport = transport_complete_design_tuple_branches(
        group,
        lifted_generators,
        plan,
        max_partition_states=max_partition_states,
    )
    if transport.complete:
        transport_resource = record_design_tuple_transport_execution(
            transport_resource,
            executed_branches=transport.executed_branch_count,
            executed_orbit_states=transport.total_orbit_states,
            executed_action_steps=transport.total_action_steps,
            complete=True,
        )
        pipeline_resource = record_design_original_root_pipeline_phase(
            pipeline_resource,
            "transport",
            charged_work=transport_resource.charged_work_upper_bound,
        )
    if transport.exact_empty:
        return ExactTWLDesignCandidateSI(
            "exact_empty_exact_twl_design_transport", plan, branch_cost, transport, None,
            theorem_gate, fidelity, True, True, True, transport.reason, twl_resource,
            transport_resource, pipeline_resource,
        )
    if not transport.complete or transport.status != "certified_complete_design_tuple_transport_cover":
        return ExactTWLDesignCandidateSI(
            "undetermined_exact_twl_design_transport", plan, branch_cost, transport, None,
            theorem_gate, fidelity, True, False, False, transport.reason, twl_resource,
            transport_resource, pipeline_resource,
        )

    full = solve_design_tuple_transport_full_string(
        group,
        transport,
        source_values,
        target_values,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_depth=max_depth,
        max_design_full_string_child_work=pipeline_resource.phase_work_upper_bounds[3],
        max_design_union_reconstruction_work=pipeline_resource.phase_work_upper_bounds[4],
    )
    if full.child_preflight is not None and full.child_preflight.complete:
        pipeline_resource = record_design_original_root_pipeline_phase(
            pipeline_resource,
            "children",
            charged_work=int(full.child_preflight.work_upper_bound),
        )
    if full.union_resource_envelope is not None and full.union_resource_envelope.complete:
        pipeline_resource = record_design_original_root_pipeline_phase(
            pipeline_resource,
            "union",
            charged_work=int(full.union_resource_envelope.work_upper_bound),
        )
    if not full.exact:
        return ExactTWLDesignCandidateSI(
            "undetermined_exact_twl_design_full_string", plan, branch_cost, transport, full,
            theorem_gate, fidelity, True, False, False, full.reason, twl_resource,
            transport_resource, pipeline_resource,
        )
    return ExactTWLDesignCandidateSI(
        "exact_empty_exact_twl_design_full_string" if full.coset is None else "exact_twl_design_full_string_coset",
        plan,
        branch_cost,
        transport,
        full,
        theorem_gate,
        fidelity,
        True,
        True,
        True,
        "exact standard-k-WL Design witness family, quasipolynomial branch charge, exact ambient tuple transport, and exact full-string union all certified",
        twl_resource,
        transport_resource,
        pipeline_resource,
    )
