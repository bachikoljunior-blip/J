from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log2
from typing import Hashable, Iterable

from colored_subset_design_witness_v1 import (
    DesignWitnessFamily,
    find_colored_subset_design_witness_family,
)
from design_original_root_ledger_v1 import (
    DesignOriginalRootLedger,
    design_original_root_ledger,
)


@dataclass(frozen=True)
class DesignBranchPlan:
    status: str
    vertex_count: int
    arity: int
    individualization_length: int | None
    source_family: DesignWitnessFamily | None
    target_family: DesignWitnessFamily | None
    branches: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]
    branch_count: int
    local_log2_cost_bound: float
    exact_empty: bool
    complete: bool
    reason: str
    materialization_resource_envelope: object | None = None
    original_root_ledger: DesignOriginalRootLedger | None = None


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
    original_root_degree: int | None = None,
    max_partition_states: int = 200000,
    max_design_full_string_child_work: int = 10**30,
    max_design_union_reconstruction_work: int = 10**30,
    max_original_root_design_work: int = 10**60,
) -> DesignBranchPlan:
    """Build a complete source/target branch family for a Design-Lemma witness level.

    Supplying ``original_root_degree`` enables the rev242 production path: before
    the first incidence-WL execution, one original-root ledger reserves the complete
    correlated witness searches and every downstream phase through exact union
    reconstruction. A rejected ledger therefore returns fail-closed without entering
    either source or target witness search. Legacy callers that do not yet supply an
    original root retain the pre-rev242 behavior and carry no ledger downstream.
    """
    v = int(vertex_count)
    t = int(arity)
    source = tuple(source_colors)
    target = tuple(target_colors)
    if max_branch_pairs < 1:
        raise ValueError("max_branch_pairs must be positive")

    ledger = None
    if original_root_degree is not None:
        ledger = design_original_root_ledger(
            int(original_root_degree),
            v,
            t,
            max_states=max_states,
            max_wl_vertices=max_wl_vertices,
            max_wl_rounds=max_wl_rounds,
            max_branch_pairs=max_branch_pairs,
            max_partition_states=max_partition_states,
            max_design_full_string_child_work=max_design_full_string_child_work,
            max_design_union_reconstruction_work=max_design_union_reconstruction_work,
            max_work=max_original_root_design_work,
        )
        if not ledger.admitted:
            return DesignBranchPlan(
                ledger.status, v, t, None, None, None, (), 0, 0.0,
                False, False, ledger.reason,
                original_root_ledger=ledger,
            )

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

    if Counter(source) != Counter(target):
        return DesignBranchPlan(
            "exact_empty_design_relation_color_multiplicity",
            v, t, None, source_family, target_family, (), 0,
            base_bound + log2(max(2, len(source) + len(target))),
            True, True,
            "source and target complete colored t-subset relations have different color multiplicities",
            original_root_ledger=ledger,
        )

    if source_family.status != "certified_design_witness_family" or not source_family.exact:
        return DesignBranchPlan(
            "undetermined_source_design_witness_family",
            v, t, None, source_family, target_family, (), 0,
            base_bound, False, False,
            "source Design-Lemma witness family is not exact and complete",
            original_root_ledger=ledger,
        )
    if target_family.status != "certified_design_witness_family" or not target_family.exact:
        return DesignBranchPlan(
            "undetermined_target_design_witness_family",
            v, t, None, source_family, target_family, (), 0,
            base_bound, False, False,
            "target Design-Lemma witness family is not exact and complete",
            original_root_ledger=ledger,
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
            original_root_ledger=ledger,
        )

    branch_count = len(source_family.witness_tuples) * len(target_family.witness_tuples)
    branch_bound = base_bound + log2(max(1, branch_count)) + 24.0
    if branch_count > max_branch_pairs:
        return DesignBranchPlan(
            "undetermined_design_branch_pair_limit",
            v, t, sell, source_family, target_family, (), branch_count,
            branch_bound, False, False,
            "the exact Cartesian witness cover is quasipolynomially structured but exceeds the explicit branch-pair materialization cap",
            original_root_ledger=ledger,
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
        original_root_ledger=ledger,
    )
