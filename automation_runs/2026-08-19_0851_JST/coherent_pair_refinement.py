from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Tuple


@dataclass(frozen=True)
class CoherentPairRefinement:
    status: str
    quotient_size: int
    rank: int
    refinement_rounds: int
    point_colors: Tuple[int, ...]
    color_classes: Tuple[Tuple[int, ...], ...]
    largest_class: int
    significant_split: bool
    pair_color_matrix: Tuple[Tuple[int, ...], ...]
    reason: str


def coherent_refine_pair_relation(
    quotient_size: int,
    pair_weights,
    *,
    max_class_fraction: float = 0.9,
    max_rounds: int = 128,
) -> CoherentPairRefinement:
    """Compute the stable 2-WL/coherent refinement of a pair-weight relation.

    Ordered pairs start colored by diagonal versus the canonical unordered pair
    weight. Each round recolors (u,v) by its current color together with the exact
    multiset of two-step color pairs (color(u,w), color(w,v)). Stable diagonal
    colors induce a canonical point partition; if it remains homogeneous, the
    full stable pair-color matrix is retained as a coherent relational structure
    for Johnson/design recognition rather than discarded.
    """
    m = int(quotient_size)
    if m < 2:
        raise ValueError("quotient_size must be at least 2")
    if not (0 < max_class_fraction < 1):
        raise ValueError("max_class_fraction must be in (0,1)")
    if max_rounds < 1:
        raise ValueError("max_rounds must be positive")

    pairs = {tuple(map(int, p)): int(w) for p, w in pair_weights}
    expected = {(u, v) for u, v in combinations(range(m), 2)}
    if set(pairs) != expected:
        raise ValueError("pair_weights must contain each unordered pair exactly once")

    raw = []
    for u in range(m):
        row = []
        for v in range(m):
            row.append(("D",) if u == v else ("E", pairs[tuple(sorted((u, v)))]))
        raw.append(row)
    labels = {
        sig: i for i, sig in enumerate(sorted({x for row in raw for x in row}, key=repr))
    }
    colors = [[labels[x] for x in row] for row in raw]

    rounds = 0
    while True:
        signatures = []
        for u in range(m):
            row = []
            for v in range(m):
                two_step = Counter((colors[u][w], colors[w][v]) for w in range(m))
                row.append((colors[u][v], tuple(sorted(two_step.items()))))
            signatures.append(row)
        relabel = {
            sig: i for i, sig in enumerate(
                sorted({x for row in signatures for x in row}, key=repr)
            )
        }
        next_colors = [[relabel[x] for x in row] for row in signatures]
        rounds += 1
        current_rank = len({x for row in colors for x in row})
        next_rank = len(relabel)
        if next_rank < current_rank:
            raise AssertionError("2-WL refinement merged an existing pair-color class")
        if next_rank == current_rank:
            # Stability is equality of the induced partition, not equality of
            # transient integer IDs.  The signature contains the old color, so
            # every round refines the old partition; equal rank therefore proves
            # the partition is unchanged even when canonical ID compression
            # permutes its numeric labels.
            colors = next_colors
            break
        colors = next_colors
        if rounds >= max_rounds:
            return CoherentPairRefinement(
                "undetermined_round_limit", m, 0, rounds, (), (), m, False, (),
                "2-WL pair refinement did not stabilize within max_rounds",
            )

    point_colors = tuple(colors[u][u] for u in range(m))
    classes = {}
    for u, color in enumerate(point_colors):
        classes.setdefault(color, []).append(u)
    color_classes = tuple(tuple(xs) for _, xs in sorted(classes.items()))
    largest = max(map(len, color_classes), default=0)
    significant = len(color_classes) > 1 and largest <= max_class_fraction * m + 1e-12
    rank = len({x for row in colors for x in row})

    return CoherentPairRefinement(
        "certified_coherent_point_split" if significant else "stable_coherent_pair_relation",
        m,
        rank,
        rounds,
        point_colors,
        color_classes,
        largest,
        significant,
        tuple(tuple(row) for row in colors),
        "stable 2-WL ordered-pair colors with canonical diagonal fibers",
    )
