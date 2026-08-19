import random
import numpy as np

from group_pruned_canonical_label import exact_group_pruned_canonical_label


def graph(n, edges, attrs=None):
    a = np.zeros((n, n), dtype=bool)
    for u, v in edges:
        a[u, v] = a[v, u] = 1
    x = np.zeros((n, 1), dtype=float) if attrs is None else np.asarray(attrs, dtype=float).reshape(n, -1)
    return a, x


def relabel(g, p):
    a, x = g
    inv = np.argsort(np.asarray(p, dtype=int))
    return a[np.ix_(inv, inv)], x[inv]


def apply_canonical_permutation(g, p):
    a, x = g
    order = np.argsort(np.asarray(p, dtype=int))
    return a[np.ix_(order, order)], x[order]


def test_random_relabeling_invariance_and_emitted_permutation():
    rng = random.Random(112)
    checked = 0
    for _ in range(120):
        n = rng.randint(1, 8)
        edges = [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < 0.4]
        attrs = [[rng.randrange(3)] for _ in range(n)]
        G = graph(n, edges, attrs)
        first = exact_group_pruned_canonical_label(G, max_states=200000, max_group_nodes=200000)
        assert first.status == "exact_canonical_label"
        canonical = apply_canonical_permutation(G, first.canonical_permutation)
        for _ in range(5):
            p = list(range(n)); rng.shuffle(p)
            H = relabel(G, p)
            other = exact_group_pruned_canonical_label(H, max_states=200000, max_group_nodes=200000)
            assert other.status == "exact_canonical_label"
            assert other.canonical_code == first.canonical_code
            canonical_other = apply_canonical_permutation(H, other.canonical_permutation)
            assert np.array_equal(canonical[0], canonical_other[0])
            assert np.array_equal(canonical[1], canonical_other[1])
        checked += 1
    assert checked == 120


def test_high_symmetry_orbit_pruning_collapses_equivalent_branches():
    for n in (6, 9, 12):
        complete = graph(n, [(i, j) for i in range(n) for j in range(i + 1, n)])
        result = exact_group_pruned_canonical_label(complete)
        assert result.status == "exact_canonical_label"
        assert result.states_explored <= n + 2
        assert result.leaves_verified == 1
    for n in (5, 8, 12):
        cycle = graph(n, [(i, (i + 1) % n) for i in range(n)])
        result = exact_group_pruned_canonical_label(cycle)
        assert result.status == "exact_canonical_label"
        assert result.leaves_verified == 1
