from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log2

from colored_subset_design_branch_plan_v1 import DesignBranchPlan


@dataclass(frozen=True)
class DesignBranchCostCertificate:
    status: str
    root_n: int
    ground_size: int
    arity: int
    individualization_length: int | None
    branch_count: int
    theorem_arity_cap: int
    branch_log2_bound: float
    certified: bool
    reason: str


def certify_design_branch_quasipoly_cost(
    plan: DesignBranchPlan,
    *,
    root_n: int,
) -> DesignBranchCostCertificate:
    """Certify the explicit tuple-pair branching charge is quasipolynomial.

    For a complete first-successful Design-Lemma level of ordered ell-tuples,
    each witness family is a subset of the v*(v-1)*...*(v-ell+1) possible
    individualizations. Therefore the Cartesian source/target cover has at most
    v^(2*ell) branches. If ell < arity <= ceil(log2(root_n)) and v <= root_n,
    its logarithmic branching charge is at most
    2*ceil(log2(root_n))*log2(root_n), i.e. O(log^2 root_n).

    This certificate covers the explicit branch multiplicity only. It does not
    certify that every recursive child has sufficient measure decrease, so it is
    intentionally not a global W1R-H6 recurrence certificate.
    """
    r = int(root_n)
    v = int(plan.vertex_count)
    t = int(plan.arity)
    ell = plan.individualization_length
    cap = max(1, ceil(log2(max(2, r))))
    if r < 1 or v < 1:
        raise ValueError("root and ground sizes must be positive")
    if plan.exact_empty:
        return DesignBranchCostCertificate(
            "certified_empty_design_branch_cost",
            r, v, t, ell, plan.branch_count, cap, 0.0, True,
            "the exact branch plan is empty, so its branching charge is zero",
        )
    if not plan.complete or plan.status != "certified_complete_design_branch_plan":
        return DesignBranchCostCertificate(
            "undetermined_incomplete_design_branch_cost",
            r, v, t, ell, plan.branch_count, cap, 0.0, False,
            "quasipolynomial branch certification requires a complete exact Design branch plan",
        )
    if ell is None or ell < 0 or ell >= t:
        return DesignBranchCostCertificate(
            "undetermined_design_individualization_length",
            r, v, t, ell, plan.branch_count, cap, 0.0, False,
            "complete Design branch plan does not expose a valid ell<arity individualization level",
        )
    if v > r or t > cap:
        return DesignBranchCostCertificate(
            "undetermined_design_quasipoly_parameter_gate",
            r, v, t, ell, plan.branch_count, cap, 0.0, False,
            "ground size or Design arity exceeds the root/logarithmic theorem gate",
        )

    branch_bound = (v ** ell) ** 2
    if plan.branch_count > branch_bound:
        raise AssertionError("materialized Design branch count exceeds the ordered-tuple Cartesian bound")
    actual_log = log2(max(1, plan.branch_count))
    theorem_log = 2.0 * cap * log2(max(2, r))
    if actual_log > theorem_log + 1e-12:
        raise AssertionError("Design branch count violates the derived O(log^2 n) exponent bound")
    return DesignBranchCostCertificate(
        "certified_design_branch_quasipoly_cost",
        r, v, t, ell, plan.branch_count, cap,
        theorem_log, True,
        "complete minimal Design witness branching is bounded by v^(2*ell) with ell<arity<=ceil(log2(root_n)), giving an O(log^2 root_n) logarithmic branch charge",
    )
