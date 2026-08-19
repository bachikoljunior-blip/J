from __future__ import annotations
from dataclasses import dataclass
from collections import Counter
import math
import numpy as np


@dataclass(frozen=True)
class TriangleBudgetCertificate:
    minimum_common_nodes: int
    maximum_common_nodes: int
    lower_bound_disagreements: int
    per_size_bounds: tuple[tuple[int, int], ...]
    inconsistent: bool
    reason: str


def _validate_graph(graph):
    if not isinstance(graph, (tuple, list)) or len(graph) != 2:
        raise ValueError("graph must be (adjacency, attributes)")
    adj = np.asarray(graph[0], dtype=int)
    attrs = np.asarray(graph[1])
    if adj.ndim != 2 or adj.shape[0] != adj.shape[1]:
        raise ValueError("adjacency must be square")
    if attrs.ndim == 1:
        attrs = attrs[:, None]
    if attrs.ndim != 2 or len(attrs) != len(adj):
        raise ValueError("attributes must align with vertices")
    if not np.array_equal(adj, adj.T):
        raise ValueError("only undirected graphs are supported")
    if np.any(np.diag(adj) != 0):
        raise ValueError("self loops are not supported")
    if not np.all((adj == 0) | (adj == 1)):
        raise ValueError("adjacency must be binary")
    return adj.astype(np.int8, copy=False), attrs


def _row_key(row) -> tuple:
    out = []
    for x in np.asarray(row).tolist():
        if isinstance(x, list):
            out.append(tuple(x))
        else:
            out.append(x.item() if hasattr(x, "item") else x)
    return tuple(out)


def _attribute_capacity(a_attrs, b_attrs) -> int:
    ca = Counter(_row_key(r) for r in a_attrs)
    cb = Counter(_row_key(r) for r in b_attrs)
    return sum(min(ca[k], cb[k]) for k in ca.keys() | cb.keys())


def _triangle_stats(adj: np.ndarray):
    n = len(adj)
    tri_degree = np.zeros(n, dtype=int)
    total = 0
    for i in range(n):
        for j in range(i + 1, n):
            if not adj[i, j]:
                continue
            for k in range(j + 1, n):
                if adj[i, k] and adj[j, k]:
                    total += 1
                    tri_degree[i] += 1
                    tri_degree[j] += 1
                    tri_degree[k] += 1
    return int(total), tri_degree


def selected_triangle_interval(adj: np.ndarray, selected_size: int) -> tuple[int, int]:
    """Safe interval for triangle count in any induced selected_size subset."""
    adj = np.asarray(adj, dtype=int)
    n = len(adj)
    if selected_size < 0 or selected_size > n:
        raise ValueError("selected_size out of range")
    total, tri_degree = _triangle_stats(adj)
    omitted = n - selected_size
    if omitted:
        removable_upper = int(np.sort(tri_degree)[::-1][:omitted].sum())
    else:
        removable_upper = 0
    lo = max(0, total - removable_upper)
    hi = min(total, math.comb(selected_size, 3) if selected_size >= 3 else 0)
    return int(lo), int(hi)


def _interval_gap(a: tuple[int, int], b: tuple[int, int]) -> int:
    alo, ahi = a
    blo, bhi = b
    if ahi < blo:
        return blo - ahi
    if bhi < alo:
        return alo - bhi
    return 0


def infer_triangle_budget_lower_bound(graph_a, graph_b, *, max_unmatched_total: int, max_common_edge_disagreements: int | None = None) -> TriangleBudgetCertificate:
    """Lower-bound edge disagreements using a third-order motif invariant.

    For fixed common size s, one edge flip affects at most s-2 triangles.
    Unknown partial selections are handled with safe triangle-count intervals
    and the minimum certificate over all attribute-feasible common sizes.
    """
    if max_unmatched_total < 0:
        raise ValueError("max_unmatched_total must be nonnegative")
    if max_common_edge_disagreements is not None and max_common_edge_disagreements < 0:
        raise ValueError("edge budget must be nonnegative")
    a, xa = _validate_graph(graph_a)
    b, xb = _validate_graph(graph_b)
    if xa.shape[1] != xb.shape[1]:
        return TriangleBudgetCertificate(0, 0, 0, (), True, "attribute dimensions differ")
    n, m = len(a), len(b)
    kmin = max(0, math.ceil((n + m - max_unmatched_total) / 2))
    kmax = min(n, m, _attribute_capacity(xa, xb))
    if kmin > kmax:
        return TriangleBudgetCertificate(kmin, kmax, 0, (), True, "unmatched/attribute budgets admit no common size")
    per = []
    for s in range(kmin, kmax + 1):
        ia = selected_triangle_interval(a, s)
        ib = selected_triangle_interval(b, s)
        gap = _interval_gap(ia, ib)
        lb = 0 if s <= 2 or gap == 0 else math.ceil(gap / (s - 2))
        per.append((s, int(lb)))
    lb = min(v for _, v in per) if per else 0
    inconsistent = max_common_edge_disagreements is not None and lb > max_common_edge_disagreements
    reason = "triangle-motif lower bound exceeds edge-disagreement budget" if inconsistent else "safe third-order motif lower bound over every feasible common size"
    return TriangleBudgetCertificate(kmin, kmax, int(lb), tuple(per), inconsistent, reason)
