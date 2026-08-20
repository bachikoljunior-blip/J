from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from colored_subset_design_branch_plan_v1 import DesignBranchPlan
from colored_subset_exact_twl_branch_plan_v1 import build_exact_twl_design_branch_plan
from uniform_neighborhood_relation_provenance_v1 import UniformNeighborhoodRelation
from uniform_relation_twin_restriction_v1 import (
    PairedUniformRelationTwinRestriction,
    certify_paired_uniform_relation_twin_restriction,
)


@dataclass(frozen=True)
class PairedUniformRelationDesignBridge:
    status: str
    relation_gate: PairedUniformRelationTwinRestriction
    branch_plan: DesignBranchPlan | None
    source_unary_partition: tuple[tuple[int, ...], ...]
    target_unary_partition: tuple[tuple[int, ...], ...]
    relation_arity: int | None
    theorem_hypotheses_certified: bool
    structural_branch_complete: bool
    exact_empty: bool
    exact: bool
    reason: str


def _relation_palette(relation: UniformNeighborhoodRelation) -> tuple[int, ...]:
    t = relation.relation_arity
    if t is None:
        return ()
    color_of = {
        tuple(subset): int(color)
        for color, subsets in relation.relation_classes
        for subset in subsets
    }
    coords = tuple(combinations(range(relation.right_size), t))
    if set(color_of) != set(coords):
        raise AssertionError("relation classes do not cover the complete t-subset ground")
    return tuple(color_of[S] for S in coords)


def _unary_partition(relation: UniformNeighborhoodRelation) -> tuple[tuple[int, ...], ...]:
    if relation.relation_arity != 1:
        raise ValueError("unary partition requested for non-unary relation")
    return tuple(
        tuple(sorted(subset[0] for subset in subsets))
        for _color, subsets in relation.relation_classes
    )


def certify_paired_uniform_relation_design_bridge(
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    alpha: float = 0.75,
    restriction_alpha: float = 0.75,
    max_subsets: int = 200000,
    max_states: int = 200000,
    max_tuple_states: int = 250000,
    max_twl_rounds: int | None = None,
    max_twl_work_units: int = 500000000,
    max_branch_pairs: int = 200000,
) -> PairedUniformRelationDesignBridge:
    """H6-R3c: compose rev202 relation provenance with exact WL/Design machinery.

    rev203 first decides the exact relation-twin boundary. A large relation-twin
    class is handled by the proper-restriction branch and is not duplicated here.
    When the symmetry-defect gate holds:

    * arity 1 is already a canonical alpha-bounded coloring, so no k-WL theorem
      is invoked;
    * arity >=2 is passed as the complete actual containment relation to the
      existing exact correlated-replacement k-WL / Design witness-family and
      complete branch-plan implementation.

    No caller boolean is trusted to assert that a coherent/Design object exists.
    The actual relation colors, theorem gate, exact symmetry gate and every
    resource/branch cap are checked mechanically. Ambient parent-group transport
    and full incidence-string intersection remain separate obligations.
    """
    gate = certify_paired_uniform_relation_twin_restriction(
        left_size,
        right_size,
        tuple(source_edges),
        tuple(target_edges),
        relation_alpha=alpha,
        restriction_alpha=restriction_alpha,
        max_subsets=max_subsets,
    )

    if gate.exact_empty:
        return PairedUniformRelationDesignBridge(
            "exact_empty_uniform_relation_design_invariant",
            gate,
            None,
            (),
            (),
            gate.provenance.source.relation_arity,
            False,
            True,
            True,
            True,
            gate.reason,
        )
    if gate.status == "certified_paired_uniform_relation_twin_restriction":
        return PairedUniformRelationDesignBridge(
            "relation_twin_restriction_available",
            gate,
            None,
            (),
            (),
            gate.provenance.source.relation_arity,
            False,
            True,
            False,
            True,
            "rev203 already supplied the canonical proper right restriction; the WL/Design branch is not applicable to this symmetry regime",
        )
    if gate.status == "explicit_johnson_transport_required":
        return PairedUniformRelationDesignBridge(
            "explicit_johnson_transport_required",
            gate,
            None,
            (),
            (),
            gate.provenance.source.relation_arity,
            False,
            False,
            False,
            True,
            gate.reason,
        )
    if gate.status != "relation_design_gate_available":
        return PairedUniformRelationDesignBridge(
            "undetermined_uniform_relation_design_bridge",
            gate,
            None,
            (),
            (),
            gate.provenance.source.relation_arity,
            False,
            False,
            False,
            False,
            "the paired exact relation did not reach the symmetry-defect Design branch",
        )

    src = gate.provenance.source
    dst = gate.provenance.target
    t = src.relation_arity
    if t is None or t != dst.relation_arity:
        raise AssertionError("paired Design-gate relation lacks a common arity")

    if t == 1:
        sp = _unary_partition(src)
        tp = _unary_partition(dst)
        if tuple(map(len, sp)) != tuple(map(len, tp)):
            return PairedUniformRelationDesignBridge(
                "exact_empty_unary_relation_partition_shape",
                gate,
                None,
                sp,
                tp,
                1,
                True,
                True,
                True,
                True,
                "paired unary relation color multiplicities must give the same ordered partition shape",
            )
        if max(map(len, sp), default=0) > alpha * int(right_size) + 1e-12:
            raise AssertionError("unary relation passed exact symmetry gate without an alpha-bounded color partition")
        return PairedUniformRelationDesignBridge(
            "certified_unary_relation_alpha_partition",
            gate,
            None,
            sp,
            tp,
            1,
            True,
            True,
            False,
            True,
            "the actual nonconstant unary containment relation is already a canonical paired alpha-bounded coloring of the right ground",
        )

    source_palette = _relation_palette(src)
    target_palette = _relation_palette(dst)
    plan = build_exact_twl_design_branch_plan(
        right_size,
        t,
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
        return PairedUniformRelationDesignBridge(
            "exact_empty_uniform_relation_design_branch_plan",
            gate,
            plan,
            (),
            (),
            t,
            theorem_gate,
            True,
            True,
            True,
            plan.reason,
        )
    if not plan.complete or plan.status != "certified_complete_design_branch_plan":
        return PairedUniformRelationDesignBridge(
            "undetermined_uniform_relation_design_branch_plan",
            gate,
            plan,
            (),
            (),
            t,
            theorem_gate,
            False,
            False,
            False,
            plan.reason,
        )
    return PairedUniformRelationDesignBridge(
        "certified_uniform_relation_design_branch_plan",
        gate,
        plan,
        (),
        (),
        t,
        theorem_gate,
        True,
        False,
        True,
        "rev202's actual paired containment relation satisfies the exact symmetry gate and the existing exact k-WL/Design implementation produced a complete paired structural branch cover",
    )
