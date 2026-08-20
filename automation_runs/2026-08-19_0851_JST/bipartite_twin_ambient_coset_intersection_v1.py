from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bipartite_twin_quotient_refinement_v1 import BipartiteTwinQuotientRefinement
from canonical_partition_transporter_v1 import canonical_partition_transporter
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import (
    compose,
    identity,
    inverse,
    schreier_stabilizer_chain,
)


@dataclass(frozen=True)
class BipartiteTwinAmbientCosetIntersection:
    status: str
    degree: int
    orbit_states: int
    source_cells: tuple[tuple[int, ...], ...]
    target_cells: tuple[tuple[int, ...], ...]
    ambient_coset: RightCoset
    candidate_coset: Optional[RightCoset]
    exact: bool
    complete: bool
    reason: str


def _shift_right(cells, left_size: int):
    return tuple(tuple(left_size + int(x) for x in cell) for cell in cells)


def _ordered_target_cells(refinement: BipartiteTwinQuotientRefinement):
    def order(source_cells, target_cells, pairing):
        if len(pairing) != len(source_cells) or len(pairing) != len(target_cells):
            raise ValueError("unique quotient pairing must cover every cell")
        by_source = {}
        targets = set()
        for si, ti in pairing:
            si, ti = int(si), int(ti)
            if not 0 <= si < len(source_cells) or not 0 <= ti < len(target_cells):
                raise ValueError("quotient pairing index outside cell range")
            if si in by_source or ti in targets:
                raise ValueError("quotient pairing must be a cell bijection")
            by_source[si] = ti
            targets.add(ti)
        if set(by_source) != set(range(len(source_cells))) or targets != set(range(len(target_cells))):
            raise ValueError("quotient pairing must cover all source and target cells")
        out = []
        for si, source in enumerate(source_cells):
            target = target_cells[by_source[si]]
            if len(source) != len(target):
                raise ValueError("paired twin cells must have equal size")
            out.append(tuple(int(x) for x in target))
        return tuple(out)

    left = order(
        refinement.source_left_cells,
        refinement.target_left_cells,
        refinement.left_cell_pairing,
    )
    right = order(
        refinement.source_right_cells,
        refinement.target_right_cells,
        refinement.right_cell_pairing,
    )
    return left, right


def _act_partition(cells, p):
    return tuple(tuple(sorted(p[x] for x in cell)) for cell in cells)


def _target_stabilizer(source_stabilizer, transporter):
    """Conjugate an exact source-partition stabilizer to the target partition."""
    e = identity(source_stabilizer.degree)
    gens = source_stabilizer.original_generators or (e,)
    # Project convention: compose(a,b) = b o a.  Ordinary t h t^-1 is therefore
    # compose(compose(inverse(t), h), t), matching rev147's established adapter.
    conjugates = [
        compose(compose(inverse(transporter), h), transporter)
        for h in gens
    ]
    return schreier_stabilizer_chain(conjugates or (e,))


