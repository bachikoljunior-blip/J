from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from coset_stabilizer_primitives import RightCoset
from giant_block_action_certificates import analyze_giant_block_action
from permutation_group_schreier import StabilizerChain, identity
from quotient_factored_partial_string_intersection_v1 import (
    QuotientFactoredPartialStringIntersection,
    quotient_factored_partial_string_intersection,
)


@dataclass(frozen=True)
class AffectedSegmentAutomorphismV2:
    status: str
    subgroup: Optional[StabilizerChain]
    execution: QuotientFactoredPartialStringIntersection
    exact: bool
    recurrence_child_bound_verified: bool
    reason: str


def _generator_preserves_segment(g, values, active):
    A = set(active)
    return {g[x] for x in A} == A and all(values[g[x]] == values[x] for x in A)


def affected_segment_automorphism_group_v2(
    group: StabilizerChain,
    quotient_blocks,
    values,
    active_points,
    *,
    max_quotient_leaves=2000000,
    max_child_nodes=200000,
    giant_certificate=None,
    max_quotient_schreier_work=None,
    max_reassembly_schreier_work=None,
) -> AffectedSegmentAutomorphismV2:
    """Exact segment automorphism group from the same double recursion we account.

    If every current generator already preserves the active segment, subgroup
    closure proves immediately that the entire group does; no quotient branching
    is executed.  Otherwise rev161's quotient-factored executor computes the
    intersection as an exact right coset.  Because the identity must belong to a
    group/segment-stabilizer intersection, that coset necessarily equals its
    subgroup.  Both paths therefore expose the exact subgroup used by the
    growing-beard iteration without manufacturing complexity evidence.
    """
    vals = tuple(values)
    active = tuple(sorted(set(int(x) for x in active_points)))
    gens = group.original_generators or (identity(group.degree),)
    if all(_generator_preserves_segment(g, vals, active) for g in gens):
        giant = giant_certificate if giant_certificate is not None else analyze_giant_block_action(group, quotient_blocks)
        t = len(tuple(quotient_blocks))
        bound = (giant.largest_group_orbit + t - 1) // t if t else 0
        execution = QuotientFactoredPartialStringIntersection(
            "segment_already_invariant",
            RightCoset(group, identity(group.degree)),
            t,
            giant.image_order,
            0,
            0,
            0,
            0,
            bound,
            True,
            (),
            "every source-group generator preserves the active segment, so subgroup closure proves the whole group does without recursive SI calls",
        )
        return AffectedSegmentAutomorphismV2(
            "exact_affected_segment_automorphism_group",
            group,
            execution,
            True,
            True,
            "the active segment was already invariant under every source-group generator",
        )

    execution = quotient_factored_partial_string_intersection(
        group,
        quotient_blocks,
        vals,
        active,
        max_quotient_leaves=max_quotient_leaves,
        max_child_nodes=max_child_nodes,
        giant_certificate=giant_certificate,
        max_quotient_schreier_work=max_quotient_schreier_work,
        max_reassembly_schreier_work=max_reassembly_schreier_work,
    )
    if execution.status.startswith("undetermined_") or execution.status == "giant_action_required":
        return AffectedSegmentAutomorphismV2(
            execution.status, None, execution, False, False,
            "segment double recursion did not complete exactly; fail closed",
        )
    if execution.status == "empty_intersection":
        raise AssertionError("identity always preserves a string segment")
    if execution.status != "exact_quotient_factored_partial_string_intersection" or execution.coset is None:
        return AffectedSegmentAutomorphismV2(
            "undetermined_segment_execution_status", None, execution,
            False, False, "unexpected segment-execution status; fail closed",
        )

    e = identity(group.degree)
    if not execution.coset.contains(e):
        raise AssertionError("exact segment intersection omitted the identity")
    subgroup = execution.coset.subgroup
    if not subgroup.contains(execution.coset.representative):
        raise AssertionError("identity-containing right coset did not collapse to its subgroup")
    for g in subgroup.original_generators:
        if not _generator_preserves_segment(g, vals, active):
            raise AssertionError("segment automorphism generator violates the active string segment")

    return AffectedSegmentAutomorphismV2(
        "exact_affected_segment_automorphism_group",
        subgroup,
        execution,
        True,
        execution.recurrence_child_bound_verified,
        "exact segment subgroup is the identity-containing result of the quotient/kernel child execution tree",
    )
