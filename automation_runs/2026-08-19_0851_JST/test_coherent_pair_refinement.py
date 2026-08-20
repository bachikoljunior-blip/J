from itertools import combinations, permutations

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

    def weight(u, v):
        return weights[tuple(sorted((u, v)))]

    automorphisms = tuple(
        p
        for p in permutations(range(6))
        if all(
            weight(u, v) == weight(p[u], p[v])
            for u, v in combinations(range(6), 2)
        )
    )
    unseen = set(range(6))
    orbits = []
    while unseen:
        u = min(unseen)
        orbit = frozenset(p[u] for p in automorphisms)
        orbits.append(orbit)
        unseen.difference_update(orbit)

    assert len(automorphisms) == 2
    assert {frozenset(cell) for cell in r.color_classes} == set(orbits)
    assert sorted(map(len, r.color_classes)) == [1, 1, 1, 1, 2]
    assert r.rank == 26


def test_stability_uses_color_partition_not_transient_numeric_ids():
    # The same rev118 relation used to cycle its compressed integer IDs after
    # the 2-WL partition was already stable and incorrectly hit max_rounds.
    weights = {
        (0, 1): 1, (0, 2): 1, (0, 3): 1, (0, 4): 2, (0, 5): 1,
        (1, 2): 2, (1, 3): 1, (1, 4): 1, (1, 5): 1,
        (2, 3): 2, (2, 4): 0, (2, 5): 2,
        (3, 4): 1, (3, 5): 1, (4, 5): 2,
    }
    r = coherent_refine_pair_relation(6, tuple(weights.items()), max_rounds=8)
    assert r.status == "certified_coherent_point_split"
    assert r.refinement_rounds < 8


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
