from itertools import combinations

from coherent_pair_refinement import coherent_refine_pair_relation


def johnson_pair_weights(v, k):
    vertices = list(combinations(range(v), k))
    return tuple(
        ((i, j), int(len(set(vertices[i]) & set(vertices[j])) == k - 1))
        for i, j in combinations(range(len(vertices)), 2)
    )


def test_johnson_5_2_stabilizes_to_rank_three_association_relation():
    r = coherent_refine_pair_relation(10, johnson_pair_weights(5, 2))
    assert r.status == "stable_coherent_pair_relation"
    assert r.rank == 3
    assert r.color_classes == (tuple(range(10)),)


def test_regular_pair_codegrees_can_split_after_coherent_refinement():
    # Pair weights from the rev118 regular 3-uniform example.
    weights = {
        (0, 1): 1, (0, 2): 1, (0, 3): 1, (0, 4): 2, (0, 5): 1,
        (1, 2): 2, (1, 3): 1, (1, 4): 1, (1, 5): 1,
        (2, 3): 2, (2, 4): 0, (2, 5): 2,
        (3, 4): 1, (3, 5): 1, (4, 5): 2,
    }
    r = coherent_refine_pair_relation(6, tuple(weights.items()))
    assert r.status == "certified_coherent_point_split"
    assert sorted(map(len, r.color_classes)) == [2, 4]
    assert (2, 4) in r.color_classes
    assert r.rank > 3


def test_vertex_transitive_cyclic_distance_relation_remains_homogeneous_but_nontrivial():
    m = 7
    weights = []
    for u, v in combinations(range(m), 2):
        d = min((u - v) % m, (v - u) % m)
        weights.append(((u, v), d))
    r = coherent_refine_pair_relation(m, weights)
    assert r.status == "stable_coherent_pair_relation"
    assert r.color_classes == (tuple(range(m)),)
    assert r.rank == 4
