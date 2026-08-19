from itertools import combinations

from coherent_pair_refinement import coherent_refine_pair_relation
from johnson_pair_relation_recognizer import recognize_johnson_pair_relation
from johnson_coherent_scheme_certificate import certify_johnson_coherent_scheme


def johnson_pair_weights(v, k):
    vertices = list(combinations(range(v), k))
    return tuple(
        ((i, j), int(len(set(vertices[i]) & set(vertices[j])) == k - 1))
        for i, j in combinations(range(len(vertices)), 2)
    )


def test_johnson_graph_relations_stabilize_to_exact_distance_schemes():
    for v, k, expected_rank in ((5, 2, 3), (6, 2, 3), (6, 3, 4)):
        weights = johnson_pair_weights(v, k)
        n = len(list(combinations(range(v), k)))
        coherent = coherent_refine_pair_relation(n, weights)
        johnson = recognize_johnson_pair_relation(n, weights)
        cert = certify_johnson_coherent_scheme(coherent, johnson)
        assert cert.status == "exact_johnson_distance_scheme"
        assert cert.exact_distance_scheme
        assert cert.coherent_rank == expected_rank
        assert cert.expected_johnson_rank == expected_rank
        assert len(cert.distance_to_color) == expected_rank


def test_relabeling_does_not_change_distance_scheme_result():
    weights = dict(johnson_pair_weights(5, 2))
    n = 10
    p = tuple(reversed(range(n)))
    moved = []
    for (u, v), value in weights.items():
        a, b = sorted((p[u], p[v]))
        moved.append(((a, b), value))
    coherent = coherent_refine_pair_relation(n, moved)
    johnson = recognize_johnson_pair_relation(n, moved)
    cert = certify_johnson_coherent_scheme(coherent, johnson)
    assert cert.status == "exact_johnson_distance_scheme"
    assert cert.expected_johnson_rank == 3