def intersect_unique_twin_mapping_with_ambient_coset(
    refinement: BipartiteTwinQuotientRefinement,
    ambient_coset: RightCoset,
    *,
    max_states: int = 200000,
) -> BipartiteTwinAmbientCosetIntersection:
    """Exact ambient-coset intersection for a rev201 unique twin-cell mapping.

    Let the ambient right coset be ``H r`` in the repository convention, i.e.
    its elements are ``compose(r,h)`` for ``h in H`` (ordinary ``h o r``).
    A candidate maps the ordered source twin partition S to target T iff h maps
    ``r(S)`` to T.  This reduces the intersection to the already-proved exact
    canonical partition transporter *inside H* on singleton quotient blocks.

    If the H-orbit contains T, rev146 returns one exact transporter h0 and the
    exact stabilizer of r(S).  Conjugating that stabilizer to T gives
    ``H ∩ Stab(T)``; therefore the complete intersection is one RightCoset with
    representative ``compose(r,h0)``.  If T is outside the orbit, the
    intersection is exactly empty.  A state-budget exhaustion remains fail
    closed and is not reported as empty.

    This avoids factorial enumeration of internal twin-cell bijections and also
    subsumes an explicit intersection with rev202's unconstrained product-of-
    symmetric-groups transport family.  It is complete for the *unique ordered
    twin-cell mapping* subcase only; ambiguous rev201 quotient classes remain a
    separate corrected Split-or-Johnson child.
    """
    if max_states < 1:
        raise ValueError("max_states must be positive")
    if refinement.status != "exact_unique_twin_quotient_mapping":
        return BipartiteTwinAmbientCosetIntersection(
            "ambient_twin_intersection_refinement_not_unique",
            int(refinement.left_size + refinement.right_size),
            0,
            (),
            (),
            ambient_coset,
            None,
            bool(refinement.exact),
            False,
            "rev201 did not certify a unique ordered twin-cell map; no arbitrary quotient-cell pairing is intersected",
        )
    if not refinement.exact or not refinement.complete_for_quotient:
        raise ValueError("rev201 unique mapping must be exact and quotient-complete")

    n1 = int(refinement.left_size)
    n2 = int(refinement.right_size)
    n = n1 + n2
    if ambient_coset.subgroup.degree != n or len(ambient_coset.representative) != n:
        raise ValueError("ambient coset degree must equal left_size + right_size")

    target_left, target_right = _ordered_target_cells(refinement)
    source = tuple(tuple(int(x) for x in cell) for cell in refinement.source_left_cells) + _shift_right(
        refinement.source_right_cells, n1
    )
    target = tuple(tuple(int(x) for x in cell) for cell in target_left) + _shift_right(
        target_right, n1
    )
    if sorted(x for cell in source for x in cell) != list(range(n)):
        raise ValueError("source twin cells must partition the whole bipartite domain")
    if sorted(x for cell in target for x in cell) != list(range(n)):
        raise ValueError("target twin cells must partition the whole bipartite domain")

    r = ambient_coset.representative
    moved_source = _act_partition(source, r)
    singleton_blocks = tuple((x,) for x in range(n))
    transport = canonical_partition_transporter(
        ambient_coset.subgroup,
        singleton_blocks,
        moved_source,
        target,
        max_states=max_states,
    )
    if transport.status == "undetermined_partition_orbit_limit":
        return BipartiteTwinAmbientCosetIntersection(
            transport.status,
            n,
            transport.orbit_states,
            source,
            target,
            ambient_coset,
            None,
            False,
            False,
            "ambient subgroup partition-orbit search exceeded max_states; no empty or complete intersection claim is made",
        )
    if transport.status != "partition_transporter_coset":
        return BipartiteTwinAmbientCosetIntersection(
            "exact_empty_ambient_twin_cell_intersection",
            n,
            transport.orbit_states,
            source,
            target,
            ambient_coset,
            None,
            True,
            True,
            "the ordered target twin partition is outside the H-orbit of the ambient representative image r(S), so no element of H r can realize the rev201 mapping",
        )

    h0 = transport.transporter
    if h0 is None or transport.source_stabilizer is None:
        raise AssertionError("partition transporter success must carry transporter and source stabilizer")
    representative = compose(r, h0)
    if not ambient_coset.contains(representative):
        raise AssertionError("derived representative escaped the ambient right coset")
    if _act_partition(source, representative) != target:
        raise AssertionError("derived representative does not realize the ordered twin-cell map")

    target_stabilizer = _target_stabilizer(transport.source_stabilizer, h0)
    candidate = RightCoset(target_stabilizer, representative)
    if not candidate.contains(representative):
        raise AssertionError("candidate right coset does not contain its representative")

    # Verify all available subgroup generators stay inside the ambient coset and
    # preserve the ordered target partition. Completeness follows from the exact
    # Schreier transporter construction; these checks defend convention mistakes.
    e = identity(n)
    for g in target_stabilizer.original_generators or (e,):
        if _act_partition(target, g) != target:
            raise AssertionError("conjugated target stabilizer generator does not preserve T")
        p = compose(representative, g)
        if not candidate.contains(p) or not ambient_coset.contains(p):
            raise AssertionError("candidate generator transport escaped an exact coset")
        if _act_partition(source, p) != target:
            raise AssertionError("candidate generator transport does not preserve the ordered mapping")

    return BipartiteTwinAmbientCosetIntersection(
        "exact_complete_ambient_twin_cell_intersection",
        n,
        transport.orbit_states,
        source,
        target,
        ambient_coset,
        candidate,
        True,
        True,
        "rev201's unique twin-cell map was intersected exactly with the arbitrary ambient right coset by reducing to the existing exact H-partition transporter; the returned candidate is complete for this ordered-cell constraint",
    )
