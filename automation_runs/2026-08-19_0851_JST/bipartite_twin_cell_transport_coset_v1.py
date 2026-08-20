from __future__ import annotations

from dataclasses import dataclass
from math import factorial, prod

from bipartite_twin_quotient_refinement_v1 import BipartiteTwinQuotientRefinement
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import (
    Permutation,
    compose,
    identity,
    schreier_stabilizer_chain,
)


@dataclass(frozen=True)
class BipartiteTwinCellTransportCoset:
    status: str
    degree: int
    left_size: int
    right_size: int
    representative: Permutation | None
    coset: RightCoset | None
    target_cell_sizes: tuple[int, ...]
    expected_order: int
    subgroup_order: int
    exact: bool
    complete_for_cell_transport: bool
    reason: str


def _validate_partition(cells, size, name):
    flat = [int(x) for cell in cells for x in cell]
    if sorted(flat) != list(range(size)):
        raise ValueError(f"{name} cells must partition 0..{size - 1}")
    if any(not cell for cell in cells):
        raise ValueError(f"{name} cells must be nonempty")


def _transposition(n: int, a: int, b: int) -> Permutation:
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def _cell_symmetric_generators(n: int, cells):
    # Adjacent transpositions in a fixed sorted listing generate the full
    # symmetric group on each cell. Different cells have disjoint support.
    generators = []
    for raw_cell in cells:
        cell = tuple(sorted(int(x) for x in raw_cell))
        for i in range(len(cell) - 1):
            generators.append(_transposition(n, cell[i], cell[i + 1]))
    return tuple(generators)


def _representative_from_pairing(refinement: BipartiteTwinQuotientRefinement) -> Permutation:
    n1 = int(refinement.left_size)
    n2 = int(refinement.right_size)
    n = n1 + n2
    image = [-1] * n

    def install(source_cells, target_cells, pairing, offset):
        if len(pairing) != len(source_cells) or len(pairing) != len(target_cells):
            raise ValueError("unique quotient pairing must cover every source and target cell")
        seen_source = set()
        seen_target = set()
        for si, ti in pairing:
            si = int(si)
            ti = int(ti)
            if not 0 <= si < len(source_cells) or not 0 <= ti < len(target_cells):
                raise ValueError("quotient pairing index outside cell range")
            if si in seen_source or ti in seen_target:
                raise ValueError("quotient pairing must be bijective on cells")
            seen_source.add(si)
            seen_target.add(ti)
            source = tuple(sorted(int(x) for x in source_cells[si]))
            target = tuple(sorted(int(x) for x in target_cells[ti]))
            if len(source) != len(target):
                raise ValueError("paired twin cells must have equal cardinality")
            for a, b in zip(source, target):
                image[offset + a] = offset + b
        if seen_source != set(range(len(source_cells))) or seen_target != set(range(len(target_cells))):
            raise ValueError("quotient pairing must cover every cell exactly once")

    install(
        refinement.source_left_cells,
        refinement.target_left_cells,
        refinement.left_cell_pairing,
        0,
    )
    install(
        refinement.source_right_cells,
        refinement.target_right_cells,
        refinement.right_cell_pairing,
        n1,
    )
    if sorted(image) != list(range(n)):
        raise AssertionError("cell pairing failed to construct a whole-domain permutation")
    return tuple(image)


