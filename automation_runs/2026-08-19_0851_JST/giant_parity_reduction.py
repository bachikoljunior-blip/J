from __future__ import annotations

from dataclasses import dataclass
from math import factorial
from typing import Optional, Tuple

from permutation_group_schreier import identity, schreier_stabilizer_chain
from coset_stabilizer_primitives import RightCoset
from giant_block_action_certificates import _block_action
from local_fullness_certificates import exact_string_stabilizer, _alternating_test_generators


@dataclass(frozen=True)
class GiantParityReduction:
    status: str
    quotient_size: int
    image_order: int
    giant_type: Optional[str]
    parity_branch_count: int
    parity_cosets: Tuple[RightCoset, ...]
    reason: str


def reduce_global_giant_to_parity_classes(
    group,
    blocks,
    values,
    *,
    max_nodes=500000,
) -> GiantParityReduction:
    """Reduce a certified full alternating/symmetric quotient to <=2 parity classes.

    Once Aut_G(values) induces S_m, quotient reorderings form one automorphism
    orbit. If it induces exactly A_m, all m! reorderings split into precisely two
    right cosets of A_m in S_m, represented by the identity and one transposition.
    A canonical-form recursion therefore needs at most a constant two parity
    classes at this quotient barrier rather than branching over m! labelings.

    This routine certifies only the quotient ambiguity reduction; lower-domain or
    block-internal relational work still has to be processed by the master
    recursion.
    """
    blocks = tuple(tuple(b) for b in blocks)
    m = len(blocks)
    if m < 5:
        raise ValueError("global giant reduction requires quotient size at least 5")

    intersection = exact_string_stabilizer(group, values, max_nodes=max_nodes)
    if intersection.status == "undetermined_node_limit":
        return GiantParityReduction(
            "undetermined_search_limit", m, 0, None, 0, (),
            "exact global string-stabilizer search exceeded max_nodes",
        )
    if intersection.status == "empty_intersection":
        raise AssertionError("identity must stabilize every string")

    aut = intersection.coset.subgroup
    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    domain_gens = aut.original_generators or (identity(group.degree),)
    image_gens = [_block_action(g, blocks, point_to_block) for g in domain_gens]
    image = schreier_stabilizer_chain(image_gens or [identity(m)])

    full_order = factorial(m)
    alt_order = full_order // 2
    giant_type = "S_m" if image.order == full_order else ("A_m" if image.order == alt_order else None)
    if giant_type is None:
        return GiantParityReduction(
            "not_global_giant", m, image.order, None, 0, (),
            "quotient automorphism image is neither A_m nor S_m",
        )

    alt_gens = _alternating_test_generators(m, tuple(range(m)))
    alternating = schreier_stabilizer_chain(alt_gens or [identity(m)])
    if alternating.order != alt_order or not all(image.contains(g) for g in alternating.original_generators):
        raise AssertionError("standard A_m certificate is not contained in the quotient image")

    if giant_type == "S_m":
        return GiantParityReduction(
            "symmetric_single_quotient_orbit", m, image.order, giant_type, 1,
            (RightCoset(image, identity(m)),),
            "quotient image is exactly S_m, so every quotient ordering is in one automorphism orbit",
        )

    odd = list(range(m))
    odd[0], odd[1] = odd[1], odd[0]
    odd = tuple(odd)
    if alternating.contains(odd):
        raise AssertionError("chosen odd representative unexpectedly lies in A_m")
    even_coset = RightCoset(alternating, identity(m))
    odd_coset = RightCoset(alternating, odd)
    return GiantParityReduction(
        "alternating_two_parity_classes", m, image.order, giant_type, 2,
        (even_coset, odd_coset),
        "quotient image is exactly A_m; S_m labelings are exactly the even and odd right cosets",
    )
