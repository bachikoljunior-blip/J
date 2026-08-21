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
from design_tuple_full_string_union_si_v1 import DesignTupleFullStringSI, solve_design_tuple_transport_full_string


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
    max_partition_states: int = 200000,
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
    twl_resource = paired_correlated_twl_resource_envelope(
        root_n, vertex_count, arity, max_paired_twl_work_units,
    )
    if not twl_resource.admitted:
        return ExactTWLDesignCandidateSI(
            "undetermined_exact_twl_resource_preflight", None, None, None, None,
            False, False, False, False, False, twl_resource.reason, twl_resource,
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
        )
    if not plan.complete or plan.status != "certified_complete_design_branch_plan":
        return ExactTWLDesignCandidateSI(
            "undetermined_exact_twl_design_branch_plan", plan, None, None, None,
            theorem_gate, False, False, False, False, plan.reason, twl_resource,
        )

    branch_cost = certify_design_branch_quasipoly_cost(plan, root_n=root_n)
    if not branch_cost.certified:
        return ExactTWLDesignCandidateSI(
            "undetermined_exact_twl_design_branch_cost", plan, branch_cost, None, None,
            theorem_gate, fidelity, False, False, False, branch_cost.reason, twl_resource,
        )

    transport = transport_complete_design_tuple_branches(
        group,
        lifted_generators,
        plan,
        max_partition_states=max_partition_states,
    )
    if transport.exact_empty:
        return ExactTWLDesignCandidateSI(
            "exact_empty_exact_twl_design_transport", plan, branch_cost, transport, None,
            theorem_gate, fidelity, True, True, True, transport.reason, twl_resource,
        )
    if not transport.complete or transport.status != "certified_complete_design_tuple_transport_cover":
        return ExactTWLDesignCandidateSI(
            "undetermined_exact_twl_design_transport", plan, branch_cost, transport, None,
            theorem_gate, fidelity, True, False, False, transport.reason, twl_resource,
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
    )
    if not full.exact:
        return ExactTWLDesignCandidateSI(
            "undetermined_exact_twl_design_full_string", plan, branch_cost, transport, full,
            theorem_gate, fidelity, True, False, False, full.reason, twl_resource,
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
    )
