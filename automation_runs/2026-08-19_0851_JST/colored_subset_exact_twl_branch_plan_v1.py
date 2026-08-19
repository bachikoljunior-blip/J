from __future__ import annotations

from math import log2

from colored_subset_design_branch_plan_v1 import DesignBranchPlan
from colored_subset_exact_twl_design_v1 import paired_exact_twl_design_witness_families


def build_exact_twl_design_branch_plan(
    vertex_count: int,
    arity: int,
    source_colors,
    target_colors,
    *,
    alpha: float = 0.9,
    max_states: int = 200000,
    max_tuple_states: int = 250000,
    max_rounds: int | None = None,
    max_work_units: int = 500000000,
    max_branch_pairs: int = 200000,
) -> DesignBranchPlan:
    """Build the complete Design witness branch cover from exact standard k-WL.

    This returns the existing `DesignBranchPlan` interface so the already-verified
    signed tuple transporter and exact full-string branch-union machinery can be
    reused unchanged. The source/target family objects are the exact-k-WL family
    type; downstream consumers only rely on their shared theorem-gate attributes.
    """
    if max_branch_pairs < 1:
        raise ValueError("max_branch_pairs must be positive")
    v = int(vertex_count)
    k = int(arity)
    paired = paired_exact_twl_design_witness_families(
        v,
        k,
        tuple(source_colors),
        tuple(target_colors),
        alpha=alpha,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_rounds=max_rounds,
        max_work_units=max_work_units,
    )
    source = paired.source
    target = paired.target
    base_bound = source.local_log2_cost_bound + target.local_log2_cost_bound + 16.0

    if paired.exact_empty:
        return DesignBranchPlan(
            paired.status,
            v,
            k,
            None,
            source,
            target,
            (),
            0,
            base_bound + 16.0,
            True,
            True,
            paired.reason,
        )
    if not paired.complete or paired.status != "certified_paired_exact_twl_design_family":
        return DesignBranchPlan(
            "undetermined_exact_twl_design_branch_plan",
            v,
            k,
            None,
            source,
            target,
            (),
            0,
            base_bound,
            False,
            False,
            paired.reason,
        )

    ell = source.minimal_individualization_length
    if ell != target.minimal_individualization_length or ell is None:
        raise AssertionError("paired exact-k-WL family was certified with inconsistent minimal levels")
    source_tuples = tuple(outcome.individualized for outcome in source.witness_outcomes)
    target_tuples = tuple(outcome.individualized for outcome in target.witness_outcomes)
    branch_count = len(source_tuples) * len(target_tuples)
    branch_bound = base_bound + log2(max(1, branch_count)) + 24.0
    if branch_count > max_branch_pairs:
        return DesignBranchPlan(
            "undetermined_exact_twl_design_branch_pair_limit",
            v,
            k,
            ell,
            source,
            target,
            (),
            branch_count,
            branch_bound,
            False,
            False,
            "the complete theorem-faithful witness Cartesian cover exceeds the explicit branch materialization cap",
        )

    branches = tuple((xs, yt) for xs in source_tuples for yt in target_tuples)
    return DesignBranchPlan(
        "certified_complete_design_branch_plan",
        v,
        k,
        ell,
        source,
        target,
        branches,
        branch_count,
        branch_bound,
        False,
        True,
        "the complete first-successful exact standard-k-WL Design witness families are paired without choosing a label-dependent representative",
    )
