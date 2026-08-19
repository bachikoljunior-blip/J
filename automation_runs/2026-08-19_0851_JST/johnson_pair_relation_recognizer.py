from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Optional

import numpy as np

from coset_stabilizer_primitives import RightCoset
from exact_gi_isomorphism_coset import exact_gi_isomorphism_coset


@dataclass(frozen=True)
class JohnsonRelationCertificate:
    status: str
    relation_weight: Optional[int]
    ground_size: Optional[int]
    subset_size: Optional[int]
    isomorphism_coset: Optional[RightCoset]
    isomorphism_count: int
    search_nodes: int
    reason: str


def _parameter_candidates(vertex_count: int):
    out = []
    for v in range(4, vertex_count + 1):
        for k in range(2, v // 2 + 1):
            if comb(v, k) == vertex_count:
                out.append((v, k))
    return tuple(out)


def _johnson_graph(v: int, k: int):
    vertices = list(combinations(range(v), k))
    n = len(vertices)
    adjacency = np.zeros((n, n), dtype=np.uint8)
    sets = [set(x) for x in vertices]
    for i in range(n):
        for j in range(i + 1, n):
            if len(sets[i] & sets[j]) == k - 1:
                adjacency[i, j] = adjacency[j, i] = 1
    return adjacency, np.zeros((n, 1), dtype=float)


def recognize_johnson_pair_relation(
    quotient_size: int,
    pair_weights,
    *,
    max_nodes_per_candidate: int = 500000,
) -> JohnsonRelationCertificate:
    """Recognize an exact Johnson graph among canonical pair-weight colors.

    Every distinct pair weight is interpreted as one simple graph relation on the
    quotient points. Feasible J(v,k) parameters are derived from the exact vertex
    count and degree before invoking rev111's exact GI isomorphism-coset
    certificate against a generated Johnson graph. Search limits fail closed.

    Finding one color relation is enough to expose a Johnson structure already
    canonically embedded by the pair-weight relation. A negative result is called
    certified only when every feasible exact GI comparison returned
    non-isomorphic rather than hitting its resource bound.
    """
    m = int(quotient_size)
    if m < 2:
        raise ValueError("quotient_size must be at least 2")
    if max_nodes_per_candidate < 1:
        raise ValueError("max_nodes_per_candidate must be positive")

    pairs = {tuple(map(int, p)): int(w) for p, w in pair_weights}
    expected = {(u, v) for u, v in combinations(range(m), 2)}
    if set(pairs) != expected:
        raise ValueError("pair_weights must contain each unordered quotient pair exactly once")

    candidates = _parameter_candidates(m)
    if not candidates:
        return JohnsonRelationCertificate(
            "no_johnson_parameter_candidate", None, None, None, None, 0, 0,
            "quotient vertex count is not C(v,k) for any 2<=k<=v/2",
        )

    any_undetermined = False
    total_nodes = 0
    attributes = np.zeros((m, 1), dtype=float)
    for weight in sorted(set(pairs.values())):
        adjacency = np.zeros((m, m), dtype=np.uint8)
        for (u, v), value in pairs.items():
            if value == weight:
                adjacency[u, v] = adjacency[v, u] = 1
        degrees = tuple(int(x) for x in adjacency.sum(axis=1))
        if len(set(degrees)) != 1:
            continue
        degree = degrees[0]

        for v, k in candidates:
            if degree != k * (v - k):
                continue
            cert = exact_gi_isomorphism_coset(
                (adjacency, attributes),
                _johnson_graph(v, k),
                max_nodes=max_nodes_per_candidate,
            )
            total_nodes += cert.search_nodes
            if cert.status == "exact_isomorphism_coset":
                return JohnsonRelationCertificate(
                    "exact_johnson_color_relation", weight, v, k, cert.coset,
                    cert.isomorphism_count, total_nodes,
                    "one canonical pair-weight color is exactly isomorphic to J(v,k), with the complete isomorphism set represented as a coset",
                )
            if cert.status == "undetermined_search_limit":
                any_undetermined = True

    if any_undetermined:
        return JohnsonRelationCertificate(
            "undetermined_search_limit", None, None, None, None, 0, total_nodes,
            "at least one feasible Johnson comparison exceeded the exact GI search bound",
        )
    return JohnsonRelationCertificate(
        "certified_no_johnson_color_relation", None, None, None, None, 0, total_nodes,
        "every feasible pair-weight color/Johnson parameter comparison was exactly certified non-isomorphic",
    )
