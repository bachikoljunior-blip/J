from __future__ import annotations

import random

from canonical_oracle_adapter_v1 import canonicalize_with_external_oracle, graph6_text


def relabel_edges(n, edges, p):
    return [(p[u], p[v]) for u, v in edges]


def families():
    # Ordinary and symmetry-heavy families.
    for n in range(1, 13):
        yield f"empty-{n}", n, []
        yield f"cycle-{n}", n, [(i, (i + 1) % n) for i in range(n)] if n >= 3 else []
        yield f"complete-{n}", n, [(i, j) for i in range(n) for j in range(i + 1, n)]

    # Adversarial structural families: large automorphism groups and repeated local views.
    for m in range(2, 7):
        n = 2 * m
        yield f"complete-bipartite-{m}-{m}", n, [(i, j) for i in range(m) for j in range(m, n)]
        yield f"two-cliques-{m}", n, ([(i, j) for i in range(m) for j in range(i + 1, m)] +
                                      [(i, j) for i in range(m, n) for j in range(i + 1, n)])
    for d in range(2, 5):
        n = 1 << d
        edges = []
        for u in range(n):
            for bit in range(d):
                v = u ^ (1 << bit)
                if u < v:
                    edges.append((u, v))
        yield f"hypercube-{d}", n, edges

    rng = random.Random(142)
    for n in range(4, 17):
        for k in range(16):
            p = 0.15 if k < 8 else 0.5
            yield f"random-{n}-{k}", n, [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < p]


def require_canonical(n, edges):
    out = canonicalize_with_external_oracle(n, edges)
    assert out.status == 'canonical', out
    assert out.canonical_text is not None
    return out.canonical_text


def test_labelg_is_invariant_under_arbitrary_relabeling():
    rng = random.Random(14201)
    checked = 0
    for name, n, edges in families():
        base = require_canonical(n, edges)
        for _ in range(8):
            p = list(range(n))
            rng.shuffle(p)
            got = require_canonical(n, relabel_edges(n, edges, p))
            assert got == base, name
            checked += 1
    assert checked >= 1500


def test_interchange_encoding_does_not_depend_on_edge_order_or_duplicates():
    n = 8
    edges = [(0, 7), (1, 4), (2, 5), (3, 6), (0, 3)]
    noisy = list(reversed(edges)) + [(7, 0), (4, 1), (0, 3)]
    assert graph6_text(n, noisy) == graph6_text(n, edges)
