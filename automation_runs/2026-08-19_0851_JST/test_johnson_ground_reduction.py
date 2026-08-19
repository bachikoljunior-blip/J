from itertools import combinations, permutations

from johnson_pair_relation_recognizer import recognize_johnson_pair_relation
from johnson_ground_reduction import reduce_johnson_colored_vertices


def johnson_pair_weights(v, k):
    vertices = list(combinations(range(v), k))
    return tuple(
        ((i, j), int(len(set(vertices[i]) & set(vertices[j])) == k - 1))
        for i, j in combinations(range(len(vertices)), 2)
    )


def test_reduction_is_directly_reversible_and_shrinks_domain():
    cert = recognize_johnson_pair_relation(10, johnson_pair_weights(5, 2))
    values = tuple((i % 3) for i in range(10))
    reduced = reduce_johnson_colored_vertices(cert, values)
    assert reduced.status == "exact_johnson_ground_reduction"
    assert (reduced.quotient_size, reduced.ground_size, reduced.subset_size) == (10, 5, 2)
    assert not reduced.complement_ambiguity
    standard_values = dict(reduced.standard_colored_subsets)
    standard_vertices = list(combinations(range(5), 2))
    p = cert.isomorphism_coset.representative
    assert all(standard_values[standard_vertices[p[i]]] == values[i] for i in range(10))


def test_relabeling_changes_coordinates_only_within_ground_symmetric_ambiguity():
    base_weights = dict(johnson_pair_weights(5, 2))
    values = tuple(int(i in {0, 1, 3, 7}) for i in range(10))
    base_cert = recognize_johnson_pair_relation(10, tuple(base_weights.items()))
    base = reduce_johnson_colored_vertices(base_cert, values)

    q = tuple(reversed(range(10)))
    moved_weights = []
    for (u, v), w in base_weights.items():
        a, b = sorted((q[u], q[v]))
        moved_weights.append(((a, b), w))
    moved_values = [None] * 10
    for i, j in enumerate(q):
        moved_values[j] = values[i]
    moved_cert = recognize_johnson_pair_relation(10, moved_weights)
    moved = reduce_johnson_colored_vertices(moved_cert, moved_values)

    A = dict(base.standard_colored_subsets)
    B = dict(moved.standard_colored_subsets)
    found = False
    for sigma in permutations(range(5)):
        ok = True
        for S, value in A.items():
            T = tuple(sorted(sigma[x] for x in S))
            if B[T] != value:
                ok = False
                break
        if ok:
            found = True
            break
    assert found


def test_middle_layer_preserves_complement_ambiguity_explicitly():
    cert = recognize_johnson_pair_relation(20, johnson_pair_weights(6, 3))
    reduced = reduce_johnson_colored_vertices(cert, [0] * 20)
    assert reduced.status == "exact_johnson_ground_reduction"
    assert reduced.complement_ambiguity
    assert reduced.target_ambiguity_order == 1440
    assert reduced.ground_size == 6
