from __future__ import annotations

import random
import shutil

import pytest

from nauty_labelg_oracle import canonical_graph6_with_labelg, encode_graph6


def relabel_edges(n, edges, p):
    return [(p[u], p[v]) for u, v in edges]


def families():
    # deterministic ordinary + symmetry-heavy cases; labelg remains the independent oracle.
    for n in range(1, 13):
        yield n, []
        yield n, [(i, (i + 1) % n) for i in range(n)] if n >= 3 else []
        yield n, [(i, j) for i in range(n) for j in range(i + 1, n)]
    rng = random.Random(141)
    for n in range(4, 13):
        for _ in range(20):
            yield n, [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < 0.5]


@pytest.mark.skipif(shutil.which('labelg') is None, reason='independent nauty labelg executable unavailable')
def test_labelg_is_invariant_under_arbitrary_relabeling():
    rng = random.Random(14101)
    checked = 0
    for n, edges in families():
        base = canonical_graph6_with_labelg(n, edges)
        assert base.status == 'ok', base
        for _ in range(8):
            p = list(range(n))
            rng.shuffle(p)
            got = canonical_graph6_with_labelg(n, relabel_edges(n, edges, p))
            assert got.status == 'ok', got
            assert got.canonical_graph6 == base.canonical_graph6
            checked += 1
    assert checked >= 1000


def test_interchange_encoding_does_not_depend_on_edge_order_or_duplicates():
    n = 8
    edges = [(0, 7), (1, 4), (2, 5), (3, 6), (0, 3)]
    noisy = list(reversed(edges)) + [(7, 0), (4, 1), (0, 3)]
    assert encode_graph6(n, noisy) == encode_graph6(n, edges)
