import itertools
import random
from math import factorial
import numpy as np

from exact_gi_isomorphism_coset import exact_gi_isomorphism_coset


def graph(n, edges, attrs=None):
    a = np.zeros((n, n), dtype=bool)
    for u, v in edges:
        a[u, v] = a[v, u] = 1
    x = np.zeros((n, 1), dtype=float) if attrs is None else np.asarray(attrs, dtype=float).reshape(n, -1)
    return a, x


def permute(g, p):
    a, x = g
    inv = np.argsort(np.asarray(p, dtype=int))
    return a[np.ix_(inv, inv)], x[inv]


def brute_maps(A, B):
    a, x = A
    b, y = B
    out = []
    for p in itertools.permutations(range(len(a))):
        q = np.asarray(p, dtype=int)
        if np.array_equal(x, y[q]) and np.array_equal(a, b[np.ix_(q, q)]):
            out.append(p)
    return out


def test_random_degree_1_to_7_matches_bruteforce_isomorphism_set():
    rng = random.Random(111)
    checked = 0
    for _ in range(160):
        n = rng.randint(1, 7)
        edges = [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < 0.35]
        attrs = [[rng.randrange(2)] for _ in range(n)]
        A = graph(n, edges, attrs)
        if rng.random() < 0.7:
            p = list(range(n)); rng.shuffle(p); B = permute(A, p)
        else:
            edges2 = [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < 0.35]
            B = graph(n, edges2, attrs)
        brute = brute_maps(A, B)
        result = exact_gi_isomorphism_coset(A, B, max_nodes=500000)
        assert result.status != "undetermined_search_limit"
        if not brute:
            assert result.status == "non_isomorphic"
        else:
            assert result.status == "exact_isomorphism_coset"
            assert result.isomorphism_count == len(brute)
            for p in itertools.permutations(range(n)):
                assert result.coset.contains(p) == (p in brute)
        checked += 1
    assert checked == 160


def test_high_symmetry_orders_without_enumerating_automorphisms():
    for n in (5, 7, 9, 12):
        complete = graph(n, [(i, j) for i in range(n) for j in range(i + 1, n)])
        result = exact_gi_isomorphism_coset(complete, complete, max_nodes=500000)
        assert result.status == "exact_isomorphism_coset"
        assert result.automorphism_order == factorial(n)
    for n in (5, 8, 12):
        cycle = graph(n, [(i, (i + 1) % n) for i in range(n)])
        result = exact_gi_isomorphism_coset(cycle, cycle, max_nodes=500000)
        assert result.status == "exact_isomorphism_coset"
        assert result.automorphism_order == 2 * n
