from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Hashable, Iterable


@dataclass(frozen=True)
class ReducePart2ByColorCertificate:
    status: str
    left_size: int
    right_size: int
    alpha: float
    full_left_twin_classes: tuple[tuple[int, ...], ...]
    part0: tuple[int, ...]
    part1: tuple[int, ...]
    part0_left_twin_classes: tuple[tuple[int, ...], ...]
    part1_left_twin_classes: tuple[tuple[int, ...], ...]
    part0_relative_symmetry_defect: float
    part1_relative_symmetry_defect: float
    selected_part_index: int | None
    selected_part: tuple[int, ...]
    selected_relative_symmetry_defect: float | None
    theorem_gate_verified: bool
    exact: bool
    reason: str


def _normalize_edges(n1, n2, edges):
    out = set()
    for a, b in edges:
        a = int(a)
        b = int(b)
        if not 0 <= a < n1 or not 0 <= b < n2:
            raise ValueError("edge endpoint outside the declared bipartite parts")
        out.add((a, b))
    return out


def _left_twins(n1, edges, right_subset, left_colors):
    subset = set(right_subset)
    nbrs = [set() for _ in range(n1)]
    for a, b in edges:
        if b in subset:
            nbrs[a].add(b)
    buckets = defaultdict(list)
    for a in range(n1):
        buckets[(left_colors[a], tuple(sorted(nbrs[a])))].append(a)
    return tuple(sorted((tuple(xs) for xs in buckets.values()), key=lambda C: (len(C), C)))


def _relative_defect(n1, classes):
    largest = max((len(C) for C in classes), default=0)
    return 1.0 - largest / n1


def reduce_part2_by_color_certificate(
    left_size: int,
    right_size: int,
    edges: Iterable[tuple[int, int]],
    part0: Iterable[int],
    part1: Iterable[int],
    *,
    alpha: float = 0.75,
    left_colors: Iterable[Hashable] | None = None,
) -> ReducePart2ByColorCertificate:
    """Exact certificate for the corrected Reduce-Part2-by-Color lemma.

    The input is a colored bipartite graph X=(V1,V2;E) with no twins in V1 and
    an *ordered* partition V2=C0 dot-union C1. For each induced graph X[V1,Cj]
    we compute the exact V1 twin classes. If X is twin-free on V1 and
    ``alpha >= 2/3`` with ``|V1| >= 3``, the standard intersection argument says
    at least one induced graph has relative symmetry defect at least ``1-alpha``.

    We verify that conclusion directly instead of assuming it. If one or both
    parts pass, the lowest passing part index is selected; since the input color
    partition is ordered, this is canonical relative to that supplied partition.
    If the hypotheses are not met or neither side passes, the routine fails closed.

    This is the exact reduction subroutine only. It does not claim that a caller
    has constructed the surrounding corrected Bipartite Split-or-Johnson loop.
    """
    n1 = int(left_size)
    n2 = int(right_size)
    if n1 < 3 or n2 < 1:
        raise ValueError("Reduce-Part2-by-Color requires left_size>=3 and right_size>=1")
    if not 2 / 3 <= alpha < 1.0:
        raise ValueError("alpha must lie in [2/3,1)")
    palette = tuple(0 for _ in range(n1)) if left_colors is None else tuple(left_colors)
    if len(palette) != n1:
        raise ValueError("left-color sequence length mismatch")
    edgeset = _normalize_edges(n1, n2, edges)
    C0 = tuple(sorted(set(int(x) for x in part0)))
    C1 = tuple(sorted(set(int(x) for x in part1)))
    if any(not 0 <= x < n2 for x in C0 + C1):
        raise ValueError("right partition contains an out-of-range vertex")
    if set(C0) & set(C1) or set(C0) | set(C1) != set(range(n2)):
        raise ValueError("part0 and part1 must form a disjoint cover of the right part")

    full = _left_twins(n1, edgeset, range(n2), palette)
    twin_free = max((len(C) for C in full), default=0) <= 1
    T0 = _left_twins(n1, edgeset, C0, palette)
    T1 = _left_twins(n1, edgeset, C1, palette)
    d0 = _relative_defect(n1, T0)
    d1 = _relative_defect(n1, T1)
    threshold = 1.0 - alpha
    passing = []
    if d0 + 1e-12 >= threshold:
        passing.append((0, C0, d0))
    if d1 + 1e-12 >= threshold:
        passing.append((1, C1, d1))

    if not twin_free:
        return ReducePart2ByColorCertificate(
            "reduce_part2_requires_twin_free_left",
            n1, n2, float(alpha), full, C0, C1, T0, T1, d0, d1,
            None, (), None, False, True,
            "the full bipartite graph still has a nontrivial twin class in V1",
        )
    if not passing:
        return ReducePart2ByColorCertificate(
            "reduce_part2_lemma_invariant_violation",
            n1, n2, float(alpha), full, C0, C1, T0, T1, d0, d1,
            None, (), None, False, True,
            "twin-free hypotheses were verified but neither induced side reaches symmetry defect 1-alpha; do not continue the theorem recursion from this state",
        )

    j, selected, defect = passing[0]
    return ReducePart2ByColorCertificate(
        "certified_reduce_part2_by_color",
        n1, n2, float(alpha), full, C0, C1, T0, T1, d0, d1,
        j, selected, defect, True, True,
        "full V1 twin-freeness and the selected induced side's symmetry-defect threshold are mechanically certified",
    )
