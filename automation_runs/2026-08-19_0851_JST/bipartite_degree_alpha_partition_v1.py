from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Hashable, Iterable


@dataclass(frozen=True)
class BipartiteDegreePartition:
    status: str
    left_size: int
    right_size: int
    alpha: float
    color_cells: tuple[tuple[int, ...], ...]
    cell_signatures: tuple[tuple[Hashable, int], ...]
    max_cell_size: int
    alpha_partition_certified: bool
    dominant_cell: tuple[int, ...]
    dominant_signature: tuple[Hashable, int] | None
    dominant_degree: int | None
    dominant_twin_free: bool
    canonical: bool
    exact: bool
    reason: str


def bipartite_degree_alpha_partition(
    left_size: int,
    right_size: int,
    edges: Iterable[tuple[int, int]],
    *,
    alpha: float = 2 / 3,
    left_colors: Iterable[Hashable] | None = None,
) -> BipartiteDegreePartition:
    """Canonical first reduction by existing left color and bipartite degree.

    In the initial stage of Bipartite Split-or-Johnson, unequal left degrees already
    give a canonical colored partition. This routine isolates that mechanically safe
    part: color each left vertex by its existing color together with its exact degree.
    If every resulting cell is alpha-bounded, a canonical alpha partition is proved.

    Because alpha>=1/2, a cell larger than alpha*|V1| is unique. In that case the
    routine returns the dominant same-color/same-degree cell and additionally checks
    whether its vertices are pairwise non-twins in the full bipartite graph. A
    twin-free dominant cell is precisely the clean input needed to form the uniform
    neighborhood hypergraph used by the next theorem stage. No Johnson or recursive
    progress is claimed here beyond the certified partition itself.
    """
    n1 = int(left_size)
    n2 = int(right_size)
    if n1 < 1 or n2 < 1:
        raise ValueError("bipartite parts must be positive")
    if not 0.5 <= alpha < 1.0:
        raise ValueError("alpha must lie in [1/2,1)")
    palette = tuple(0 for _ in range(n1)) if left_colors is None else tuple(left_colors)
    if len(palette) != n1:
        raise ValueError("left-color sequence length mismatch")

    nbrs = [set() for _ in range(n1)]
    for a, b in edges:
        a = int(a)
        b = int(b)
        if not 0 <= a < n1 or not 0 <= b < n2:
            raise ValueError("bipartite edge endpoint outside the declared part")
        nbrs[a].add(b)

    buckets = defaultdict(list)
    for a in range(n1):
        buckets[(palette[a], len(nbrs[a]))].append(a)
    ordered = tuple(sorted(buckets.items(), key=lambda item: repr(item[0])))
    signatures = tuple(sig for sig, _ in ordered)
    cells = tuple(tuple(xs) for _, xs in ordered)
    largest = max(map(len, cells), default=0)
    certified = len(cells) > 1 and largest <= alpha * n1 + 1e-12
    if certified:
        return BipartiteDegreePartition(
            "certified_bipartite_degree_alpha_partition",
            n1, n2, float(alpha), cells, signatures, largest, True,
            (), None, None, False, True, True,
            "existing left color plus exact bipartite degree yields a nontrivial canonical alpha-bounded partition",
        )

    dominant_index = None
    for i, cell in enumerate(cells):
        if len(cell) > alpha * n1 + 1e-12:
            dominant_index = i
            break
    if dominant_index is None:
        return BipartiteDegreePartition(
            "bipartite_degree_partition_trivial",
            n1, n2, float(alpha), cells, signatures, largest, False,
            (), None, None, False, True, True,
            "degree coloring has no certified nontrivial alpha partition and no unique alpha-dominant cell",
        )

    dominant = cells[dominant_index]
    signature = signatures[dominant_index]
    seen = set()
    twin_free = True
    for a in dominant:
        token = tuple(sorted(nbrs[a]))
        if token in seen:
            twin_free = False
            break
        seen.add(token)
    return BipartiteDegreePartition(
        "certified_bipartite_degree_dominant_cell",
        n1, n2, float(alpha), cells, signatures, largest, False,
        dominant, signature, int(signature[1]), twin_free, True, True,
        (
            "degree coloring has a unique alpha-dominant same-color/same-degree cell; "
            + ("its full neighborhoods are pairwise distinct" if twin_free else "it still contains full-graph twins")
        ),
    )
