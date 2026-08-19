from __future__ import annotations

from dataclasses import dataclass

from colored_subset_design_branch_plan_v1 import DesignBranchPlan, build_colored_subset_design_branch_plan
from design_branch_tuple_transport_v1 import DesignTupleTransportPlan, transport_complete_design_tuple_branches
from design_tuple_full_string_union_si_v1 import DesignTupleFullStringSI, solve_design_tuple_transport_full_string


@dataclass(frozen=True)
class DesignLemmaCandidateSI:
    status: str
    branch_plan: DesignBranchPlan
    transport_plan: DesignTupleTransportPlan | None
    full_string_result: DesignTupleFullStringSI | None
    theorem_hypotheses_certified: bool
    exact: bool
    complete: bool
    local_log2_cost_bound: float
    reason: str


def design_lemma_candidate_string_isomorphism(
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
    max_wl_vertices: int = 512,
    max_wl_rounds: int = 4096,
    max_branch_pairs: int = 200000,
    max_partition_states: int = 200000,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 256,
    max_depth: int = 64,
) -> DesignLemmaCandidateSI:
    """Compose the exact small-instance Design-Lemma path into full-string SI.

    This is the W1R-H6 composition boundary after a logarithmic colored t-subset
    relation has already been constructed. It verifies the exact source/target
    Design-Lemma witness families, materializes their complete canonical tuple
    branch cover, intersects every branch with the actual signed ambient action,
    and finally intersects all surviving candidate cosets with the original full
    string and reconstructs their exact union.

    Every partial/resource-limited stage fails closed. A returned exact result is
    therefore an exact ambient string-isomorphism set for the supplied relation
    branch cover. This function does not by itself prove the asymptotic Design
    Lemma or the global quasipolynomial recurrence charge; those remain separate
    proof obligations before W1R-H6 can be declared closed.
    """
    plan = build_colored_subset_design_branch_plan(
        vertex_count,
        arity,
        source_relation,
        target_relation,
        alpha=alpha,
        max_states=max_states,
        max_wl_vertices=max_wl_vertices,
        max_wl_rounds=max_wl_rounds,
        max_branch_pairs=max_branch_pairs,
    )
    source_gate = bool(plan.source_family.theorem_parameter_gate and plan.source_family.symmetry_defect_gate)
    target_gate = bool(plan.target_family.theorem_parameter_gate and plan.target_family.symmetry_defect_gate)
    theorem_gate = source_gate and target_gate

    if plan.exact_empty:
        return DesignLemmaCandidateSI(
            "exact_empty_design_lemma_relation_branch_plan",
            plan,
            None,
            None,
            theorem_gate,
            True,
            True,
            plan.local_log2_cost_bound,
            plan.reason,
        )
    if not plan.complete or plan.status != "certified_complete_design_branch_plan":
        return DesignLemmaCandidateSI(
            "undetermined_design_lemma_branch_plan",
            plan,
            None,
            None,
            theorem_gate,
            False,
            False,
            0.0,
            plan.reason,
        )

    transport = transport_complete_design_tuple_branches(
        group,
        lifted_generators,
        plan,
        max_partition_states=max_partition_states,
    )
    if transport.exact_empty:
        return DesignLemmaCandidateSI(
            "exact_empty_design_lemma_tuple_transport",
            plan,
            transport,
            None,
            theorem_gate,
            True,
            True,
            transport.local_log2_cost_bound,
            transport.reason,
        )
    if not transport.complete or transport.status != "certified_complete_design_tuple_transport_cover":
        return DesignLemmaCandidateSI(
            "undetermined_design_lemma_tuple_transport",
            plan,
            transport,
            None,
            theorem_gate,
            False,
            False,
            0.0,
            transport.reason,
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
        return DesignLemmaCandidateSI(
            "undetermined_design_lemma_full_string_branch",
            plan,
            transport,
            full,
            theorem_gate,
            False,
            False,
            0.0,
            full.reason,
        )

    status = (
        "exact_empty_design_lemma_full_string"
        if full.coset is None
        else "exact_design_lemma_full_string_coset"
    )
    return DesignLemmaCandidateSI(
        status,
        plan,
        transport,
        full,
        theorem_gate,
        True,
        True,
        full.explicit_union_log2_cost_bound,
        "exact Design-Lemma branch cover, exact signed tuple transport, and exact full-string union reconstruction all completed",
    )
