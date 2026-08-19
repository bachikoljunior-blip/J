import itertools
import numpy as np
from triangle_partial_budget_lb import infer_triangle_budget_lower_bound, selected_triangle_interval


def graph_from_edges(n, edges):
    a = np.zeros((n, n), dtype=int)
    for u, v in edges:
        a[u, v] = a[v, u] = 1
    return a, np.zeros((n, 1), dtype=int)


def exact_min_partial_disagreements(a, b, max_unmatched_total):
    n, m = len(a), len(b)
    kmin = max(0, (n + m - max_unmatched_total + 1) // 2)
    best = None
    for s in range(kmin, min(n, m) + 1):
        for sa in itertools.combinations(range(n), s):
            for sb in itertools.combinations(range(m), s):
                for perm in itertools.permutations(sb):
                    e = 0
                    for i in range(s):
                        for j in range(i + 1, s):
                            e += int(bool(a[sa[i], sa[j]]) != bool(b[perm[i], perm[j]]))
                    best = e if best is None else min(best, e)
    return best


def test_degree_regular_graphs_separated_by_triangles():
    c6 = graph_from_edges(6, [(i, (i + 1) % 6) for i in range(6)])
    two_tri = graph_from_edges(6, [(0,1),(1,2),(2,0),(3,4),(4,5),(5,3)])
    cert = infer_triangle_budget_lower_bound(c6, two_tri, max_unmatched_total=0, max_common_edge_disagreements=0)
    assert cert.lower_bound_disagreements == 1
    assert cert.inconsistent


def test_partial_selection_can_correctly_erase_triangle_signal():
    c6 = graph_from_edges(6, [(i, (i + 1) % 6) for i in range(6)])
    two_tri = graph_from_edges(6, [(0,1),(1,2),(2,0),(3,4),(4,5),(5,3)])
    cert = infer_triangle_budget_lower_bound(c6, two_tri, max_unmatched_total=4)
    assert cert.minimum_common_nodes == 4
    assert cert.lower_bound_disagreements == 0


def test_selected_triangle_interval_contains_all_small_subsets():
    rng = np.random.default_rng(7)
    for n in range(3, 7):
        for _ in range(20):
            a = np.triu((rng.random((n,n)) < 0.4).astype(int), 1); a = a + a.T
            for s in range(n + 1):
                lo, hi = selected_triangle_interval(a, s)
                vals = []
                for sub in itertools.combinations(range(n), s):
                    t = 0
                    for i, j, k in itertools.combinations(sub, 3):
                        t += int(a[i,j] and a[i,k] and a[j,k])
                    vals.append(t)
                assert lo <= min(vals) <= max(vals) <= hi


def test_random_oracle_soundness_small_partial_graphs():
    rng = np.random.default_rng(11)
    for _ in range(160):
        n = int(rng.integers(3, 6)); m = int(rng.integers(3, 6))
        aa = np.triu((rng.random((n,n)) < 0.42).astype(int), 1); aa += aa.T
        bb = np.triu((rng.random((m,m)) < 0.42).astype(int), 1); bb += bb.T
        max_unmatched = int(rng.integers(abs(n-m), n+m-1))
        cert = infer_triangle_budget_lower_bound((aa,np.zeros((n,1),int)), (bb,np.zeros((m,1),int)), max_unmatched_total=max_unmatched)
        exact = exact_min_partial_disagreements(aa, bb, max_unmatched)
        if exact is not None:
            assert cert.lower_bound_disagreements <= exact
