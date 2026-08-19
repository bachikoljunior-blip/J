from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Tuple


@dataclass(frozen=True)
class DesignCodegreeRefinement:
    status: str
    ground_size: int
    arity: int
    decisive_subset_size: int
    point_colors: Tuple[int, ...]
    color_classes: Tuple[Tuple[int, ...], ...]
    largest_class: int
    significant_split: bool
    refinement_rounds: int
    subset_signatures: Tuple[Tuple[Tuple[int, ...], Tuple[int, ...]], ...]
    reason: str


def _canonical_value_ids(values):
    unique = []
    seen = {}
    for value in values:
        try:
            if value not in seen:
                seen[value] = len(unique)
                unique.append(value)
        except TypeError as exc:
            raise ValueError("relation values must be hashable") from exc
    keyed = []
    for value in unique:
        key = (type(value).__module__, type(value).__qualname__, repr(value))
        keyed.append((key, value))
    keyed.sort(key=lambda x: x[0])
    for i in range(1, len(keyed)):
        if keyed[i - 1][0] == keyed[i][0] and keyed[i - 1][1] != keyed[i][1]:
            raise ValueError("distinct relation values have indistinguishable canonical repr keys")
    return {value: i for i, (_, value) in enumerate(keyed)}


def refine_design_codegrees(
    ground_size: int,
    colored_subsets,
    *,
    max_subset_size: int | None = None,
    max_class_fraction: float = 0.9,
    max_subsets: int = 200000,
) -> DesignCodegreeRefinement:
    """Canonical Design-Lemma-style refinement of a complete colored k-set system.

    For each s=1,...,k-1, every s-subset receives the vector of counts of each
    k-set color among its supersets. The first nonconstant s-level is converted
    into a colored point/s-subset incidence structure and refined canonically.
    This detects structure invisible to ordinary point degrees; if the point side
    still does not split significantly, the nonconstant s-subset relation is
    preserved for the next coherent/Johnson step.

    If every tested level through k-1 is constant, the routine certifies exact
    codegree homogeneity through k-1. It does not call that condition a Johnson
    scheme by itself.
    """
    v = int(ground_size)
    if v < 2:
        raise ValueError("ground_size must be at least 2")
    if not (0 < max_class_fraction < 1):
        raise ValueError("max_class_fraction must be in (0,1)")
    if max_subsets < 1:
        raise ValueError("max_subsets must be positive")

    rows = []
    for raw_S, value in colored_subsets:
        S = tuple(sorted(set(int(x) for x in raw_S)))
        if any(x < 0 or x >= v for x in S):
            raise ValueError("relation point outside ground domain")
        rows.append((S, value))
    rows = tuple(rows)
    if not rows:
        raise ValueError("colored_subsets must be nonempty")
    k = len(rows[0][0])
    if k < 2 or any(len(S) != k for S, _ in rows):
        raise ValueError("all relation rows must have the same arity k>=2")

    expected_rows = set(combinations(range(v), k))
    if {S for S, _ in rows} != expected_rows or len(rows) != len(expected_rows):
        raise ValueError("colored_subsets must contain every k-subset exactly once")

    value_ids = _canonical_value_ids(value for _, value in rows)
    row_color = {S: value_ids[value] for S, value in rows}
    color_count = len(value_ids)
    limit_s = k - 1 if max_subset_size is None else min(k - 1, int(max_subset_size))
    if limit_s < 1:
        raise ValueError("max_subset_size leaves no tested subset level")

    for s in range(1, limit_s + 1):
        total_s = comb(v, s)
        if total_s > max_subsets:
            return DesignCodegreeRefinement(
                "undetermined_subset_limit", v, k, s, (), (), v, False, 0, (),
                "number of s-subsets exceeds max_subsets",
            )
        subsets = tuple(combinations(range(v), s))
        signatures = {}
        for U in subsets:
            Uset = set(U)
            counts = [0] * color_count
            for S, color in row_color.items():
                if Uset.issubset(S):
                    counts[color] += 1
            signatures[U] = tuple(counts)

        if len(set(signatures.values())) == 1:
            continue

        initial_signature_ids = {
            sig: i for i, sig in enumerate(sorted(set(signatures.values())))
        }
        point_colors = [0] * v
        subset_colors = [initial_signature_ids[signatures[U]] for U in subsets]
        rounds = 0
        while True:
            point_sigs = []
            for u in range(v):
                incidence = Counter(
                    subset_colors[j] for j, U in enumerate(subsets) if u in U
                )
                point_sigs.append(("P", point_colors[u], tuple(sorted(incidence.items()))))

            subset_sigs = []
            for j, U in enumerate(subsets):
                incidence = Counter(point_colors[u] for u in U)
                subset_sigs.append((
                    "S", signatures[U], subset_colors[j], tuple(sorted(incidence.items()))
                ))

            all_sigs = point_sigs + subset_sigs
            labels = {sig: i for i, sig in enumerate(sorted(set(all_sigs), key=repr))}
            next_points = [labels[sig] for sig in point_sigs]
            next_subsets = [labels[sig] for sig in subset_sigs]
            rounds += 1
            if next_points == point_colors and next_subsets == subset_colors:
                break
            point_colors, subset_colors = next_points, next_subsets
            if rounds > v + len(subsets) + 2:
                raise AssertionError("design incidence refinement failed to stabilize")

        classes = {}
        for u, color in enumerate(point_colors):
            classes.setdefault(color, []).append(u)
        color_classes = tuple(tuple(xs) for _, xs in sorted(classes.items()))
        largest = max(map(len, color_classes), default=0)
        significant = len(color_classes) > 1 and largest <= max_class_fraction * v + 1e-12
        return DesignCodegreeRefinement(
            "certified_design_codegree_split" if significant else "canonical_subset_relation_no_significant_split",
            v,
            k,
            s,
            tuple(point_colors),
            color_classes,
            largest,
            significant,
            rounds,
            tuple(sorted(signatures.items())),
            "first nonconstant subset-codegree level converted into a canonical colored incidence relation",
        )

    return DesignCodegreeRefinement(
        "certified_codegree_homogeneous_through_limit",
        v,
        k,
        limit_s,
        tuple(0 for _ in range(v)),
        (tuple(range(v)),),
        v,
        False,
        0,
        (),
        "every tested s-subset codegree vector is constant; stronger design/Johnson structure is required",
    )
