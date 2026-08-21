from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log2
from typing import Hashable, Iterable

from colored_subset_design_witness_v1 import (
    DesignWitnessFamily,
    find_colored_subset_design_witness_family,
)


@dataclass(frozen=True)
class DesignBranchPlan:
    status: str
    vertex_count: int
    arity: int
    individualization_length: int | None
    source_family: DesignWitnessFamily
    target_family: DesignWitnessFamily
    branches: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]
    branch_count: int
    local_log2_cost_bound: float
    exact_empty: bool
    complete: bool
    reason: str
    materialization_resource_envelope: object | None = None


def build_colored_subset_design_branch_plan(
    vertex_count: int,
    arity: int,
    source_colors: Iterable[Hashable],
    target_colors: Iterable[Hashable],
    *,
    alpha: float = 0.9,
    max_states: int = 200000,
    max_wl_vertices: int = 512,
    max_wl_rounds: int = 4096,
    max_branch_pairs: int = 200000,
) -> DesignBranchPlan:
    """Build a complete source/target branch family for a Design-Lemma witness level.

    The single-structure witness finder returns the *entire* first successful
    ordered-tuple level. Under every color-preserving isomorphism that family maps
    bijectively to the corresponding target family. Therefore the Cartesian product
    of the two complete families is a safe exact branching cover: every true
    isomorphism maps some source witness tuple to a target witness tuple occurring in
    the plan. No arbitrary tuple representative is selected.

    This routine does not yet compute the ambient-group transporter for each tuple
    pair. It certifies only the complete quasipolynomial branch cover and invariant
    rejection gates; the next layer must intersect each pair with the signed Johnson
    ground action and recurse on the full string.
    """
    v = int(vertex_count)
    t = int(arity)
    source = tuple(source_colors)
    target = tuple(target_colors)
    if max_branch_pairs < 1:
        raise ValueError("max_branch_pairs must be positive")

    source_family = find_colored_subset_design_witness_family(
        v, t, source,
        alpha=alpha,
        max_states=max_states,
        max_wl_vertices=max_wl_vertices,
        max_wl_rounds=max_wl_rounds,
    )
    target_family = find_colored_subset_design_witness_family(
        v, t, target,
        alpha=alpha,
        max_states=max_states,
        max_wl_vertices=max_wl_vertices,
        max_wl_rounds=max_wl_rounds,
    )

    base_bound = (
        source_family.local_log2_cost_bound
        + target_family.local_log2_cost_bound
        + 16.0
    )

    # Raw relation color multiplicities are an exact isomorphism invariant.
    if Counter(source) != Counter(target):
        return DesignBranchPlan(
            "exact_empty_design_relation_color_multiplicity",
            v, t, None, source_family, target_family, (), 0,
            base_bound + log2(max(2, len(source) + len(target))),
            True, True,
            "source and target complete colored t-subset relations have different color multiplicities",
        )

    if source_family.status != "certified_design_witness_family" or not source_family.exact:
        return DesignBranchPlan(
            "undetermined_source_design_witness_family",
            v, t, None, source_family, target_family, (), 0,
            base_bound, False, False,
            "source Design-Lemma witness family is not exact and complete",
        )
    if target_family.status != "certified_design_witness_family" or not target_family.exact:
        return DesignBranchPlan(
            "undetermined_target_design_witness_family",
            v, t, None, source_family, target_family, (), 0,
            base_bound, False, False,
            "target Design-Lemma witness family is not exact and complete",
        )

    sell = source_family.minimal_individualization_length
    tell = target_family.minimal_individualization_length
    source_kind_counts = Counter(source_family.witness_kinds)
    target_kind_counts = Counter(target_family.witness_kinds)
    if (
        sell != tell
        or len(source_family.witness_tuples) != len(target_family.witness_tuples)
        or source_kind_counts != target_kind_counts
    ):
        return DesignBranchPlan(
            "exact_empty_design_witness_family_invariant",
            v, t, None, source_family, target_family, (), 0,
            base_bound + 16.0,
            True, True,
            "minimal witness length, witness-family cardinality, or certified outcome multiplicities differ",
        )

    branch_count = len(source_family.witness_tuples) * len(target_family.witness_tuples)
    branch_bound = base_bound + log2(max(1, branch_count)) + 24.0
    if branch_count > max_branch_pairs:
        return DesignBranchPlan(
            "undetermined_design_branch_pair_limit",
            v, t, sell, source_family, target_family, (), branch_count,
            branch_bound, False, False,
            "the exact Cartesian witness cover is quasipolynomially structured but exceeds the explicit branch-pair materialization cap",
        )

    branches = tuple(
        (tuple(xs), tuple(yt))
        for xs in source_family.witness_tuples
        for yt in target_family.witness_tuples
    )
    return DesignBranchPlan(
        "certified_complete_design_branch_plan",
        v, t, sell, source_family, target_family, branches, branch_count,
        branch_bound, False, True,
        "the entire minimal source witness family is paired with the entire minimal target witness family; every true relation isomorphism is covered without selecting a label-dependent representative",
    )
