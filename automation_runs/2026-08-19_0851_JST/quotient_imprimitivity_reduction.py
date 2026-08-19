from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from permutation_group_schreier import identity, schreier_stabilizer_chain
from giant_block_action_certificates import _block_action
from local_fullness_certificates import exact_string_stabilizer
from canonical_block_system import canonical_minimal_block_system


@dataclass(frozen=True)
class QuotientImprimitivityReduction:
    status: str
    quotient_size: int
    quotient_group_order: int
    block_size: int
    block_count: int
    block_system: Tuple[Tuple[int, ...], ...]
    alternative_minimal_system_count: int
    search_nodes: int
    reason: str


def reduce_quotient_imprimitivity(group, blocks, values, *, max_nodes=500000) -> QuotientImprimitivityReduction:
    """Find canonical imprimitive structure in the exact string-automorphism quotient.

    The exact global string stabilizer is projected to the supplied invariant block
    domain. rev130 then classifies that quotient action. Intransitive point orbits
    and a unique minimum nontrivial block system are canonical reductions. If the
    quotient is primitive or has several equally minimal systems, the routine
    preserves that obstruction rather than choosing a numerically favored system.
    """
    blocks = tuple(tuple(b) for b in blocks)
    m = len(blocks)
    if m < 1:
        raise ValueError("at least one quotient block is required")

    intersection = exact_string_stabilizer(group, values, max_nodes=max_nodes)
    if intersection.status == "undetermined_node_limit":
        return QuotientImprimitivityReduction(
            "undetermined_search_limit", m, 0, 0, 0, (), 0,
            intersection.search_nodes,
            "exact string-stabilizer search exceeded max_nodes",
        )
    if intersection.status == "empty_intersection":
        raise AssertionError("identity must stabilize every string")

    aut = intersection.coset.subgroup
    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    eq = identity(m)
    quotient_gens = [
        _block_action(g, blocks, point_to_block)
        for g in (aut.original_generators or (identity(group.degree),))
    ]
    quotient = schreier_stabilizer_chain(quotient_gens or [eq])
    cert = canonical_minimal_block_system(quotient)

    if cert.status == "canonical_intransitive_orbit_partition":
        partition = cert.selected_block_system
        return QuotientImprimitivityReduction(
            "canonical_intransitive_quotient_split", m, quotient.order,
            max(map(len, partition), default=0), len(partition), partition, 1,
            intersection.search_nodes,
            "exact quotient point orbits give a canonical invariant partition",
        )
    if cert.status == "unique_canonical_minimal_block_system":
        partition = cert.selected_block_system
        return QuotientImprimitivityReduction(
            "unique_canonical_imprimitive_quotient", m, quotient.order,
            cert.minimum_block_size, len(partition), partition, 1,
            intersection.search_nodes,
            "exact quotient action has one canonical minimum-size nontrivial block system",
        )
    if cert.status == "multiple_canonical_minimal_block_systems":
        return QuotientImprimitivityReduction(
            "multiple_minimal_quotient_block_systems", m, quotient.order,
            cert.minimum_block_size, 0, (), len(cert.block_systems),
            intersection.search_nodes,
            "several equally minimal canonical block systems exist; their family must be reduced without label-based selection",
        )
    return QuotientImprimitivityReduction(
        "primitive_quotient_action", m, quotient.order, m, 1, (), 0,
        intersection.search_nodes,
        "exact quotient action has no nontrivial block system",
    )
