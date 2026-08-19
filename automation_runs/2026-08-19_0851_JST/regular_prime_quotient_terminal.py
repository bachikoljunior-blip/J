from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from permutation_group_schreier import identity, schreier_stabilizer_chain
from giant_block_action_certificates import _block_action
from local_fullness_certificates import exact_string_stabilizer
from aggregate_local_certificate_relation import aggregate_fullness_relation
from regular_prime_cyclic_terminal import canonicalize_regular_prime_subset_relation


@dataclass(frozen=True)
class RegularPrimeQuotientTerminal:
    status: str
    quotient_size: int
    quotient_group_order: int
    coordinate_systems_checked: int
    canonical_code: Optional[bytes]
    progress_verified: bool
    reason: str


def regular_prime_quotient_terminal(
    group,
    blocks,
    values,
    *,
    max_nodes=500000,
    max_test_sets=200000,
    max_coordinate_systems=200000,
    max_group_elements=200000,
) -> RegularPrimeQuotientTerminal:
    """Canonicalize the exact local-certificate relation on a regular prime quotient.

    The exact string automorphism group is projected to quotient blocks.  Only a
    transitive prime-order quotient is accepted by the affine terminal.  The same
    canonical 3-subset fullness relation used by the earlier master reductions
    is then encoded in every origin/generator coordinate system and minimized.
    No arbitrary quotient point, cycle generator, or orientation is retained.
    """
    blocks = tuple(tuple(b) for b in blocks)
    m = len(blocks)
    if m < 3:
        return RegularPrimeQuotientTerminal(
            "not_applicable_small_quotient", m, 0, 0, None, False,
            "regular-prime terminal is only used on the large homogeneous branch",
        )

    intersection = exact_string_stabilizer(group, values, max_nodes=max_nodes)
    if intersection.status == "undetermined_node_limit":
        return RegularPrimeQuotientTerminal(
            "undetermined_search_limit", m, 0, 0, None, False,
            "exact global string-stabilizer search exceeded max_nodes",
        )
    if intersection.status == "empty_intersection":
        raise AssertionError("identity must stabilize every string")

    aut = intersection.coset.subgroup
    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    quotient_gens = [
        _block_action(g, blocks, point_to_block)
        for g in (aut.original_generators or (identity(group.degree),))
    ]
    quotient = schreier_stabilizer_chain(quotient_gens or [identity(m)])

    aggregate = aggregate_fullness_relation(
        group, blocks, values,
        test_size=3,
        max_test_sets=max_test_sets,
        max_nodes=max_nodes,
    )
    if aggregate.status in {"undetermined_testset_limit", "undetermined_search_limit"}:
        return RegularPrimeQuotientTerminal(
            aggregate.status, m, quotient.order, 0, None, False, aggregate.reason,
        )

    terminal = canonicalize_regular_prime_subset_relation(
        quotient,
        aggregate.relation,
        max_group_elements=max_group_elements,
        max_coordinate_systems=max_coordinate_systems,
        max_relation_entries=max_test_sets,
    )
    if terminal.status != "exact_regular_prime_cyclic_subset_terminal":
        return RegularPrimeQuotientTerminal(
            terminal.status, m, quotient.order,
            terminal.coordinate_systems_checked, None, False, terminal.reason,
        )

    return RegularPrimeQuotientTerminal(
        "exact_regular_prime_quotient_terminal",
        m,
        quotient.order,
        terminal.coordinate_systems_checked,
        terminal.canonical_code,
        True,
        "exact quotient action plus canonical local-certificate subset relation resolved by the affine regular-prime terminal",
    )
