from __future__ import annotations

from dataclasses import dataclass

from uniform_neighborhood_twl_branch_cost_v1 import UniformNeighborhoodTWLBranchCost
from uniform_neighborhood_twl_design_family_v1 import UniformNeighborhoodTWLFamilyProgress


@dataclass(frozen=True)
class UniformNeighborhoodTWLRecurrenceFrontier:
    status: str
    right_size: int
    branch_count: int
    total_child_occurrences: int
    max_child_aux_size: int | None
    shrink_fraction: float
    branch_cost_certified: bool
    all_branch_edges_shrink: bool
    canonical: bool
    local_log2_cost_bound: float
    exact: bool
    reason: str


def certify_uniform_neighborhood_twl_recurrence_frontier(
    progress: UniformNeighborhoodTWLFamilyProgress,
    branch_cost: UniformNeighborhoodTWLBranchCost,
    *,
    shrink_fraction: float = 0.9,
) -> UniformNeighborhoodTWLRecurrenceFrontier:
    """Verify every materialized rev206 witness branch has a true aux-shrink edge.

    Rev206 records the exact auxiliary child sizes exposed by each accepted Design
    witness. Rev207 independently certifies the controlled-arity branch
    multiplicity. This verifier joins those two orthogonal facts: every branch must
    be canonical/exact, every branch must have structural progress, every materialized
    child must have size at most ``shrink_fraction*|V2|`` and strictly below |V2|,
    and the branch-cost certificate must match the same ground/arity.

    Passing this gate closes the *local recurrence frontier* only. The child nodes
    are not declared terminal: each smaller auxiliary subproblem still requires its
    exact downstream SI implementation and recursively certified accounting before
    the global recurrence validator may accept the tree.
    """
    if not 0.0 < shrink_fraction < 1.0:
        raise ValueError("shrink_fraction must lie in (0,1)")
    v = int(progress.right_size)
    if not progress.exact or not progress.canonical_branch_family:
        return UniformNeighborhoodTWLRecurrenceFrontier(
            "undetermined_nonexact_twl_frontier", v, progress.branch_count, 0,
            None, shrink_fraction, branch_cost.certified, False, False,
            progress.local_log2_cost_bound, False,
            "the Design branch family is not exact and canonical",
        )
    if not branch_cost.certified:
        return UniformNeighborhoodTWLRecurrenceFrontier(
            "undetermined_twl_frontier_branch_cost", v, progress.branch_count, 0,
            None, shrink_fraction, False, False, True,
            progress.local_log2_cost_bound, False,
            "the Design branch multiplicity lacks its independent quasipolynomial certificate",
        )
    if branch_cost.right_size != v or branch_cost.arity != progress.arity:
        return UniformNeighborhoodTWLRecurrenceFrontier(
            "undetermined_twl_frontier_certificate_mismatch", v, progress.branch_count, 0,
            None, shrink_fraction, True, False, True,
            progress.local_log2_cost_bound, False,
            "branch-cost certificate does not describe the same right-ground relation",
        )
    if not progress.all_witness_branches_progress or progress.residual_branch_count:
        return UniformNeighborhoodTWLRecurrenceFrontier(
            "twl_frontier_has_structural_residual", v, progress.branch_count, 0,
            progress.max_child_aux_size, shrink_fraction, True, False, True,
            progress.local_log2_cost_bound + branch_cost.theorem_log2_branch_bound,
            True,
            "at least one canonical Design witness branch still requires corrected Split-or-Johnson rather than exposing an alpha-smaller child",
        )
    child_families = tuple(progress.branch_child_aux_sizes)
    if len(child_families) != progress.branch_count or not child_families:
        return UniformNeighborhoodTWLRecurrenceFrontier(
            "undetermined_twl_frontier_child_inventory", v, progress.branch_count, 0,
            None, shrink_fraction, True, False, True,
            progress.local_log2_cost_bound + branch_cost.theorem_log2_branch_bound,
            False,
            "exact child-size inventory is missing for at least one materialized Design branch",
        )

    total = 0
    max_child = 0
    limit = shrink_fraction * v + 1e-12
    for children in child_families:
        if not children:
            return UniformNeighborhoodTWLRecurrenceFrontier(
                "undetermined_twl_frontier_empty_progress_branch", v, progress.branch_count,
                total, max_child or None, shrink_fraction, True, False, True,
                progress.local_log2_cost_bound + branch_cost.theorem_log2_branch_bound,
                False,
                "a branch marked as structural progress exposes no auxiliary child measure",
            )
        for size in children:
            size = int(size)
            total += 1
            max_child = max(max_child, size)
            if size < 1 or size >= v or size > limit:
                return UniformNeighborhoodTWLRecurrenceFrontier(
                    "undetermined_twl_frontier_insufficient_aux_shrink", v,
                    progress.branch_count, total, max_child, shrink_fraction, True,
                    False, True,
                    progress.local_log2_cost_bound + branch_cost.theorem_log2_branch_bound,
                    False,
                    "a materialized Design child violates the required strict alpha-bounded auxiliary shrink",
                )

    return UniformNeighborhoodTWLRecurrenceFrontier(
        "certified_twl_design_aux_shrink_frontier",
        v,
        progress.branch_count,
        total,
        max_child,
        shrink_fraction,
        True,
        True,
        True,
        progress.local_log2_cost_bound + branch_cost.theorem_log2_branch_bound,
        True,
        "every branch in the canonical exact Design witness family has only strict alpha-smaller auxiliary children and the eventual source/target branch multiplicity is quasipolynomially certified; exact recursive SI children remain the next leaf",
    )
