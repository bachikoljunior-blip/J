from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Dict, Iterable, Mapping, Tuple

Edge = Tuple[int, int]


@dataclass(frozen=True)
class AssignmentLowerBoundResult:
    feasible: bool
    minimum_cost: int
    matching: Tuple[Edge, ...]
    need: int


def min_cost_cardinality_matching(
    costs: Mapping[Edge, int],
    left: Iterable[int],
    right: Iterable[int],
    need: int,
    *,
    forced: Iterable[Edge] = (),
    forbidden: Iterable[Edge] = (),
) -> AssignmentLowerBoundResult:
    """Exact minimum-cost matching of a requested cardinality.

    Costs must be non-negative integers. Missing edges are unavailable. `forced`
    edges are included in the requested cardinality and must be vertex-disjoint.
    This routine is intended as a sound lower-bound primitive: when each edge
    cost counts disagreements against already-forced anchors, the returned cost
    is the least total anchor-disagreement cost any remaining assignment can
    achieve. Pairwise disagreements among non-anchor assignments are omitted,
    so the value is a lower bound on the complete disagreement objective.
    """
    left = tuple(left)
    right = tuple(right)
    forced = tuple(forced)
    forbidden = set(forbidden)
    if need < 0:
        raise ValueError("need must be non-negative")
    if any((not isinstance(c, int)) or c < 0 for c in costs.values()):
        raise ValueError("costs must be non-negative integers")

    fu = {u for u, _ in forced}
    fv = {v for _, v in forced}
    if len(fu) != len(forced) or len(fv) != len(forced):
        return AssignmentLowerBoundResult(False, math.inf, (), need)
    if len(forced) > need:
        return AssignmentLowerBoundResult(False, math.inf, (), need)

    forced_cost = 0
    for e in forced:
        if e in forbidden or e not in costs:
            return AssignmentLowerBoundResult(False, math.inf, (), need)
        forced_cost += costs[e]

    rem_need = need - len(forced)
    if rem_need == 0:
        return AssignmentLowerBoundResult(True, forced_cost, tuple(sorted(forced)), need)

    L = [u for u in left if u not in fu]
    R = [v for v in right if v not in fv]
    if rem_need > min(len(L), len(R)):
        return AssignmentLowerBoundResult(False, math.inf, (), need)

    S = ("S", -1)
    T = ("T", -1)
    LN = {u: ("L", u) for u in L}
    RN = {v: ("R", v) for v in R}
    nodes = [S, T] + list(LN.values()) + list(RN.values())
    graph: Dict[tuple, list[list]] = {n: [] for n in nodes}

    def add(a, b, cap, cost, tag=None):
        graph[a].append([b, cap, cost, len(graph[b]), tag])
        graph[b].append([a, 0, -cost, len(graph[a]) - 1, None])

    for u in L:
        add(S, LN[u], 1, 0)
    for v in R:
        add(RN[v], T, 1, 0)
    for u in L:
        for v in R:
            e = (u, v)
            if e in forbidden or e not in costs:
                continue
            add(LN[u], RN[v], 1, costs[e], e)

    potential = {n: 0 for n in nodes}
    flow = 0
    variable_cost = 0
    while flow < rem_need:
        dist = {n: math.inf for n in nodes}
        prev = {}
        dist[S] = 0
        pq = [(0, repr(S), S)]
        while pq:
            d, _, x = heapq.heappop(pq)
            if d != dist[x]:
                continue
            for idx, edge in enumerate(graph[x]):
                y, cap, cost, _, _ = edge
                if cap <= 0:
                    continue
                nd = d + cost + potential[x] - potential[y]
                if nd < dist[y]:
                    dist[y] = nd
                    prev[y] = (x, idx)
                    heapq.heappush(pq, (nd, repr(y), y))
        if math.isinf(dist[T]):
            return AssignmentLowerBoundResult(False, math.inf, (), need)
        for n in nodes:
            if not math.isinf(dist[n]):
                potential[n] += dist[n]
        x = T
        while x != S:
            p, idx = prev[x]
            edge = graph[p][idx]
            edge[1] -= 1
            graph[x][edge[3]][1] += 1
            variable_cost += edge[2]
            x = p
        flow += 1

    chosen = list(forced)
    for u in L:
        for edge in graph[LN[u]]:
            if edge[4] is not None and edge[1] == 0:
                chosen.append(edge[4])

    return AssignmentLowerBoundResult(
        True,
        forced_cost + variable_cost,
        tuple(sorted(chosen)),
        need,
    )


def budget_feasible_edge_superset(
    costs: Mapping[Edge, int],
    left: Iterable[int],
    right: Iterable[int],
    need: int,
    budget: int,
) -> Tuple[Tuple[Edge, ...], AssignmentLowerBoundResult]:
    """Return every edge not disproved by the total assignment lower bound.

    An edge is retained iff some cardinality-`need` matching containing that edge
    has anchor-disagreement lower bound <= `budget`. Because omitted non-anchor
    pairwise disagreements are non-negative, every truly feasible full alignment
    is contained in this returned candidate graph.
    """
    if budget < 0:
        raise ValueError("budget must be non-negative")
    left = tuple(left)
    right = tuple(right)
    base = min_cost_cardinality_matching(costs, left, right, need)
    if not base.feasible or base.minimum_cost > budget:
        return (), base
    kept = []
    for e in sorted(costs):
        if e[0] not in left or e[1] not in right:
            continue
        r = min_cost_cardinality_matching(costs, left, right, need, forced=(e,))
        if r.feasible and r.minimum_cost <= budget:
            kept.append(e)
    return tuple(kept), base