def build_bipartite_twin_cell_transport_coset(
    refinement: BipartiteTwinQuotientRefinement,
) -> BipartiteTwinCellTransportCoset:
    """Build the complete internal twin-cell transport family for rev201 success.

    Suppose rev201 has uniquely paired every exact source twin cell with a target
    twin cell and verified the quotient blocks. Inside one paired twin cell, every
    bijection is valid for the colored bipartite quotient because all vertices in
    the cell have the same color and the same opposite-side neighborhood. Hence
    the full transport family is exactly one cellwise representative followed by
    arbitrary independent permutations of every *target* twin cell.

    With this repository's permutation convention, ``RightCoset(H, r)`` contains
    precisely ``compose(r, h)`` for h in H. Thus H must stabilize the target cells:
    after r maps each source cell onto its paired target cell, h ranges over all
    internal target-cell permutations. The subgroup order is checked against the
    product of cell factorials, so this routine does not silently under-generate
    the complete family.

    This is complete only for the twin-cell transport implied by rev201. It does
    not intersect the family with an arbitrary ambient group/coset; that remains a
    separate exact child problem.
    """
    if refinement.status != "exact_unique_twin_quotient_mapping":
        return BipartiteTwinCellTransportCoset(
            status="twin_cell_transport_refinement_not_unique",
            degree=int(refinement.left_size + refinement.right_size),
            left_size=int(refinement.left_size),
            right_size=int(refinement.right_size),
            representative=None,
            coset=None,
            target_cell_sizes=(),
            expected_order=0,
            subgroup_order=0,
            exact=bool(refinement.exact),
            complete_for_cell_transport=False,
            reason=(
                "rev201 did not certify a unique quotient-cell mapping; no arbitrary "
                "cell pairing is promoted to an exact transport family"
            ),
        )
    if not refinement.exact or not refinement.complete_for_quotient:
        raise ValueError("unique quotient mapping must be exact and quotient-complete")

    n1 = int(refinement.left_size)
    n2 = int(refinement.right_size)
    n = n1 + n2
    _validate_partition(refinement.source_left_cells, n1, "source-left")
    _validate_partition(refinement.target_left_cells, n1, "target-left")
    _validate_partition(refinement.source_right_cells, n2, "source-right")
    _validate_partition(refinement.target_right_cells, n2, "target-right")

    representative = _representative_from_pairing(refinement)
    target_cells = tuple(tuple(int(x) for x in cell) for cell in refinement.target_left_cells) + tuple(
        tuple(n1 + int(x) for x in cell) for cell in refinement.target_right_cells
    )
    target_sizes = tuple(sorted(len(cell) for cell in target_cells))
    expected_order = prod(factorial(size) for size in target_sizes)
    generators = _cell_symmetric_generators(n, target_cells)
    subgroup = schreier_stabilizer_chain(generators or (identity(n),))
    if subgroup.order != expected_order:
        raise AssertionError(
            f"target-cell subgroup order mismatch: got {subgroup.order}, expected {expected_order}"
        )

    # The representative itself must be in the returned right coset; this also
    # guards the convention used by RightCoset.contains.
    coset = RightCoset(subgroup, representative)
    if not coset.contains(representative):
        raise AssertionError("RightCoset convention does not contain its representative")

    # Every subgroup generator must preserve each target cell setwise, and the
    # corresponding compose(representative, generator) must lie in the coset.
    target_cell_sets = tuple(frozenset(cell) for cell in target_cells)
    for generator in subgroup.original_generators:
        for cell in target_cell_sets:
            if frozenset(generator[x] for x in cell) != cell:
                raise AssertionError("internal target-cell generator escaped its cell")
        if not coset.contains(compose(representative, generator)):
            raise AssertionError("generated cellwise transport is missing from the right coset")

    return BipartiteTwinCellTransportCoset(
        status="exact_complete_twin_cell_transport_coset",
        degree=n,
        left_size=n1,
        right_size=n2,
        representative=representative,
        coset=coset,
        target_cell_sizes=target_sizes,
        expected_order=expected_order,
        subgroup_order=subgroup.order,
        exact=True,
        complete_for_cell_transport=True,
        reason=(
            "rev201 uniquely paired exact twin cells; a representative maps paired "
            "cells positionwise and the checked product of full symmetric groups on "
            "target cells supplies every and only internal cellwise bijection. Ambient "
            "group/coset intersection remains a separate proof obligation"
        ),
    )
