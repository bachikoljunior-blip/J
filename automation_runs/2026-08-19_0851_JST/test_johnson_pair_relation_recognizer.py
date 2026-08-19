from itertools import combinations

from johnson_pair_relation_recognizer import recognize_johnson_pair_relation


def johnson_pair_weights(v, k):
    vertices = list(combinations(range(v), k))
    out = []
    for i, j in combinations(range(len(vertices)), 2):
        weight = 1 if len(set(vertices[i]) & set(vertices[j])) == k - 1 else 0
        out.append(((i, j), weight))
    return tuple(out)


def test_exact_johnson_color_relations_for_three_parameter_sets():
    for v, k, expected_aut in ((5, 2, 120), (6, 2, 720), (6, 3, 1440)):
        weights = johnson_pair_weights(v, k)
        n = len(list(combinations(range(v), k)))
        cert = recognize_johnson_pair_relation(n, weights)
        assert cert.status == "exact_johnson_color_relation"
        assert cert.relation_weight == 1
        assert cert.ground_size == v
        assert cert.subset_size == k
        assert cert.isomorphism_count == expected_aut
        assert cert.isomorphism_coset is not None


def test_vertex_relabeling_preserves_johnson_recognition():
    v, k = 5, 2
    weights = dict(johnson_pair_weights(v, k))
    n = len(list(combinations(range(v), k)))
    p = tuple(reversed(range(n)))
    moved = []
    for (u, w), value in weights.items():
        a, b = sorted((p[u], p[w]))
        moved.append(((a, b), value))
    cert = recognize_johnson_pair_relation(n, moved)
    assert cert.status == "exact_johnson_color_relation"
    assert (cert.ground_size, cert.subset_size) == (5, 2)


def test_cycle_relation_is_exactly_rejected_for_ten_vertices():
    n = 10
    weights = []
    for u, v in combinations(range(n), 2):
        edge = ((u - v) % n in (1, n - 1))
        weights.append(((u, v), int(edge)))
    cert = recognize_johnson_pair_relation(n, weights)
    assert cert.status == "certified_no_johnson_color_relation"


def test_search_limit_fails_closed():
    weights = johnson_pair_weights(5, 2)
    cert = recognize_johnson_pair_relation(10, weights, max_nodes_per_candidate=1)
    assert cert.status == "undetermined_search_limit"
    assert cert.isomorphism_coset is None
