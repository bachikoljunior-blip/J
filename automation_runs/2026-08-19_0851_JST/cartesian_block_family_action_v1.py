from __future__ import annotations

from dataclasses import dataclass

from canonical_cartesian_block_family_v1 import certify_canonical_cartesian_block_family
from permutation_group_schreier import identity, schreier_stabilizer_chain


@dataclass(frozen=True)
class CartesianBlockFamilyAction:
    status: str
    original_degree: int
    reduced_degree: int
    factor_count: int
    blocks_per_factor: int
    original_group_order: int
    image_group_order: int
    faithful: bool
    strict_domain_reduction: bool
    image: object | None
    reason: str


def exact_cartesian_block_family_action(group) -> CartesianBlockFamilyAction:
    """Build the exact action on the full canonical Cartesian block universe.

    Each minimum block system is individually G-invariant.  We take the disjoint
    union of all factor blocks as the reduced domain and project every original
    generator to its block action in each factor.  For an exact Cartesian family,
    fixing every coordinate block fixes every singleton Cartesian cell, hence the
    combined action must be faithful.  Equality of Schreier-certified group orders
    mechanically audits that kernel-triviality claim.
    """
    cert = certify_canonical_cartesian_block_family(group)
    n = group.degree
    if not cert.exact_cartesian:
        return CartesianBlockFamilyAction(
            "not_exact_cartesian_family",
            n,
            0,
            cert.factor_count,
            cert.blocks_per_factor,
            group.order,
            0,
            False,
            False,
            None,
            "a faithful Cartesian coordinate action is only available after exact full-family Cartesian certification",
        )

    family = cert.block_system_family
    t = cert.factor_count
    q = cert.blocks_per_factor
    m = t * q
    image_gens = []
    for g in (group.original_generators or (identity(n),)):
        out = list(range(m))
        for factor_index, system in enumerate(family):
            lookup = {frozenset(block): j for j, block in enumerate(system)}
            for block_index, block in enumerate(system):
                image_block = frozenset(g[u] for u in block)
                if image_block not in lookup:
                    raise AssertionError("canonical Cartesian factor is not invariant under a group generator")
                out[factor_index * q + block_index] = factor_index * q + lookup[image_block]
        image_gens.append(tuple(out))

    image = schreier_stabilizer_chain(image_gens or (identity(m),))
    faithful = image.order == group.order
    if not faithful:
        raise AssertionError("exact Cartesian cell uniqueness predicted a faithful coordinate-block action, but certified group orders disagree")

    return CartesianBlockFamilyAction(
        "exact_faithful_cartesian_coordinate_action",
        n,
        m,
        t,
        q,
        group.order,
        image.order,
        True,
        m < n,
        image,
        "the disjoint union of canonical factor blocks carries a Schreier-certified faithful image of the original group; strict_domain_reduction records whether this action domain is smaller than the point domain",
    )
