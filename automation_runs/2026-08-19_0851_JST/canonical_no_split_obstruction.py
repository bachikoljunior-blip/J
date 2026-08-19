from __future__ import annotations

from dataclasses import dataclass
from math import factorial
from typing import Optional, Tuple

from permutation_group_schreier import identity, schreier_stabilizer_chain
from giant_block_action_certificates import _block_action
from local_fullness_certificates import exact_string_stabilizer, _alternating_test_generators
from aggregate_local_certificate_relation import aggregate_fullness_relation


@dataclass(frozen=True)
class CanonicalNoSplitObstruction:
    status: str
    quotient_size: int
    full_test_count: int
    nonfull_test_count: int
    split_classes: Tuple[Tuple[int, ...], ...]
    quotient_image_order: int
    giant_type: Optional[str]
    compact_alt_generator_count: int
    compact_alt_generators_verified: bool
    reason: str


def classify_no_split_obstruction(
    group,
    blocks,
    values,
    *,
    test_size=3,
    max_test_sets=200000,
    max_nodes=500000,
    max_class_fraction=0.9,
) -> CanonicalNoSplitObstruction:
    """Turn rev116 aggregation into either a split or an exact giant obstruction.

    The split result is passed through unchanged.  In the canonical no-split
    case, if every 3-set is full then the quotient image contains all standard
    generators (0 1 c), c>=2, of A_m.  Exact stabilizer-chain membership and the
    quotient image order then certify that the image is A_m or S_m.  If the
    relation is no-split but not uniformly full, this routine deliberately
    returns an unresolved canonical nonfull relation rather than calling it a
    Johnson obstruction without structural evidence.
    """
    blocks = tuple(tuple(b) for b in blocks)
    m = len(blocks)
    if test_size != 3:
        raise ValueError("the global alternating obstruction certificate currently requires test_size=3")

    agg = aggregate_fullness_relation(
        group,
        blocks,
        values,
        test_size=test_size,
        max_test_sets=max_test_sets,
        max_nodes=max_nodes,
        max_class_fraction=max_class_fraction,
    )
    if agg.status in {"undetermined_testset_limit", "undetermined_search_limit"}:
        return CanonicalNoSplitObstruction(
            agg.status, m, agg.full_count, agg.nonfull_count, agg.color_classes,
            0, None, 0, False, agg.reason,
        )
    if agg.significant_split:
        return CanonicalNoSplitObstruction(
            "certified_significant_split", m, agg.full_count, agg.nonfull_count,
            agg.color_classes, 0, None, 0, False,
            "rev116 canonical certificate-incidence refinement produced a significant quotient split",
        )

    intersection = exact_string_stabilizer(group, values, max_nodes=max_nodes)
    if intersection.status == "undetermined_node_limit":
        return CanonicalNoSplitObstruction(
            "undetermined_search_limit", m, agg.full_count, agg.nonfull_count,
            agg.color_classes, 0, None, 0, False,
            "exact global string-stabilizer search exceeded max_nodes",
        )
    if intersection.status == "empty_intersection":
        raise AssertionError("identity must stabilize every string")

    aut = intersection.coset.subgroup
    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    domain_gens = aut.original_generators or (identity(group.degree),)
    image_gens = [_block_action(g, blocks, point_to_block) for g in domain_gens]
    image = schreier_stabilizer_chain(image_gens or [identity(m)])

    if agg.nonfull_count == 0 and m >= 5:
        compact = _alternating_test_generators(m, tuple(range(m)))
        verified = all(image.contains(q) for q in compact)
        full_order = factorial(m)
        alt_order = full_order // 2
        giant_type = "S_m" if image.order == full_order else ("A_m" if image.order == alt_order else None)
        if not verified or giant_type is None:
            raise AssertionError("uniformly full 3-set relation failed the global A_m containment/order audit")
        return CanonicalNoSplitObstruction(
            "certified_global_alternating_obstruction", m, agg.full_count, 0,
            agg.color_classes, image.order, giant_type, len(compact), True,
            "every 3-set is full; compact standard A_m generators are contained exactly and quotient order identifies A_m/S_m",
        )

    return CanonicalNoSplitObstruction(
        "canonical_nonfull_no_split", m, agg.full_count, agg.nonfull_count,
        agg.color_classes, image.order, None, 0, False,
        "certificate relation is canonically no-split but not uniformly full; a stronger relational/Johnson-style reduction is still required",
    )
