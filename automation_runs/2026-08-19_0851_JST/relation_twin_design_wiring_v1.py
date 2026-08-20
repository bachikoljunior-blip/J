from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from colored_subset_design_branch_plan_v1 import DesignBranchPlan
from colored_subset_exact_twl_branch_plan_v1 import build_exact_twl_design_branch_plan
from relation_twin_restriction_provenance_v1 import (
    PairedRelationTwinRestriction,
    RelationTwinRestriction,
    certify_paired_relation_twin_restriction,
)
from uniform_neighborhood_relation_provenance_v1 import UniformNeighborhoodRelation


@dataclass(frozen=True)
class RelationTwinDesignWiring:
    status: str
    relation_twin: PairedRelationTwinRestriction
    branch_plan: DesignBranchPlan | None
    source_unary_partition: tuple[tuple[int, ...], ...]
    target_unary_partition: tuple[tuple[int, ...], ...]
    relation_arity: int | None
    parent_provenance_verified: bool
    theorem_hypotheses_certified: bool
    structural_branch_complete: bool
    exact_empty: bool
    exact: bool
    reason: str


def _relation_palette(relation: UniformNeighborhoodRelation) -> tuple[int, ...]:
    d = relation.relation_arity
    if d is None:
        return ()
    color_of = {
        tuple(subset): int(color)
        for color, subsets in relation.relation_classes
        for subset in subsets
    }
    coords = tuple(combinations(range(relation.right_size), d))
    if set(color_of) != set(coords):
        raise ValueError("relation classes must color every distinct d-subset exactly once")
    return tuple(color_of[S] for S in coords)


def _unary_partition(relation: UniformNeighborhoodRelation) -> tuple[tuple[int, ...], ...]:
    if relation.relation_arity != 1:
        raise ValueError("unary partition requested from a non-unary relation")
    return tuple(
        tuple(sorted(S[0] for S in subsets))
        for _color, subsets in relation.relation_classes
    )


def wire_no_large_twin_relation_into_design(
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    alpha: float = 0.75,
    max_subsets: int = 200000,
    max_states: int = 200000,
    max_tuple_states: int = 250000,
    max_twl_rounds: int | None = None,
    max_twl_work_units: int = 500000000,
    max_branch_pairs: int = 200000,
) -> RelationTwinDesignWiring:
    """H6-R3c1: wire rev203 no-large-twin provenance into exact WL/Design.

    The parent relation is always re-derived from the original bipartite inputs by
    rev202/rev203.  No caller boolean may assert that a suitable relation exists.
    A unique >half relation-twin class stays on rev203's restriction branch.  Only
    the mechanically certified `relation_twin_no_large_class` case enters here.

    A nonconstant unary relation is already a paired alpha-bounded coloring because
    each color class is a relation-twin class and rev203 certified that no class is
    larger than half.  For arity >=2 the actual complete relation palettes are fed
    into the existing exact correlated-replacement k-WL / Design branch-plan code.
    """
    paired = certify_paired_relation_twin_restriction(
        left_size,
        right_size,
        tuple(source_edges),
        tuple(target_edges),
        alpha=alpha,
        max_subsets=max_subsets,
    )

    mismatch_statuses = {
        "paired_relation_twin_status_mismatch",
        "paired_relation_twin_inventory_mismatch",
        "paired_relation_twin_restriction_invariant_mismatch",
    }
    if paired.status in mismatch_statuses:
        return RelationTwinDesignWiring(
            "exact_empty_relation_twin_parent_invariant", paired, None, (), (),
            paired.source.relation.relation_arity, False, False, True, True, True,
            paired.reason,
        )
    if paired.status == "paired_relation_twin_restriction":
        return RelationTwinDesignWiring(
            "relation_twin_restriction_available", paired, None, (), (),
            paired.source.relation.relation_arity, True, False, True, False, True,
            "rev203 already certifies the complete paired proper restriction; the no-large-twin Design branch is not applicable",
        )

    src: RelationTwinRestriction = paired.source
    dst: RelationTwinRestriction = paired.target
    if src.status != "relation_twin_no_large_class" or dst.status != "relation_twin_no_large_class":
        if src.relation.status == dst.relation.status == "explicit_johnson_embedding":
            return RelationTwinDesignWiring(
                "explicit_johnson_transport_required", paired, None, (), (),
                src.relation.relation_arity, paired.provenance_verified, False,
                False, False, True,
                "rev202 produced explicit Johnson coordinates; ambient Johnson transport is the applicable next child",
            )
        return RelationTwinDesignWiring(
            "undetermined_no_large_twin_design_wiring", paired, None, (), (),
            src.relation.relation_arity, paired.provenance_verified, False,
            False, False, False,
            "the exact parent provenance did not reach the paired nonconstant no-large-relation-twin state",
        )

    relation = src.relation
    target_relation = dst.relation
    d = relation.relation_arity
    if d is None or d != target_relation.relation_arity:
        raise AssertionError("paired no-large-twin relation lacks a common arity")
    parent_verified = paired.provenance_verified and src.provenance_verified and dst.provenance_verified
    if not parent_verified:
        return RelationTwinDesignWiring(
            "undetermined_no_large_twin_parent_provenance", paired, None, (), (), d,
            False, False, False, False, False,
            "no-large-twin state was not accompanied by complete mechanical parent provenance",
        )

    if d == 1:
        sp = _unary_partition(relation)
        tp = _unary_partition(target_relation)
        if tuple(map(len, sp)) != tuple(map(len, tp)):
            return RelationTwinDesignWiring(
                "exact_empty_unary_relation_partition_shape", paired, None, sp, tp, 1,
                True, True, True, True, True,
                "a right-ground isomorphism must preserve the ordered unary relation color multiplicities",
            )
        if max(map(len, sp), default=0) * 2 > int(right_size):
            raise AssertionError("rev203 no-large-twin unary relation contains a >half color class")
        return RelationTwinDesignWiring(
            "certified_unary_relation_half_bounded_coloring", paired, None, sp, tp, 1,
            True, True, True, False, True,
            "the actual unary containment relation already gives a canonical paired coloring whose cells are all at most half of the right ground",
        )

    source_palette = _relation_palette(relation)
    target_palette = _relation_palette(target_relation)
    plan = build_exact_twl_design_branch_plan(
        right_size,
        d,
        source_palette,
        target_palette,
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
        return RelationTwinDesignWiring(
            "exact_empty_relation_design_branch_plan", paired, plan, (), (), d,
            True, theorem_gate, True, True, True, plan.reason,
        )
    if not plan.complete or plan.status != "certified_complete_design_branch_plan":
        return RelationTwinDesignWiring(
            "undetermined_relation_design_branch_plan", paired, plan, (), (), d,
            True, theorem_gate, False, False, False, plan.reason,
        )
    return RelationTwinDesignWiring(
        "certified_relation_design_branch_plan", paired, plan, (), (), d,
        True, theorem_gate, True, False, True,
        "rev203's mechanically derived no-large-twin containment relation was passed intact into exact k-WL/Design and yielded a complete paired structural branch cover",
    )
