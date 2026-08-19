from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from canonical_block_system import canonical_minimal_block_system


@dataclass(frozen=True)
class CanonicalCartesianBlockFamily:
    status: str
    degree: int
    minimum_block_size: int
    factor_count: int
    blocks_per_factor: int
    coordinate_object_count: int
    cartesian_cell_count: int
    exact_cartesian: bool
    strict_coordinate_reduction: bool
    block_system_family: Tuple[Tuple[Tuple[int, ...], ...], ...]
    reason: str


def certify_canonical_cartesian_block_family(group) -> CanonicalCartesianBlockFamily:
    """Recognize an exact Cartesian decomposition without choosing a block system.

    The upstream certificate preserves the full family of equally minimal
    G-invariant block systems.  For each point we record which block contains it
    in every family member.  The family is an exact Cartesian decomposition iff
    the product of factor block counts equals the point-domain size and these
    membership tuples are all distinct.  Because every point lies in one block
    of every partition, these two checks imply that every Cartesian coordinate
    tuple occurs exactly once.

    The boolean/property certificate is independent of the incidental ordering
    used to serialize the family or blocks: relabeling permutes factors, blocks,
    and point signatures but preserves their counts and uniqueness.  No factor
    is selected by numeric point labels.
    """
    cert = canonical_minimal_block_system(group)
    n = group.degree
    if cert.status != "multiple_canonical_minimal_block_systems":
        return CanonicalCartesianBlockFamily(
            "not_multiple_minimal_block_family",
            n,
            cert.minimum_block_size,
            0,
            0,
            0,
            0,
            False,
            False,
            (),
            "Cartesian-family recognition applies only when the canonical minimum block-system family has multiple members",
        )

    family = cert.block_systems
    t = len(family)
    if t < 2:
        raise AssertionError("multiple-family certificate contains fewer than two systems")
    block_counts = {len(system) for system in family}
    if len(block_counts) != 1:
        raise AssertionError("minimum equal-size block systems have inconsistent block counts")
    q = next(iter(block_counts))
    if q <= 1:
        raise AssertionError("nontrivial minimum block family has no quotient reduction")

    memberships = []
    for system in family:
        owner = [-1] * n
        for block_index, block in enumerate(system):
            for point in block:
                if owner[point] != -1:
                    raise AssertionError("block system contains an overlapping point")
                owner[point] = block_index
        if any(x < 0 for x in owner):
            raise AssertionError("block system does not cover the point domain")
        memberships.append(tuple(owner))

    signatures = tuple(
        tuple(membership[point] for membership in memberships)
        for point in range(n)
    )
    unique_signatures = len(set(signatures))
    cartesian_cells = q ** t
    exact = cartesian_cells == n and unique_signatures == n
    coordinate_objects = t * q
    strict = exact and coordinate_objects < n

    if exact:
        return CanonicalCartesianBlockFamily(
            "exact_canonical_cartesian_decomposition",
            n,
            cert.minimum_block_size,
            t,
            q,
            coordinate_objects,
            cartesian_cells,
            True,
            strict,
            family,
            (
                "the full canonical family is an exact Cartesian decomposition: each point has a unique factor-block tuple and every tuple occurs; "
                "the induced coordinate-block universe is strictly smaller when strict_coordinate_reduction is true"
            ),
        )

    return CanonicalCartesianBlockFamily(
        "canonical_block_family_not_cartesian",
        n,
        cert.minimum_block_size,
        t,
        q,
        coordinate_objects,
        cartesian_cells,
        False,
        False,
        family,
        (
            "the canonical minimum block family is preserved, but it is not a full Cartesian decomposition; "
            "choosing one member or pretending product coordinates would be noncanonical/incorrect"
        ),
    )
