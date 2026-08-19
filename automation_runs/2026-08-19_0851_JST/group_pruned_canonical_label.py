from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional
import numpy as np

from permutation_group_schreier import Permutation, group_orbit
from coset_stabilizer_primitives import pointwise_stabilizer_chain
from exact_gi_isomorphism_coset import exact_gi_isomorphism_coset


@dataclass(frozen=True)
class CanonicalLabelCertificate:
    status: str
    canonical_permutation: Optional[Permutation]
    canonical_code: Optional[bytes]
    automorphism_order: int
    states_explored: int
    leaves_verified: int
    reason: str


def _validate(graph):
    a = np.asarray(graph[0]) != 0
    x = np.asarray(graph[1], dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1] or not np.array_equal(a, a.T) or np.any(np.diag(a)):
        raise ValueError("expected simple undirected adjacency")
    if x.ndim != 2 or x.shape[0] != len(a) or x.shape[1] < 1 or not np.all(np.isfinite(x)):
        raise ValueError("bad attributes")
    return a, x


def _key(row):
    return np.ascontiguousarray(row, dtype=np.float64).tobytes()


def _compress(signatures):
    lab = {s: i for i, s in enumerate(sorted(set(signatures), key=repr))}
    return [lab[s] for s in signatures]


def _refine(a, x, fixed, max_rounds=64):
    mark = {u: t for t, u in enumerate(fixed)}
    signatures = [(_key(x[i]), mark.get(i, -1)) for i in range(len(a))]
    colors = _compress(signatures)
    for _ in range(max_rounds):
        signatures = [
            (colors[i], tuple(sorted(Counter(colors[k] for k in np.flatnonzero(a[i])).items())))
            for i in range(len(a))
        ]
        nxt = _compress(signatures)
        if nxt == colors:
            break
        colors = nxt
    return colors


def _leaf_code(a, x, colors):
    order = tuple(i for _, i in sorted((c, i) for i, c in enumerate(colors)))
    p = [0] * len(order)
    for pos, u in enumerate(order):
        p[u] = pos
    aa = a[np.ix_(order, order)]
    xx = np.ascontiguousarray(x[list(order)], dtype=np.float64)
    header = len(a).to_bytes(4, "big") + x.shape[1].to_bytes(4, "big")
    attrs = xx.tobytes(order="C")
    upper = bytes(int(aa[i, j]) for i in range(len(a)) for j in range(i + 1, len(a)))
    return header + attrs + upper, tuple(p)


def exact_group_pruned_canonical_label(graph, *, max_states=500000, max_group_nodes=500000) -> CanonicalLabelCertificate:
    """Exact isomorphism-invariant canonical labeling with safe orbit pruning.

    The target automorphism group is first certified exactly. At each IR node the
    pointwise stabilizer of the already individualized vertices acts on the chosen
    refined color cell. Branches in the same exact stabilizer orbit are equivalent,
    so only one representative per orbit is explored. The minimum verified leaf
    code is therefore unchanged by pruning. Limits fail closed.
    """
    a, x = _validate(graph)
    gi = exact_gi_isomorphism_coset((a, x), (a, x), max_nodes=max_group_nodes)
    if gi.status != "exact_isomorphism_coset":
        return CanonicalLabelCertificate(
            "undetermined_group_limit", None, None, 0, 0, 0,
            "exact automorphism group was not certified",
        )
    aut = gi.coset.subgroup
    states = 0
    leaves = 0
    best_code = None
    best_permutation = None
    limit = False

    def rec(fixed):
        nonlocal states, leaves, best_code, best_permutation, limit
        if limit:
            return
        states += 1
        if states > max_states:
            limit = True
            return
        colors = _refine(a, x, fixed)
        counts = Counter(colors)
        if all(v == 1 for v in counts.values()):
            code, p = _leaf_code(a, x, colors)
            leaves += 1
            if best_code is None or code < best_code:
                best_code, best_permutation = code, p
            return

        color = min((c for c, v in counts.items() if v > 1), key=lambda c: (counts[c], c))
        cell = tuple(i for i, c in enumerate(colors) if c == color)
        stabilizer = pointwise_stabilizer_chain(aut, fixed)

        representatives = []
        seen = set()
        cell_set = set(cell)
        for v in cell:
            if v in seen:
                continue
            orbit = set(group_orbit(stabilizer, v)) & cell_set
            seen |= orbit
            representatives.append(min(orbit))

        for v in sorted(representatives):
            rec(fixed + (v,))
            if limit:
                return

    rec(())
    if limit:
        return CanonicalLabelCertificate(
            "undetermined_search_limit", None, None, aut.order, states, leaves,
            "canonical IR search exceeded max_states",
        )
    if best_code is None or best_permutation is None:
        raise AssertionError("no canonical leaf was produced")
    return CanonicalLabelCertificate(
        "exact_canonical_label", best_permutation, best_code, aut.order, states, leaves,
        "complete invariant IR search with exact automorphism-stabilizer orbit pruning",
    )
