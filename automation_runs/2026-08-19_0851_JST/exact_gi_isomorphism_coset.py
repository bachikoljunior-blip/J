from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np

from permutation_group_schreier import Permutation, identity, schreier_stabilizer_chain
from coset_stabilizer_primitives import RightCoset


class SearchLimit(Exception):
    pass


@dataclass
class _Budget:
    limit: int
    used: int = 0

    def tick(self) -> None:
        self.used += 1
        if self.used > self.limit:
            raise SearchLimit


@dataclass(frozen=True)
class ExactGICosetCertificate:
    status: str
    coset: Optional[RightCoset]
    isomorphism_count: int
    automorphism_order: int
    search_nodes: int
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


def _compress_joint(sa, sb):
    lab = {s: i for i, s in enumerate(sorted(set(sa + sb), key=repr))}
    return [lab[s] for s in sa], [lab[s] for s in sb]


def _refine(a, x, b, y, seeds, max_rounds=64):
    mark_a = {u: t for t, (u, _) in enumerate(seeds)}
    mark_b = {v: t for t, (_, v) in enumerate(seeds)}
    sa = [(_key(x[i]), mark_a.get(i, -1)) for i in range(len(a))]
    sb = [(_key(y[j]), mark_b.get(j, -1)) for j in range(len(b))]
    ca, cb = _compress_joint(sa, sb)
    for _ in range(max_rounds):
        sa = [(ca[i], tuple(sorted(Counter(ca[k] for k in np.flatnonzero(a[i])).items()))) for i in range(len(a))]
        sb = [(cb[j], tuple(sorted(Counter(cb[k] for k in np.flatnonzero(b[j])).items()))) for j in range(len(b))]
        na, nb = _compress_joint(sa, sb)
        if na == ca and nb == cb:
            break
        ca, cb = na, nb
    return ca, cb


def _verify_iso(a, x, b, y, p) -> bool:
    p = np.asarray(p, dtype=int)
    return np.array_equal(x, y[p]) and np.array_equal(a, b[np.ix_(p, p)])


def _find_iso(a, x, b, y, seeds, budget: _Budget) -> Optional[Permutation]:
    budget.tick()
    n = len(a)
    ca, cb = _refine(a, x, b, y, seeds)
    if Counter(ca) != Counter(cb):
        return None
    counts = Counter(ca)
    if all(v == 1 for v in counts.values()):
        pos = {c: j for j, c in enumerate(cb)}
        p = tuple(pos[ca[i]] for i in range(n))
        return p if _verify_iso(a, x, b, y, p) else None

    color = min((c for c, v in counts.items() if v > 1), key=lambda c: (counts[c], c))
    u = next(i for i, c in enumerate(ca) if c == color)
    for v in (j for j, c in enumerate(cb) if c == color):
        witness = _find_iso(a, x, b, y, seeds + ((u, v),), budget)
        if witness is not None:
            return witness
    return None


def _automorphism_group(a, x, budget: _Budget):
    n = len(a)
    e = identity(n)
    cache = {}

    def rec(fixed: Tuple[int, ...]):
        budget.tick()
        if fixed in cache:
            return cache[fixed]
        seeds = tuple((u, u) for u in fixed)
        ca, cb = _refine(a, x, a, x, seeds)
        if ca != cb:
            raise AssertionError("self refinement mismatch")
        counts = Counter(ca)
        if all(v == 1 for v in counts.values()):
            group = schreier_stabilizer_chain([e])
            cache[fixed] = group
            return group

        color = min((c for c, v in counts.items() if v > 1), key=lambda c: (counts[c], c))
        candidates = tuple(i for i, c in enumerate(ca) if c == color)
        u = candidates[0]
        stabilizer = rec(fixed + (u,))

        generators = list(stabilizer.original_generators)
        orbit = []
        for v in candidates:
            witness = _find_iso(a, x, a, x, seeds + ((u, v),), budget)
            if witness is None:
                continue
            if any(witness[f] != f for f in fixed) or witness[u] != v or not _verify_iso(a, x, a, x, witness):
                raise AssertionError("invalid automorphism transporter")
            orbit.append((v, witness))
            if witness != e:
                generators.append(witness)

        group = schreier_stabilizer_chain(generators or [e])
        expected_order = stabilizer.order * len(orbit)
        if group.order != expected_order:
            raise AssertionError("automorphism orbit-stabilizer mismatch")
        if not all(_verify_iso(a, x, a, x, g) and all(g[f] == f for f in fixed) for g in group.original_generators):
            raise AssertionError("automorphism generator verification failed")
        cache[fixed] = group
        return group

    return rec(())


def exact_gi_isomorphism_coset(graph_a, graph_b, *, max_nodes=500000) -> ExactGICosetCertificate:
    """Return the complete isomorphism set as one exact right coset.

    One directly verified A->B isomorphism is found by complete resource-bounded
    individualization/refinement search.  Aut(B) is reconstructed exactly by
    orbit-stabilizer recursion from verified automorphism transporters rather than
    enumerating all automorphisms.  If p is the verified witness, all A->B
    isomorphisms are exactly p*Aut(B), represented by RightCoset.
    """
    budget = _Budget(max_nodes)
    try:
        a, x = _validate(graph_a)
        b, y = _validate(graph_b)
        if len(a) != len(b) or x.shape[1] != y.shape[1]:
            return ExactGICosetCertificate("non_isomorphic", None, 0, 0, budget.used, "size or attribute-dimension mismatch")

        witness = _find_iso(a, x, b, y, (), budget)
        if witness is None:
            return ExactGICosetCertificate("non_isomorphic", None, 0, 0, budget.used, "complete IR witness search proved no isomorphism")

        aut_b = _automorphism_group(b, y, budget)
        if not _verify_iso(a, x, b, y, witness):
            raise AssertionError("isomorphism witness failed direct verification")
        return ExactGICosetCertificate(
            "exact_isomorphism_coset", RightCoset(aut_b, witness), aut_b.order, aut_b.order, budget.used,
            "one verified isomorphism times the exact target automorphism group",
        )
    except SearchLimit:
        return ExactGICosetCertificate("undetermined_search_limit", None, 0, 0, budget.used, "exact GI/group reconstruction exceeded max_nodes")
