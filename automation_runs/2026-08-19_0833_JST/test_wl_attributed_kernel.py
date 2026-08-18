import numpy as np
from wl_attributed_kernel import wl_attributed_feature_map, wl_attributed_kernel, gram_matrix


def path_graph(n):
    a = np.zeros((n, n), dtype=int)
    for i in range(n - 1):
        a[i, i + 1] = a[i + 1, i] = 1
    return a


def cycle_graph(n):
    a = path_graph(n)
    a[0, n - 1] = a[n - 1, 0] = 1
    return a


def permute_graph(a, x, p):
    return a[np.ix_(p, p)], x[p]


def test_exact_permutation_invariance_on_attributed_graph():
    rng = np.random.default_rng(11)
    n = 90
    a = path_graph(n)
    for i in range(0, n - 7, 9):
        a[i, i + 7] = a[i + 7, i] = 1
    x = rng.normal(size=(n, 5))
    p = rng.permutation(n)
    ap, xp = permute_graph(a, x, p)
    f1 = wl_attributed_feature_map(a, x, iterations=4, rff_components=48, seed=7)
    f2 = wl_attributed_feature_map(ap, xp, iterations=4, rff_components=48, seed=7)
    assert f1.keys() == f2.keys()
    for k in f1:
        assert np.isclose(f1[k], f2[k], atol=1e-11, rtol=1e-11)
    assert np.isclose(wl_attributed_kernel((a, x), (ap, xp), iterations=4,
                      rff_components=48, seed=7), 1.0, atol=1e-11)


def test_scales_to_hundreds_of_nodes_without_factorial_enumeration():
    rng = np.random.default_rng(5)
    n = 650
    a = cycle_graph(n)
    for i in range(0, n, 17):
        j = (i + 31) % n
        a[i, j] = a[j, i] = 1
    x = rng.normal(size=(n, 6))
    f = wl_attributed_feature_map(a, x, iterations=5, rff_components=24, seed=2)
    assert len(f) > 0 and all(np.isfinite(v) for v in f.values())


def test_continuous_attributes_affect_similarity_on_same_skeleton():
    rng = np.random.default_rng(8)
    a = path_graph(55)
    x = rng.normal(size=(55, 4))
    y = x.copy(); y[::3] += 4.0
    same = wl_attributed_kernel((a, x), (a, x), iterations=3, rff_components=64, seed=4)
    changed = wl_attributed_kernel((a, x), (a, y), iterations=3, rff_components=64, seed=4)
    assert same > 0.999999999 and changed < same - 0.02


def test_gram_is_psd_up_to_numerical_tolerance():
    rng = np.random.default_rng(21)
    graphs = []
    for n in [17, 18, 19, 20, 21, 22]:
        a = path_graph(n)
        if n % 2 == 0: a[0, n - 1] = a[n - 1, 0] = 1
        graphs.append((a, rng.normal(size=(n, 3))))
    K = gram_matrix(graphs, iterations=3, rff_components=40, seed=9)
    assert np.allclose(K, K.T, atol=1e-12)
    assert np.linalg.eigvalsh(K).min() > -1e-10
    assert np.allclose(np.diag(K), 1.0, atol=1e-12)


def test_structure_changes_can_be_detected_even_with_equal_attribute_multiset():
    rng = np.random.default_rng(31)
    n = 31
    x = rng.normal(size=(n, 4))
    sim = wl_attributed_kernel((path_graph(n), x), (cycle_graph(n), x),
                               iterations=4, rff_components=32, seed=3)
    assert sim < 0.99
