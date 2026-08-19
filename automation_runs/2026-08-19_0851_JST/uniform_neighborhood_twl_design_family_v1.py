from __future__ import annotations

from dataclasses import dataclass
from math import log2
from typing import Hashable, Iterable

from colored_subset_exact_twl_design_v1 import find_exact_twl_design_witness_family
from design_twl_recurrence_progress_v1 import certify_design_twl_recurrence_progress
from uniform_neighborhood_relation_descent_v1 import (
    UniformNeighborhoodRelationDescent,
    _canonical_rows,
    descend_uniform_neighborhood_test_relation,
)


@dataclass(frozen=True)
class UniformNeighborhoodTWLFamilyProgress:
    status: str
    right_size: int
    arity: int
    base_descent_status: str
    twl_family_status: str | None
    minimal_individualization_length: int | None
    branch_count: int
    branch_bound: int
    branch_statuses: tuple[str, ...]
    progress_branch_count: int
    residual_branch_count: int
    max_child_aux_size: int | None
    all_witness_branches_progress: bool
    canonical_branch_family: bool
    local_log2_cost_bound: float
    exact: bool
    reason: str


def _falling_factorial(n: int, r: int) -> int:
    out = 1
    for i in range(r):
        out *= n - i
    return out


def close_uniform_neighborhood_relation_with_twl_family(
    right_size: int,
    arity: int,
    coordinates: Iterable[Iterable[int]],
    colors: Iterable[Hashable],
    *,
    root_n: int | None = None,
    alpha: float = 0.9,
    max_subsets: int = 200000,
    max_johnson_nodes: int = 500000,
    max_states: int = 200000,
    max_tuple_states: int = 250000,
    max_rounds: int | None = None,
    max_family_work_units: int = 500000000,
    max_branch_work_units: int = 100000000,
) -> UniformNeighborhoodTWLFamilyProgress:
    """Use the exact Design-Lemma k-WL family only after rev205 stalls.

    This adapter is deliberately layered.  It first executes the cheaper exact
    codegree/pair descent from rev205.  Only the genuinely higher-arity homogeneous
    residual is passed to the existing exact standard-k-WL Design witness family.
    The complete first successful individualization level is exhausted by that
    routine, making the *set of successful branches* equivariant rather than
    selecting a label-dependent witness.

    Every returned Design witness is then replayed through the existing recurrence
    progress adapter.  Alpha-bounded colorings/imprimitive partitions and UPCCs
    already reduced by coherent/Johnson machinery count as structural progress.
    A UPCC that still needs the corrected full Split-or-Johnson theorem is retained
    as a typed residual branch.  Thus ``all_witness_branches_progress`` is strong:
    it is true only when every branch in the canonical witness family has a proved
    strictly smaller auxiliary measure.  Downstream SI children remain unsolved and
    must still replace the recurrence placeholders before any global closure claim.
    """
    rows = _canonical_rows(right_size, arity, coordinates, colors)
    v = int(right_size)
    k = int(arity)
    if root_n is None:
        root_n = v
    root_n = int(root_n)
    if root_n < v or root_n < 1:
        raise ValueError("root_n must dominate the right-ground size")

    palette = tuple(value for _, value in rows)
    base: UniformNeighborhoodRelationDescent = descend_uniform_neighborhood_test_relation(
        v,
        k,
        tuple(U for U, _ in rows),
        palette,
        max_class_fraction=alpha,
        max_subsets=max_subsets,
        max_johnson_nodes=max_johnson_nodes,
    )
    if base.status != "right_higher_arity_design_unresolved":
        decisive = base.significant_split or base.status in {
            "certified_right_pair_johnson_reduction",
            "certified_right_codegree_pair_johnson_reduction",
        }
        return UniformNeighborhoodTWLFamilyProgress(
            "rev205_descent_preempts_twl_family" if decisive else "rev205_non_twl_residual",
            v,
            k,
            base.status,
            None,
            None,
            0,
            0,
            (),
            0,
            0,
            base.largest_cell if decisive else None,
            decisive,
            True,
            0.0,
            base.exact,
            "rev205 already classified this relation; exact k-WL Design branching is reserved for its higher-arity homogeneous residual",
        )

    family = find_exact_twl_design_witness_family(
        v,
        k,
        palette,
        alpha=alpha,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_rounds=max_rounds,
        max_work_units=max_family_work_units,
    )
    if not family.exact or family.status != "certified_exact_twl_design_witness_family":
        return UniformNeighborhoodTWLFamilyProgress(
            "undetermined_exact_twl_design_family",
            v,
            k,
            base.status,
            family.status,
            family.minimal_individualization_length,
            0,
            0,
            (),
            0,
            0,
            None,
            False,
            False,
            family.local_log2_cost_bound,
            False,
            "rev205 stalled, but the exact standard-k-WL Design family did not clear all theorem/resource/mechanical gates: " + family.reason,
        )

    ell = int(family.minimal_individualization_length or 0)
    branch_bound = _falling_factorial(v, ell)
    if len(family.witness_outcomes) > branch_bound:
        raise AssertionError("witness family exceeds the complete individualization level")

    structural_progress = {
        "certified_design_auxiliary_split_progress",
        "certified_design_upcc_split_or_johnson_progress",
    }
    branch_statuses = []
    progress_count = 0
    residual_count = 0
    max_child = None
    max_branch_bound = 0.0
    for outcome in family.witness_outcomes:
        progress = certify_design_twl_recurrence_progress(
            v,
            k,
            palette,
            outcome.individualized,
            root_n=root_n,
            alpha=alpha,
            max_tuple_states=max_tuple_states,
            max_rounds=max_rounds,
            max_work_units=max_branch_work_units,
            max_johnson_nodes=max_johnson_nodes,
        )
        branch_statuses.append(progress.status)
        max_branch_bound = max(max_branch_bound, progress.local_log2_cost_bound)
        if progress.status in structural_progress and progress.aux_shrink_certified:
            progress_count += 1
            if progress.max_child_aux_size is not None:
                max_child = (
                    progress.max_child_aux_size
                    if max_child is None
                    else max(max_child, progress.max_child_aux_size)
                )
        else:
            residual_count += 1

    branch_count = len(branch_statuses)
    all_progress = branch_count > 0 and residual_count == 0
    local_bound = (
        family.local_log2_cost_bound
        + log2(max(2, branch_count))
        + max_branch_bound
        + 16.0
    )
    if all_progress:
        status = "certified_canonical_twl_design_branch_decomposition"
        reason = (
            "rev205's higher-arity homogeneous residual has a complete first-successful-level exact k-WL Design witness family, and every witness branch proves a strictly alpha-smaller auxiliary structural child; downstream exact SI/accounting children remain open"
        )
    else:
        status = "canonical_twl_design_family_with_split_or_johnson_residual"
        reason = (
            "the exact minimal k-WL Design witness family is canonical as a set of branches, but at least one UPCC/clique-side branch still lacks a verified alpha-smaller coherent/Johnson reduction and remains a corrected Split-or-Johnson child"
        )
    return UniformNeighborhoodTWLFamilyProgress(
        status,
        v,
        k,
        base.status,
        family.status,
        ell,
        branch_count,
        branch_bound,
        tuple(branch_statuses),
        progress_count,
        residual_count,
        max_child,
        all_progress,
        True,
        local_bound,
        True,
        reason,
    )
