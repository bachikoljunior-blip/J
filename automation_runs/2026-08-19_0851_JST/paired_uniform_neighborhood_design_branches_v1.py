from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import log2
from typing import Hashable, Iterable

from colored_subset_exact_twl_design_v1 import (
    ExactTWLDesignOutcome,
    paired_exact_twl_design_witness_families,
)
from uniform_neighborhood_relation_descent_v1 import _canonical_rows
from uniform_neighborhood_twl_design_family_v1 import (
    close_uniform_neighborhood_relation_with_twl_family,
)


@dataclass(frozen=True)
class PairedUniformNeighborhoodDesignBranch:
    source_individualized: tuple[int, ...]
    target_individualized: tuple[int, ...]
    outcome_status: str
    point_cell_shape: tuple[int, ...]
    output_partition_shape: tuple[int, ...]
    dominant_size: int
    two_skeleton_rank: int
    constituent_shape: tuple[int, ...]


@dataclass(frozen=True)
class PairedUniformNeighborhoodDesignBranches:
    status: str
    right_size: int
    arity: int
    source_descent_status: str
    target_descent_status: str
    paired_twl_status: str | None
    minimal_individualization_length: int | None
    source_witness_count: int
    target_witness_count: int
    branch_count: int
    branch_bound: int
    branches: tuple[PairedUniformNeighborhoodDesignBranch, ...]
    source_frontier_ready: bool
    target_frontier_ready: bool
    local_log2_branch_bound: float
    exact_empty: bool
    complete: bool
    exact: bool
    reason: str


def _outcome_key(outcome: ExactTWLDesignOutcome):
    return (
        outcome.status,
        outcome.stable_signature,
        tuple(sorted(map(len, outcome.point_cells))),
        tuple(sorted(map(len, outcome.output_partition))),
        len(outcome.dominant_cell),
        outcome.two_skeleton_rank,
        tuple(sorted(map(len, outcome.constituent_components))),
    )


