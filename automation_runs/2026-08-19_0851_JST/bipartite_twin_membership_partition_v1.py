from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Hashable, Iterable


@dataclass(frozen=True)
class BipartiteTwinMembershipPartition:
    status: str
    left_size: int
    right_size: int
    alpha: float
    twin_classes: tuple[tuple[int, ...], ...]
    vertices_with_twins: tuple[int, ...]
    twin_free_vertices: tuple[int, ...]
    color_cells: tuple[tuple[int, ...], ...]
    max_cell_size: int | None
    alpha_partition_certified: bool
    canonical: bool
    exact: bool
    reason: str


def _normalize_edges(left_size: int, right_size: int, edges: Iterable[tuple[int, int]]):
    out = set()
    for a, b in edges:
        a = int(a)
        b = int(b)
        if not 0 <= a < left_size or not 0 <= b < right_size:
            raise ValueError("bipartite edge endpoint outside the declared part")
        out.add((a, b))
    return out


def bipartite_twin_membership_alpha_partition(
    left_size: int,
    right_size: int,
    edges: Iterable[tuple[int, int]],
    *,
    alpha: float = 0.75,
    left_colors: Iterable[Hashable] | None = None,
) -> BipartiteTwinMembershipPartition:
    """Extract the label-invariant two-color partition induced by twin membership.

    Left vertices are twins exactly when they have the same existing left color
    and identical neighborhoods in the right part. The *set* of nontrivial twin
    classes is invariant under every colored bipartite isomorphism, but assigning a
    fresh color to each individual twin class would not in general be canonical:
    an isomorphism may permute whole twin classes. This routine therefore uses only
    the invariant predicate "belongs to a nontrivial twin class".

    The resulting two cells are the union of all vertices having a twin and the
    union of all singleton twin classes. When both cells are nonempty and each has
    size at most ``alpha*|V1|``, this is a genuine canonical alpha-colored
    partition and can be charged as constant-factor auxiliary shrink. Otherwise
    the exact twin structure is returned but no split progress is claimed.

    This deliberately conservative boundary avoids turning an equivariant family
    of twin blocks into a falsely labeled canonical partition.
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

    edge_set = _normalize_edges(n1, n2, edges)
    neighborhoods = [set() for _ in range(n1)]
    for a, b in edge_set:
        neighborhoods[a].add(b)

    buckets = defaultdict(list)
    for a in range(n1):
        buckets[(palette[a], tuple(sorted(neighborhoods[a])))].append(a)
    classes = tuple(sorted((tuple(xs) for xs in buckets.values()), key=lambda C: (len(C), C)))
    with_twins = tuple(sorted(x for C in classes if len(C) > 1 for x in C))
    twin_free = tuple(sorted(x for C in classes if len(C) == 1 for x in C))
    cells = tuple(cell for cell in (with_twins, twin_free) if cell)
    largest = max((len(cell) for cell in cells), default=None)
    certified = (
        len(cells) == 2
        and largest is not None
        and largest < n1
        and largest <= alpha * n1 + 1e-12
    )
    if certified:
        return BipartiteTwinMembershipPartition(
            "certified_bipartite_twin_membership_alpha_partition",
            n1,
            n2,
            float(alpha),
            classes,
            with_twins,
            twin_free,
            cells,
            largest,
            True,
            True,
            True,
            "the invariant predicate of belonging to a nontrivial left twin class yields two nonempty alpha-bounded color cells",
        )
    return BipartiteTwinMembershipPartition(
        "bipartite_twin_membership_no_alpha_partition",
        n1,
        n2,
        float(alpha),
        classes,
        with_twins,
        twin_free,
        cells,
        largest,
        False,
        True,
        True,
        "the exact twin-membership coloring is canonical, but it is trivial or has a cell larger than the requested alpha fraction",
    )
