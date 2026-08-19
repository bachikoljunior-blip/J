from __future__ import annotations

from dataclasses import dataclass
from math import factorial
from typing import Optional, Tuple

from coset_stabilizer_primitives import pointwise_stabilizer_chain
from giant_block_action_certificates import _block_action, analyze_giant_block_action
from permutation_group_schreier import StabilizerChain, identity, schreier_stabilizer_chain


@dataclass(frozen=True)
class UnaffectedStabilizerReduction:
    status: str
    quotient_degree: int
    affected_points: Tuple[int, ...]
    unaffected_points: Tuple[int, ...]
    subgroup: Optional[StabilizerChain]
    subgroup_image_order: int
    subgroup_giant_type: Optional[str]
    theorem_applicable: bool
    theorem_verified: bool
    reason: str


def unaffected_stabilizer_reduction(group, blocks) -> UnaffectedStabilizerReduction:
    """Expose the exact subgroup certified by the Unaffected Stabilizers gate.

    rev114 already classifies affected/unaffected points and checks the numerical
    theorem hypothesis.  This routine materializes the pointwise stabilizer of all
    unaffected points and independently recomputes its quotient image.  It returns
    the subgroup only when the theorem hypothesis is applicable and the image is
    still A_k or S_k.  Otherwise it fails closed.

    This is structural evidence for Q1; it does not by itself justify deleting
    unaffected string constraints from a coset intersection.  A caller must still
    prove the corresponding SI composition rule.
    """
    blocks = tuple(tuple(b) for b in blocks)
    giant = analyze_giant_block_action(group, blocks)
    k = len(blocks)
    if giant.giant_type is None:
        return UnaffectedStabilizerReduction(
            "giant_action_required", k, giant.affected_points,
            giant.unaffected_points, None, 0, None, False, False,
            "designated quotient action is not S_k/A_k",
        )
    if not giant.unaffected_stabilizer_theorem_applicable:
        return UnaffectedStabilizerReduction(
            "unaffected_stabilizer_hypothesis_not_met", k,
            giant.affected_points, giant.unaffected_points, None, 0, None,
            False, giant.unaffected_stabilizer_theorem_verified,
            "rev114 numerical hypothesis for the Unaffected Stabilizers theorem is not met",
        )
    if not giant.unaffected_stabilizer_theorem_verified:
        return UnaffectedStabilizerReduction(
            "unaffected_stabilizer_unverified", k, giant.affected_points,
            giant.unaffected_points, None, 0, None, True, False,
            "rev114 exact theorem-side audit failed",
        )

    subgroup = pointwise_stabilizer_chain(group, giant.unaffected_points)
    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    gens = subgroup.original_generators or (identity(group.degree),)
    image_gens = [_block_action(g, blocks, point_to_block) for g in gens]
    image = schreier_stabilizer_chain(image_gens or [identity(k)])
    full = factorial(k)
    half = full // 2
    image_type = "S_k" if image.order == full else ("A_k" if image.order == half else None)
    if image_type is None:
        raise AssertionError("rev114 theorem verification disagrees with materialized unaffected stabilizer")

    if any(any(g[x] != x for x in giant.unaffected_points) for g in subgroup.original_generators):
        raise AssertionError("pointwise unaffected stabilizer generator moved an unaffected point")

    return UnaffectedStabilizerReduction(
        "exact_unaffected_pointwise_stabilizer_with_giant_image",
        k,
        giant.affected_points,
        giant.unaffected_points,
        subgroup,
        image.order,
        image_type,
        True,
        True,
        "pointwise stabilizer of every unaffected point was materialized exactly and independently verified to retain a giant quotient image",
    )
