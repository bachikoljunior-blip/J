from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Hashable, Iterable


@dataclass(frozen=True)
class SymmetryDefectCertificate:
    status: str
    vertex_count: int
    arity: int
    largest_symmetric_class: int
    defect: int
    relative_defect: float
    alpha: float
    design_gate_certified: bool
    twin_classes: tuple[tuple[int, ...], ...]
    transpositions_checked: int
    relation_entries_checked: int
    reason: str


def exact_colored_subset_symmetry_defect(
    vertex_count: int,
    arity: int,
    colors: Iterable[Hashable],
    *,
    alpha: float = 0.9,
) -> SymmetryDefectCertificate:
    """Exact symmetry-defect witness for a complete colored t-subset relation.

    Two vertices are twins iff their transposition preserves every colored
    t-subset.  Twinhood is an equivalence relation: if (a b) and (b c) are
    automorphisms then their conjugate gives (a c).  A subset U is symmetric
    exactly when every transposition inside U is an automorphism, so the largest
    symmetric subset is exactly the largest twin class.  This makes the Design
    Lemma symmetry-defect hypothesis mechanically checkable without estimating
    the full automorphism group.
    """
    v = int(vertex_count)
    t = int(arity)
    if v < 1 or not 1 <= t <= v:
        raise ValueError("invalid vertex_count/arity")
    if not 0.5 <= alpha < 1.0:
        raise ValueError("alpha must lie in [1/2,1)")

    coords = tuple(combinations(range(v), t))
    palette = tuple(colors)
    if len(palette) != len(coords):
        raise ValueError("colors must contain one entry for every t-subset")
    index = {S: i for i, S in enumerate(coords)}

    parent = list(range(v))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    checked = 0
    entries = 0
    for a in range(v):
        for b in range(a + 1, v):
            checked += 1
            preserves = True
            for i, S in enumerate(coords):
                image = tuple(sorted(b if x == a else a if x == b else x for x in S))
                entries += 1
                if palette[i] != palette[index[image]]:
                    preserves = False
                    break
            if preserves:
                union(a, b)

    buckets = {}
    for x in range(v):
        buckets.setdefault(find(x), []).append(x)
    classes = tuple(sorted((tuple(xs) for xs in buckets.values()), key=lambda C: (len(C), C)))
    largest = max(map(len, classes), default=0)
    defect = v - largest
    relative = defect / v
    gate = largest <= alpha * v + 1e-12
    return SymmetryDefectCertificate(
        "exact_colored_subset_symmetry_defect",
        v,
        t,
        largest,
        defect,
        relative,
        float(alpha),
        gate,
        classes,
        checked,
        entries,
        (
            "largest twin class is the exact largest symmetric subset; "
            + ("Design-Lemma symmetry-defect hypothesis is certified" if gate else "symmetry-defect hypothesis is not certified")
        ),
    )
