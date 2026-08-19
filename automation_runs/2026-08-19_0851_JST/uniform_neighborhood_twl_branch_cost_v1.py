from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log, log2

from uniform_neighborhood_twl_design_family_v1 import UniformNeighborhoodTWLFamilyProgress


@dataclass(frozen=True)
class UniformNeighborhoodTWLBranchCost:
    status: str
    root_n: int
    right_size: int
    neighborhood_count: int
    arity: int
    individualization_length: int | None
    materialized_single_side_branches: int
    single_side_branch_bound: int
    paired_branch_bound: int
    provenance_arity_cap: int
    theorem_log2_branch_bound: float
    certified: bool
    reason: str


def certify_uniform_neighborhood_twl_branch_cost(
    progress: UniformNeighborhoodTWLFamilyProgress,
    *,
    root_n: int,
    neighborhood_count: int,
) -> UniformNeighborhoodTWLBranchCost:
    """Certify rev204->rev206 Design branching has quasipolynomial multiplicity.

    The rev204 containment-count relation uses

        t <= 6 * ceil(log(m) / log(v)),

    where ``m`` is the number of distinct uniform neighborhoods and ``v`` is the
    right-ground size.  A rev206 exact Design witness level has ell<t and at most
    ``v*(v-1)*...*(v-ell+1) <= v**ell`` successful tuples on one side.  Pairing
    source and target witness families therefore costs at most ``v**(2*ell)``.

    If ``m,v <= root_n`` and ``v>=2``, the rev204 arity cap is at most
    ``6*ceil(log2(root_n))``.  Consequently the paired logarithmic branch charge is
    at most ``12*ceil(log2(root_n))*log2(root_n) = O(log^2 root_n)``.

    This certificate covers only branch multiplicity.  It does not certify the
    downstream child SI, the residual corrected Split-or-Johnson branch, or the
    global recurrence measure.
    """
    r = int(root_n)
    v = int(progress.right_size)
    m = int(neighborhood_count)
    t = int(progress.arity)
    ell = progress.minimal_individualization_length
    if r < 2 or v < 2 or m < 1:
        raise ValueError("root_n/right_size must be >=2 and neighborhood_count positive")
    if v > r or m > r:
        return UniformNeighborhoodTWLBranchCost(
            "undetermined_twl_branch_provenance_size_gate",
            r, v, m, t, ell, progress.branch_count, 0, 0, 0, 0.0, False,
            "rev204 provenance requires right-ground size and neighborhood count not exceed root_n",
        )

    provenance_cap = max(1, 6 * ceil(log(max(2, m)) / log(max(2, v))))
    if t > provenance_cap:
        return UniformNeighborhoodTWLBranchCost(
            "undetermined_twl_branch_rev204_arity_gate",
            r, v, m, t, ell, progress.branch_count, 0, 0,
            provenance_cap, 0.0, False,
            "supplied relation arity exceeds the exact rev204 containment-count provenance cap",
        )

    if progress.twl_family_status is None:
        return UniformNeighborhoodTWLBranchCost(
            "certified_zero_twl_branch_charge",
            r, v, m, t, ell, 0, 0, 0, provenance_cap, 0.0, True,
            "rev205 preempted the exact k-WL family, so this layer adds no Design individualization branches",
        )
    if (
        not progress.exact
        or not progress.canonical_branch_family
        or progress.twl_family_status != "certified_exact_twl_design_witness_family"
    ):
        return UniformNeighborhoodTWLBranchCost(
            "undetermined_incomplete_twl_branch_family",
            r, v, m, t, ell, progress.branch_count, 0, 0,
            provenance_cap, 0.0, False,
            "branch-cost certification requires an exact complete first-successful-level k-WL Design family",
        )
    if ell is None or ell < 0 or ell >= t:
        return UniformNeighborhoodTWLBranchCost(
            "undetermined_twl_individualization_length",
            r, v, m, t, ell, progress.branch_count, 0, 0,
            provenance_cap, 0.0, False,
            "exact Design family does not expose a valid ell<arity individualization level",
        )

    single_bound = v ** ell
    if progress.branch_count > single_bound:
        raise AssertionError("materialized witness count exceeds v**ell")
    paired_bound = single_bound ** 2
    coarse_log_cap = 12.0 * ceil(log2(max(2, r))) * log2(max(2, r))
    actual_paired_log = log2(max(1, paired_bound))
    if actual_paired_log > coarse_log_cap + 1e-12:
        raise AssertionError("rev204 provenance failed the derived O(log^2 n) branch exponent bound")
    return UniformNeighborhoodTWLBranchCost(
        "certified_uniform_neighborhood_twl_quasipoly_branch_cost",
        r,
        v,
        m,
        t,
        ell,
        progress.branch_count,
        single_bound,
        paired_bound,
        provenance_cap,
        coarse_log_cap,
        True,
        "rev204 controlled arity plus the complete minimal k-WL witness level bounds the eventual source/target branch cover by v^(2*ell), with O(log^2 root_n) logarithmic multiplicity",
    )
