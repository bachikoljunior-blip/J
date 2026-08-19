from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Hashable, Iterable


@dataclass(frozen=True)
class BipartiteSOJGate:
    status: str
    left_size: int
    right_size: int
    alpha: float
    edge_count: int
    density: float
    complemented: bool
    left_degrees: tuple[int, ...]
    right_degrees: tuple[int, ...]
    semiregular: bool
    left_twin_classes: tuple[tuple[int, ...], ...]
    right_twin_classes: tuple[tuple[int, ...], ...]
    left_largest_twin_class: int
    right_largest_twin_class: int
    left_relative_symmetry_defect: float
    right_relative_symmetry_defect: float
    part_size_gate: bool
    left_symmetry_defect_gate: bool
    theorem_input_gate: bool
    exact: bool
    reason: str


def _normalize_edges(left_size: int, right_size: int, edges: Iterable[tuple[int, int]]):
    edge_set = set()
    for a, b in edges:
        a = int(a)
        b = int(b)
        if not 0 <= a < left_size or not 0 <= b < right_size:
            raise ValueError("bipartite edge endpoint outside the declared part")
        edge_set.add((a, b))
    return edge_set


def _twin_classes(part_size, neighborhoods, colors):
    buckets = defaultdict(list)
    for x in range(part_size):
        buckets[(colors[x], tuple(sorted(neighborhoods[x])))].append(x)
    return tuple(sorted((tuple(xs) for xs in buckets.values()), key=lambda C: (len(C), C)))


def certify_bipartite_split_or_johnson_gate(
    left_size: int,
    right_size: int,
    edges: Iterable[tuple[int, int]],
    *,
    alpha: float = 0.75,
    left_colors: Iterable[Hashable] | None = None,
    right_colors: Iterable[Hashable] | None = None,
    normalize_by_complement: bool = True,
) -> BipartiteSOJGate:
    """Mechanically verify the bipartite Split-or-Johnson input hypotheses.

    This is a theorem *gate*, not the Split-or-Johnson conclusion. It mirrors the
    corrected bipartite theorem boundary used in the Babai/Helfgott exposition:
    the small part must satisfy ``|V2| < alpha*|V1|`` and the symmetry defect on
    the large part must be at least ``1-alpha``. In a colored bipartite graph,
    twins are exactly same-colored vertices with identical neighborhoods, so the
    defect is computed exactly from explicit twin classes.

    When requested, the edge set is replaced by its bipartite complement if the
    density exceeds 1/2. Complementing preserves color-preserving isomorphisms and
    twin classes while matching the standard normalization used by the routine.
    Semiregularity is recorded independently because coherent-configuration edge
    color classes supply it in important subcases, but it is not silently treated
    as part of the general theorem hypothesis.

    No recursive progress, Johnson embedding, or quasipolynomial closure is claimed
    by this function. A caller must supply the actual corrected recursive routine
    after this gate fires.
    """
    n1 = int(left_size)
    n2 = int(right_size)
    if n1 < 2 or n2 < 1:
        raise ValueError("bipartite Split-or-Johnson requires left_size>=2 and right_size>=1")
    if not 2 / 3 <= alpha < 1.0:
        raise ValueError("alpha must lie in [2/3,1)")

    left_palette = tuple(0 for _ in range(n1)) if left_colors is None else tuple(left_colors)
    right_palette = tuple(1 for _ in range(n2)) if right_colors is None else tuple(right_colors)
    if len(left_palette) != n1 or len(right_palette) != n2:
        raise ValueError("vertex-color sequence length mismatch")

    edge_set = _normalize_edges(n1, n2, edges)
    total = n1 * n2
    complemented = False
    if normalize_by_complement and len(edge_set) > total / 2:
        edge_set = {
            (a, b)
            for a in range(n1)
            for b in range(n2)
            if (a, b) not in edge_set
        }
        complemented = True

    left_nbrs = [set() for _ in range(n1)]
    right_nbrs = [set() for _ in range(n2)]
    for a, b in edge_set:
        left_nbrs[a].add(b)
        right_nbrs[b].add(a)
    left_degrees = tuple(len(xs) for xs in left_nbrs)
    right_degrees = tuple(len(xs) for xs in right_nbrs)
    semiregular = len(set(left_degrees)) == 1 and len(set(right_degrees)) == 1

    left_twins = _twin_classes(n1, left_nbrs, left_palette)
    right_twins = _twin_classes(n2, right_nbrs, right_palette)
    left_largest = max((len(C) for C in left_twins), default=0)
    right_largest = max((len(C) for C in right_twins), default=0)
    left_defect = 1.0 - left_largest / n1
    right_defect = 1.0 - right_largest / n2
    part_gate = n2 < alpha * n1
    defect_gate = left_defect + 1e-12 >= 1.0 - alpha
    theorem_gate = part_gate and defect_gate

    status = (
        "certified_bipartite_split_or_johnson_input_gate"
        if theorem_gate
        else "bipartite_split_or_johnson_input_gate_not_met"
    )
    pieces = []
    if not part_gate:
        pieces.append("small-part inequality |V2| < alpha*|V1| is not certified")
    if not defect_gate:
        pieces.append("large-part symmetry defect is below 1-alpha")
    if theorem_gate:
        pieces.append("part-size and exact twin-defect hypotheses are certified; the theorem conclusion remains a separate recursive proof obligation")
    return BipartiteSOJGate(
        status,
        n1,
        n2,
        float(alpha),
        len(edge_set),
        len(edge_set) / total,
        complemented,
        left_degrees,
        right_degrees,
        semiregular,
        left_twins,
        right_twins,
        left_largest,
        right_largest,
        left_defect,
        right_defect,
        part_gate,
        defect_gate,
        theorem_gate,
        True,
        "; ".join(pieces),
    )