def pair_uniform_neighborhood_design_branches(
    right_size: int,
    arity: int,
    source_coordinates: Iterable[Iterable[int]],
    source_colors: Iterable[Hashable],
    target_coordinates: Iterable[Iterable[int]],
    target_colors: Iterable[Hashable],
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
    max_branch_pairs: int = 200000,
) -> PairedUniformNeighborhoodDesignBranches:
    """Build the paired source/target cover for rev206's exact Design family.

    One-sided canonical structural progress is not yet an isomorphism algorithm:
    source and target individualization witnesses must be paired without choosing a
    label-dependent representative.  This routine canonicalizes both complete
    right-ground relations, rejects raw color-multiplicity mismatches, runs the
    existing paired exact k-WL Design-family invariant, and then materializes the
    Cartesian product *within each equal exact witness invariant*.

    Every color-preserving relation isomorphism sends an accepted source witness to
    a target witness with the same stable k-WL outcome invariant, so the resulting
    filtered Cartesian family is a complete cover.  It may contain false-positive
    pairs; those are intentionally left for the next ambient-action transporter.
    No tuple pair is promoted to a full-string isomorphism here.
    """
    v = int(right_size)
    k = int(arity)
    if root_n is None:
        root_n = v
    root_n = int(root_n)
    if root_n < v or max_branch_pairs < 1:
        raise ValueError("root_n must dominate right_size and max_branch_pairs must be positive")

    src_rows = _canonical_rows(v, k, source_coordinates, source_colors)
    dst_rows = _canonical_rows(v, k, target_coordinates, target_colors)
    src_coords = tuple(U for U, _ in src_rows)
    dst_coords = tuple(U for U, _ in dst_rows)
    src = tuple(value for _, value in src_rows)
    dst = tuple(value for _, value in dst_rows)

    source_progress = close_uniform_neighborhood_relation_with_twl_family(
        v, k, src_coords, src,
        root_n=root_n,
        alpha=alpha,
        max_subsets=max_subsets,
        max_johnson_nodes=max_johnson_nodes,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_rounds=max_rounds,
        max_family_work_units=max_family_work_units,
        max_branch_work_units=max_branch_work_units,
    )
    target_progress = close_uniform_neighborhood_relation_with_twl_family(
        v, k, dst_coords, dst,
        root_n=root_n,
        alpha=alpha,
        max_subsets=max_subsets,
        max_johnson_nodes=max_johnson_nodes,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_rounds=max_rounds,
        max_family_work_units=max_family_work_units,
        max_branch_work_units=max_branch_work_units,
    )

    if Counter(src) != Counter(dst):
        return PairedUniformNeighborhoodDesignBranches(
            "exact_empty_uniform_neighborhood_color_multiplicity",
            v, k, source_progress.status, target_progress.status, None, None,
            0, 0, 0, 0, (), False, False, 0.0, True, True, True,
            "the complete right-ground relations have different color multiplicities, an exact isomorphism invariant",
        )

    # If both cheaper rev205 paths are decisive, no k-WL Design tuple family is needed.
    if source_progress.twl_family_status is None or target_progress.twl_family_status is None:
        compatible = (
            source_progress.twl_family_status is None
            and target_progress.twl_family_status is None
            and source_progress.base_descent_status == target_progress.base_descent_status
            and source_progress.exact
            and target_progress.exact
        )
        return PairedUniformNeighborhoodDesignBranches(
            "paired_rev205_preemption" if compatible else "undetermined_paired_preemption_mismatch",
            v, k, source_progress.status, target_progress.status, None, None,
            0, 0, 0, 0, (),
            bool(source_progress.all_witness_branches_progress),
            bool(target_progress.all_witness_branches_progress),
            0.0, False, compatible, compatible,
            (
                "both sides are handled by the same exact cheaper rev205 structural case; no Design tuple cover is introduced"
                if compatible
                else "source and target do not enter comparable rev205/TWL structural stages; fail closed rather than infer non-isomorphism from an incompletely paired pipeline"
            ),
        )

    paired = paired_exact_twl_design_witness_families(
        v,
        k,
        src,
        dst,
        alpha=alpha,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_rounds=max_rounds,
        max_work_units=max_family_work_units,
    )
    if paired.exact_empty:
        return PairedUniformNeighborhoodDesignBranches(
            paired.status,
            v, k, source_progress.status, target_progress.status, paired.status,
            None, len(paired.source.witness_outcomes), len(paired.target.witness_outcomes),
            0, 0, (), False, False,
            paired.source.local_log2_cost_bound + paired.target.local_log2_cost_bound,
            True, True, True, paired.reason,
        )
    if not paired.complete or paired.status != "certified_paired_exact_twl_design_family":
        return PairedUniformNeighborhoodDesignBranches(
            "undetermined_paired_uniform_neighborhood_twl_family",
            v, k, source_progress.status, target_progress.status, paired.status,
            None, len(paired.source.witness_outcomes), len(paired.target.witness_outcomes),
            0, 0, (), False, False,
            paired.source.local_log2_cost_bound + paired.target.local_log2_cost_bound,
            False, False, False, paired.reason,
        )

    sell = paired.source.minimal_individualization_length
    tell = paired.target.minimal_individualization_length
    if sell is None or sell != tell or sell < 0 or sell >= k:
        return PairedUniformNeighborhoodDesignBranches(
            "undetermined_paired_uniform_neighborhood_individualization_level",
            v, k, source_progress.status, target_progress.status, paired.status,
            None, len(paired.source.witness_outcomes), len(paired.target.witness_outcomes),
            0, 0, (), False, False, 0.0, False, False, False,
            "paired exact k-WL family does not expose one common valid ell<arity level",
        )
    ell = int(sell)

    target_by_key = defaultdict(list)
    for outcome in paired.target.witness_outcomes:
        target_by_key[_outcome_key(outcome)].append(outcome)

    branch_count = 0
    for outcome in paired.source.witness_outcomes:
        branch_count += len(target_by_key[_outcome_key(outcome)])
    bound = v ** (2 * ell)
    if branch_count > bound:
        raise AssertionError("paired witness cover exceeds v^(2*ell)")
    log_bound = log2(max(1, bound))
    if branch_count > max_branch_pairs:
        return PairedUniformNeighborhoodDesignBranches(
            "undetermined_paired_uniform_neighborhood_branch_cap",
            v, k, source_progress.status, target_progress.status, paired.status,
            ell, len(paired.source.witness_outcomes), len(paired.target.witness_outcomes),
            branch_count, bound, (),
            bool(source_progress.all_witness_branches_progress),
            bool(target_progress.all_witness_branches_progress),
            log_bound, False, False, False,
            "the exact invariant-filtered tuple-pair cover exceeds max_branch_pairs and is not partially materialized",
        )

    branches = []
    for source_outcome in paired.source.witness_outcomes:
        key = _outcome_key(source_outcome)
        for target_outcome in target_by_key[key]:
            branches.append(PairedUniformNeighborhoodDesignBranch(
                tuple(source_outcome.individualized),
                tuple(target_outcome.individualized),
                source_outcome.status,
                tuple(sorted(map(len, source_outcome.point_cells))),
                tuple(sorted(map(len, source_outcome.output_partition))),
                len(source_outcome.dominant_cell),
                int(source_outcome.two_skeleton_rank),
                tuple(sorted(map(len, source_outcome.constituent_components))),
            ))

    return PairedUniformNeighborhoodDesignBranches(
        "certified_paired_uniform_neighborhood_design_branch_cover",
        v, k, source_progress.status, target_progress.status, paired.status,
        ell,
        len(paired.source.witness_outcomes),
        len(paired.target.witness_outcomes),
        branch_count,
        bound,
        tuple(branches),
        bool(source_progress.all_witness_branches_progress),
        bool(target_progress.all_witness_branches_progress),
        log_bound,
        False,
        True,
        True,
        "equal exact k-WL witness invariants were paired exhaustively; every true right-relation isomorphism is covered, while ambient-action transport and full-string intersection remain the next child",
    )
