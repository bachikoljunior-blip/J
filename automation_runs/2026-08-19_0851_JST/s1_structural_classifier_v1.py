from __future__ import annotations

from dataclasses import dataclass
from math import log2
from typing import Tuple

from canonical_block_system import canonical_minimal_block_system
from giant_block_action_certificates import analyze_giant_block_action


@dataclass(frozen=True)
class S1StructuralClassification:
    status: str
    degree: int
    canonical: bool
    group_orbits: Tuple[Tuple[int, ...], ...]
    block_system: Tuple[Tuple[int, ...], ...]
    block_system_family: Tuple[Tuple[Tuple[int, ...], ...], ...]
    quotient_degree: int
    block_size: int
    giant_type: str | None
    child_measures: Tuple[int, ...]
    reason: str


def classify_s1_structure(
    group,
    *,
    root_n: int,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
) -> S1StructuralClassification:
    """Canonical fail-closed structural dispatch for a nonterminal S1 child.

    This routine performs no String-Isomorphism search.  It only reads exact
    group structure already represented by the Schreier chain and returns the
    next structural operator class.  In particular it never calls the legacy
    node-capped exact SI terminal.

    The order is deliberate: a child that is both mathematically inside the
    polylog auxiliary window and inside the explicit implementation cap is sent
    to T1.  Otherwise the canonical block-system certificate separates
    intransitive, imprimitive and primitive cases.  Primitive giant actions are
    distinguished from primitive non-giants using the existing exact giant-image
    certificate; theorem-window gating remains the responsibility of the later
    giant/local-certificates S1 operator.
    """
    n = group.degree
    if n <= 0 or root_n < n:
        raise ValueError("root_n must dominate a positive child degree")
    if polylog_power < 1 or max_explicit_degree < 1:
        raise ValueError("invalid structural classifier parameters")

    threshold = max(1.0, log2(max(2, root_n)) ** polylog_power)
    if n <= threshold + 1e-12 and n <= max_explicit_degree:
        return S1StructuralClassification(
            "t1_small_terminal", n, True, (), (), (), 0, n, None, (),
            "child lies inside both the polylogarithmic auxiliary window and the explicit full-S_m terminal cap",
        )

    blocks = canonical_minimal_block_system(group)
    if blocks.status == "canonical_intransitive_orbit_partition":
        measures = tuple(sorted((len(O) for O in blocks.group_orbits), reverse=True))
        if not measures or max(measures) >= n:
            raise AssertionError("intransitive certificate failed strict child-domain reduction")
        return S1StructuralClassification(
            "canonical_intransitive_partition", n, True,
            blocks.group_orbits, blocks.selected_block_system, (),
            len(blocks.group_orbits), max(measures), None, measures,
            "point orbits give a canonical disjoint S1 decomposition with every child strictly smaller than the parent",
        )

    if blocks.status == "unique_canonical_minimal_block_system":
        system = blocks.selected_block_system
        q = len(system)
        b = len(system[0]) if system else 0
        if not (1 < q < n and 1 < b < n and q * b == n):
            raise AssertionError("canonical imprimitive certificate has invalid block dimensions")
        return S1StructuralClassification(
            "canonical_imprimitive_block_system", n, True,
            blocks.group_orbits, system, blocks.block_systems,
            q, b, None, (q, b),
            "unique minimum nontrivial invariant block system supplies canonical quotient/kernel structural recursion dimensions",
        )

    if blocks.status == "multiple_canonical_minimal_block_systems":
        minimum = blocks.block_systems
        b = blocks.minimum_block_size
        q = n // b if b else 0
        return S1StructuralClassification(
            "canonical_imprimitive_family", n, True,
            blocks.group_orbits, (), minimum, q, b, None,
            tuple(sorted({q, b}, reverse=True)),
            "multiple equally minimum block systems form a canonical family; choosing one by point labels is forbidden and a family-aware S1 operator is required",
        )

    if blocks.status != "primitive_or_trivial":
        return S1StructuralClassification(
            "undetermined_block_certificate", n, False,
            blocks.group_orbits, (), (), 0, 0, None, (),
            "unexpected canonical block-system status; fail closed",
        )

    singleton_blocks = tuple((i,) for i in range(n))
    giant = analyze_giant_block_action(group, singleton_blocks)
    if giant.giant_type is not None:
        return S1StructuralClassification(
            "primitive_giant_local_certificates", n, True,
            blocks.group_orbits, (), (), n, 1, giant.giant_type,
            (),
            "primitive action has an exact A_n/S_n giant image and must continue through the theorem-gated local-certificates/growing-beard S1 operator",
        )
    return S1StructuralClassification(
        "primitive_non_giant", n, True,
        blocks.group_orbits, (), (), n, 1, None, (),
        "primitive action is not a giant; S1 must continue through the canonical primitive non-giant/Split-Johnson-special-terminal path rather than generic exact SI",
    )
