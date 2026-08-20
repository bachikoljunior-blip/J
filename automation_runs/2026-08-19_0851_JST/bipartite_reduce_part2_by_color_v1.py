from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Hashable, Iterable


@dataclass(frozen=True)
class ReducePart2ByColorCertificate:
    """Proof-carrying local certificate for Exercise 5.5-style restriction."""

    status: str
    left_size: int
    right_size: int
    alpha: float
    full_left_twin_classes: tuple[tuple[int, ...], ...]
    part0: tuple[int, ...]
    part1: tuple[int, ...]
    part0_left_twin_classes: tuple[tuple[int, ...], ...]
    part1_left_twin_classes: tuple[tuple[int, ...], ...]
    part0_largest_left_twin_class: int
    part1_largest_left_twin_class: int
    part0_relative_symmetry_defect: float
    part1_relative_symmetry_defect: float
    part0_exercise55_gate: bool
    part1_exercise55_gate: bool
    selected_part_index: int | None
    selected_part: tuple[int, ...]
    selected_largest_left_twin_class: int | None
    selected_relative_symmetry_defect: float | None
    selected_alpha_shrink: bool
    theorem_gate_verified: bool
    exact: bool
    reason: str


def _normalize_edges(
    left_size: int,
    right_size: int,
    edges: Iterable[tuple[int, int]],
) -> set[tuple[int, int]]:
    out: set[tuple[int, int]] = set()
    for a, b in edges:
        a = int(a)
        b = int(b)
        if not 0 <= a < left_size or not 0 <= b < right_size:
            raise ValueError("edge endpoint outside the declared bipartite parts")
        out.add((a, b))
    return out


def _left_twins(
    left_size: int,
    edges: set[tuple[int, int]],
    right_subset: Iterable[int],
    left_colors: tuple[Hashable, ...],
) -> tuple[tuple[int, ...], ...]:
    subset = frozenset(right_subset)
    neighborhoods = [set() for _ in range(left_size)]
    for a, b in edges:
        if b in subset:
            neighborhoods[a].add(b)

    buckets: dict[tuple[Hashable, tuple[int, ...]], list[int]] = defaultdict(list)
    for a in range(left_size):
        buckets[(left_colors[a], tuple(sorted(neighborhoods[a])))].append(a)
    return tuple(
        sorted((tuple(vertices) for vertices in buckets.values()), key=lambda cell: (len(cell), cell))
    )


def _largest_class(classes: tuple[tuple[int, ...], ...]) -> int:
    return max((len(cell) for cell in classes), default=0)


def _relative_defect(left_size: int, largest_class: int) -> float:
    return 1.0 - largest_class / left_size


def _exercise55_gate(left_size: int, largest_class: int) -> bool:
    # Exercise 5.5 excludes a restricted twin class of size >= |V1|/2 + 1.
    # For integral class sizes this is equivalent to max_class <= ceil(|V1|/2).
    return largest_class <= (left_size + 1) // 2


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
    """Certify a theorem-faithful proper restriction of the right part.

    The input is a colored bipartite graph ``(V1,V2;E)`` whose full left side is
    required to be twin-free, together with an *ordered, proper* two-color
    partition ``V2 = C0 dot-union C1``.  Both induced left twin relations are
    computed exactly.  A side is eligible only when its largest restricted twin
    class obeys the exact integral conclusion of Exercise 5.5,
    ``max_class <= ceil(|V1|/2)``.  This is deliberately stronger than merely
    checking the caller's looser ``1-alpha`` symmetry-defect threshold.

    The smallest eligible side is selected; ties use the supplied canonical color
    order.  This choice is invariant relative to an ordered canonical partition
    and guarantees a proper right-part reduction.  ``selected_alpha_shrink`` is
    recorded separately because Exercise 5.5 alone may yield only a one-vertex
    decrease; callers that already paid a quasipolynomial branching cost must not
    silently promote this local certificate to constant-factor recurrence progress.

    This routine certifies only the local restriction step.  It does not establish
    the full Bipartite Split-or-Johnson conclusion, a Johnson embedding, ambient
    source/target canonicality, or global recurrence closure.
    """
    n1 = int(left_size)
    n2 = int(right_size)
    if n1 < 3 or n2 < 2:
        raise ValueError("right-part restriction requires left_size>=3 and right_size>=2")
    if not 2 / 3 <= alpha < 1.0:
        raise ValueError("alpha must lie in [2/3,1)")

    palette = tuple(0 for _ in range(n1)) if left_colors is None else tuple(left_colors)
    if len(palette) != n1:
        raise ValueError("left-color sequence length mismatch")

    edge_set = _normalize_edges(n1, n2, edges)
    C0 = tuple(sorted(set(int(x) for x in part0)))
    C1 = tuple(sorted(set(int(x) for x in part1)))
    if any(not 0 <= x < n2 for x in C0 + C1):
        raise ValueError("right partition contains an out-of-range vertex")
    if set(C0) & set(C1) or set(C0) | set(C1) != set(range(n2)):
        raise ValueError("part0 and part1 must form a disjoint cover of the right part")
    if not C0 or not C1:
        raise ValueError("part0 and part1 must both be nonempty for a proper restriction")

    full = _left_twins(n1, edge_set, range(n2), palette)
    full_twin_free = _largest_class(full) <= 1

    twins0 = _left_twins(n1, edge_set, C0, palette)
    twins1 = _left_twins(n1, edge_set, C1, palette)
    largest0 = _largest_class(twins0)
    largest1 = _largest_class(twins1)
    defect0 = _relative_defect(n1, largest0)
    defect1 = _relative_defect(n1, largest1)
    gate0 = _exercise55_gate(n1, largest0)
    gate1 = _exercise55_gate(n1, largest1)

    common = (
        n1,
        n2,
        float(alpha),
        full,
        C0,
        C1,
        twins0,
        twins1,
        largest0,
        largest1,
        defect0,
        defect1,
        gate0,
        gate1,
    )

    if not full_twin_free:
        return ReducePart2ByColorCertificate(
            "reduce_part2_requires_twin_free_left",
            *common,
            None,
            (),
            None,
            None,
            False,
            False,
            True,
            "the full bipartite graph has a nontrivial same-colored twin class in V1",
        )

    eligible = []
    if gate0:
        eligible.append((len(C0), 0, C0, largest0, defect0))
    if gate1:
        eligible.append((len(C1), 1, C1, largest1, defect1))
    if not eligible:
        # Exercise 5.5 proves this state cannot occur for a true twin-free full graph
        # and a proper two-part cover; fail closed rather than inventing a child.
        return ReducePart2ByColorCertificate(
            "reduce_part2_exercise55_invariant_violation",
            *common,
            None,
            (),
            None,
            None,
            False,
            False,
            True,
            "full V1 is twin-free, but neither proper restriction satisfies the exact Exercise 5.5 twin-class bound",
        )

    _, selected_index, selected, selected_largest, selected_defect = min(eligible)
    alpha_shrink = len(selected) <= alpha * n2 + 1e-12
    return ReducePart2ByColorCertificate(
        "certified_reduce_part2_by_color",
        *common,
        selected_index,
        selected,
        selected_largest,
        selected_defect,
        alpha_shrink,
        True,
        True,
        "full V1 twin-freeness, a proper ordered right partition, and the exact Exercise 5.5 restricted twin-class bound are mechanically certified",
    )
