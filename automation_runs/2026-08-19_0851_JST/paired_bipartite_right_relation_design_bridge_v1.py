from __future__ import annotations

from dataclasses import dataclass
from math import comb
from typing import Hashable, Iterable

from colored_subset_design_branch_plan_v1 import DesignBranchPlan
from colored_subset_exact_twl_branch_plan_v1 import build_exact_twl_design_branch_plan
from paired_bipartite_higher_arity_right_relation_v1 import (
    PairedHigherArityRightRelationProvenance,
    certify_paired_higher_arity_right_relation_provenance,
)


@dataclass(frozen=True)
class PairedBipartiteRightRelationDesignBridge:
    status: str
    relation_provenance: PairedHigherArityRightRelationProvenance
    branch_plan: DesignBranchPlan | None
    selected_arity: int | None
    theorem_hypotheses_certified: bool
    structural_branch_complete: bool
    exact_empty: bool
    exact: bool
    reason: str


def _relation_palette(relation):
    if relation.selected_arity is None:
        return ()
    expected = comb(len({x for subset, _ in relation.subset_signatures for x in subset}), relation.selected_arity)
    palette = tuple(signature for _subset, signature in relation.subset_signatures)
    if expected and len(palette) != expected:
        raise AssertionError("selected right relation does not contain one color for every t-subset")
    return palette


def certify_paired_bipartite_right_relation_design_bridge(
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    source_left_colors: Iterable[Hashable] | None = None,
    target_left_colors: Iterable[Hashable] | None = None,
    source_right_colors: Iterable[Hashable] | None = None,
    target_right_colors: Iterable[Hashable] | None = None,
    relation_max_arity: int | None = None,
    max_relation_subsets: int = 200000,
    alpha: float = 0.9,
    max_states: int = 200000,
    max_tuple_states: int = 250000,
    max_twl_rounds: int | None = None,
    max_twl_work_units: int = 500000000,
    max_branch_pairs: int = 200000,
) -> PairedBipartiteRightRelationDesignBridge:
    """Connect rev202's canonical right relation to the exact k-WL Design machinery.

    The bridge never trusts a caller boolean saying that a coherent/Design object
    exists. It first derives and pairs the exact right relation from bipartite
    incidence, then feeds the complete relation palettes into the already-verified
    exact correlated-replacement k-WL / Design branch-plan implementation.

    This establishes a proof-carrying structural branch cover when all theorem,
    symmetry, resource and pairing gates fire. Ambient transport and the complete
    parent bipartite/string state remain later obligations.
    """
    relation = certify_paired_higher_arity_right_relation_provenance(
        left_size,
        right_size,
        tuple(source_edges),
        tuple(target_edges),
        source_left_colors=source_left_colors,
        target_left_colors=target_left_colors,
        source_right_colors=source_right_colors,
        target_right_colors=target_right_colors,
        max_arity=relation_max_arity,
        max_relation_subsets=max_relation_subsets,
    )

    exact_mismatch = {
        "left_color_inventory_mismatch",
        "first_order_right_signature_inventory_mismatch",
        "higher_arity_relation_inventory_mismatch",
    }
    if relation.status in exact_mismatch:
        return PairedBipartiteRightRelationDesignBridge(
            "exact_empty_right_relation_invariant",
            relation,
            None,
            relation.selected_arity,
            False,
            True,
            True,
            True,
            relation.reason,
        )

    if relation.status != "paired_higher_arity_right_relation_provenance":
        return PairedBipartiteRightRelationDesignBridge(
            "undetermined_right_relation_design_bridge",
            relation,
            None,
            relation.selected_arity,
            False,
            False,
            False,
            False,
            "a paired nonconstant higher-arity right relation was not certified; no Design/coherent progress is inferred",
        )

    t = relation.selected_arity
    if t is None:
        raise AssertionError("paired higher-arity provenance lacks selected arity")
    src_palette = _relation_palette(relation.source_relation)
    dst_palette = _relation_palette(relation.target_relation)
    expected = comb(int(right_size), int(t))
    if len(src_palette) != expected or len(dst_palette) != expected:
        raise AssertionError("paired right relation palette is incomplete")

    plan = build_exact_twl_design_branch_plan(
        right_size,
        t,
        src_palette,
        dst_palette,
        alpha=alpha,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_rounds=max_twl_rounds,
        max_work_units=max_twl_work_units,
        max_branch_pairs=max_branch_pairs,
    )
    theorem_gate = bool(
        getattr(plan.source_family, "theorem_parameter_gate", False)
        and getattr(plan.source_family, "symmetry_defect_gate", False)
        and getattr(plan.target_family, "theorem_parameter_gate", False)
        and getattr(plan.target_family, "symmetry_defect_gate", False)
    )

    if plan.exact_empty:
        return PairedBipartiteRightRelationDesignBridge(
            "exact_empty_right_relation_design_branch_plan",
            relation,
            plan,
            t,
            theorem_gate,
            True,
            True,
            True,
            plan.reason,
        )
    if not plan.complete or plan.status != "certified_complete_design_branch_plan":
        return PairedBipartiteRightRelationDesignBridge(
            "undetermined_right_relation_design_branch_plan",
            relation,
            plan,
            t,
            theorem_gate,
            False,
            False,
            False,
            plan.reason,
        )

    return PairedBipartiteRightRelationDesignBridge(
        "certified_paired_right_relation_design_branch_plan",
        relation,
        plan,
        t,
        theorem_gate,
        True,
        False,
        True,
        "canonical bipartite right-relation provenance and the complete first-successful exact k-WL Design witness branch cover are both certified; ambient paired transport and full parent-state intersection remain separate obligations",
    )
