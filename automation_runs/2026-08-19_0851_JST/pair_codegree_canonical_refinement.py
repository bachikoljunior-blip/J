from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Tuple


@dataclass(frozen=True)
class PairCodegreeRefinement:
    status: str
    quotient_size: int
    point_colors: Tuple[int, ...]
    color_classes: Tuple[Tuple[int, ...], ...]
    largest_class: int
    significant_split: bool
    refinement_rounds: int
    pair_weights: Tuple[Tuple[Tuple[int, int], int], ...]
    pair_weight_spectrum: Tuple[Tuple[int, int], ...]
    reason: str


def refine_pair_codegrees(
    quotient_size: int,
    relation,
    *,
    max_class_fraction: float = 0.9,
) -> PairCodegreeRefinement:
    """Refine a canonical t-uniform Boolean relation by pair codegrees.

    `relation` is an iterable of `(T, full)` rows such as rev116's aggregated
    local-certificate relation.  Each unordered quotient pair receives the exact
    number of full relation rows containing it.  A deterministic vertex
    refinement then uses the multiset of `(pair_weight, neighbor_color)` values.

    This is strictly stronger than looking only at each point's number of full
    test sets: regular hypergraph relations can have identical point degrees but
    non-isomorphic pair-codegree neighborhoods.  If vertices still do not split,
    a nonconstant pair-weight relation is preserved as a canonical edge-colored
    quotient structure for the next Johnson/coherent-configuration step.
    """
    m = int(quotient_size)
    if m < 2:
        raise ValueError("quotient_size must be at least 2")
    if not (0 < max_class_fraction < 1):
        raise ValueError("max_class_fraction must be in (0,1)")

    rows = []
    for raw_T, raw_full in relation:
        T = tuple(sorted(set(int(x) for x in raw_T)))
        if any(x < 0 or x >= m for x in T):
            raise ValueError("relation point outside quotient domain")
        rows.append((T, bool(raw_full)))
    rows = tuple(rows)

    pair_weights = {}
    for u, v in combinations(range(m), 2):
        pair_weights[(u, v)] = sum(full and u in T and v in T for T, full in rows)

    spectrum = Counter(pair_weights.values())
    point_colors = [0] * m
    rounds = 0
    while True:
        signatures = []
        for u in range(m):
            incident = Counter(
                (pair_weights[tuple(sorted((u, v)))], point_colors[v])
                for v in range(m) if v != u
            )
            signatures.append((point_colors[u], tuple(sorted(incident.items()))))
        labels = {s: i for i, s in enumerate(sorted(set(signatures), key=repr))}
        next_colors = [labels[s] for s in signatures]
        rounds += 1
        if next_colors == point_colors:
            break
        point_colors = next_colors
        if rounds > m + 2:
            raise AssertionError("pair-codegree refinement failed to stabilize")

    classes = {}
    for u, color in enumerate(point_colors):
        classes.setdefault(color, []).append(u)
    color_classes = tuple(tuple(v) for _, v in sorted(classes.items()))
    largest = max(map(len, color_classes), default=0)
    significant = len(color_classes) > 1 and largest <= max_class_fraction * m + 1e-12

    if significant:
        status = "certified_pair_codegree_split"
        reason = "pair-codegree neighborhoods canonically refine the quotient into a significant point partition"
    elif len(spectrum) > 1:
        status = "canonical_edge_colored_relation"
        reason = "points remain unsplit but nonconstant pair codegrees define a canonical edge-colored quotient relation"
    else:
        status = "pair_relation_homogeneous"
        reason = "pair codegrees are constant; higher-arity/Johnson-style structure is required"

    return PairCodegreeRefinement(
        status,
        m,
        tuple(point_colors),
        color_classes,
        largest,
        significant,
        rounds,
        tuple(sorted(pair_weights.items())),
        tuple(sorted(spectrum.items())),
        reason,
    )
