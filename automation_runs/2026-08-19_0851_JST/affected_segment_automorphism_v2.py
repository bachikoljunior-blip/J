from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

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


def affected_segment_automorphism_group_v2(
    group: StabilizerChain,
    quotient_blocks,
    values,
    active_points,
    *,
    max_quotient_leaves=2000000,
    max_child_nodes=200000,
) -> AffectedSegmentAutomorphismV2:
    """Exact segment automorphism group from the same double recursion we account.

    The intersection of a group with a string-segment stabilizer is itself a
    subgroup.  rev161's quotient-factored executor computes that intersection as
    an exact right coset.  Because the identity must belong to the result, the
    returned coset necessarily equals its subgroup; this wrapper checks that fact
    explicitly and exposes the subgroup used by the growing-beard iteration.
    """
    vals = tuple(values)
    active = tuple(sorted(set(int(x) for x in active_points)))
    execution = quotient_factored_partial_string_intersection(
        group,
        quotient_blocks,
        vals,
        active,
        max_quotient_leaves=max_quotient_leaves,
        max_child_nodes=max_child_nodes,
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
    A = set(active)
    for g in subgroup.original_generators:
        if {g[x] for x in A} != A:
            raise AssertionError("segment automorphism generator moved the active set")
        if any(vals[g[x]] != vals[x] for x in A):
            raise AssertionError("segment automorphism generator changed an active value")

    return AffectedSegmentAutomorphismV2(
        "exact_affected_segment_automorphism_group",
        subgroup,
        execution,
        True,
        execution.recurrence_child_bound_verified,
        "exact segment subgroup is the identity-containing result of the quotient/kernel child execution tree",
    )
