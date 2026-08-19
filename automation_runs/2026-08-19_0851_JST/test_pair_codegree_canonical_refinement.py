from itertools import combinations

from pair_codegree_canonical_refinement import refine_pair_codegrees


def relation_from_full_sets(m, full_sets):
    full_sets = {tuple(sorted(T)) for T in full_sets}
    return tuple((T, T in full_sets) for T in combinations(range(m), 3))


def test_regular_point_degrees_can_split_at_pair_codegree_level():
    # Every point occurs in exactly three full triples, so point/full-count
    # aggregation alone is regular. Pair codegrees nevertheless distinguish
    # {2,4} from the other four points.
    full_sets = {
        (0, 1, 2), (0, 3, 4), (0, 4, 5),
        (1, 2, 3), (1, 4, 5), (2, 3, 5),
    }
    r = refine_pair_codegrees(6, relation_from_full_sets(6, full_sets))
    assert r.status == "certified_pair_codegree_split"
    assert sorted(map(len, r.color_classes)) == [2, 4]
    assert (2, 4) in r.color_classes
    assert r.pair_weight_spectrum == ((0, 1), (1, 10), (2, 4))


def test_vertex_transitive_nonconstant_pair_relation_is_preserved_not_overclaimed():
    m = 7
    full_sets = {
        tuple(sorted((i, (i + 1) % m, (i + 2) % m)))
        for i in range(m)
    }
    r = refine_pair_codegrees(m, relation_from_full_sets(m, full_sets))
    assert r.status == "canonical_edge_colored_relation"
    assert r.color_classes == (tuple(range(m)),)
    assert r.pair_weight_spectrum == ((0, 7), (1, 7), (2, 7))


def test_uniform_full_relation_stays_homogeneous():
    m = 8
    relation = tuple((T, True) for T in combinations(range(m), 3))
    r = refine_pair_codegrees(m, relation)
    assert r.status == "pair_relation_homogeneous"
    assert r.color_classes == (tuple(range(m)),)
    assert r.pair_weight_spectrum == ((6, 28),)


def test_relabeling_preserves_class_sizes_and_moves_structural_class():
    full_sets = {
        (0, 1, 2), (0, 3, 4), (0, 4, 5),
        (1, 2, 3), (1, 4, 5), (2, 3, 5),
    }
    base = refine_pair_codegrees(6, relation_from_full_sets(6, full_sets))
    p = (3, 5, 1, 0, 4, 2)
    moved_sets = {tuple(sorted(p[u] for u in T)) for T in full_sets}
    moved = refine_pair_codegrees(6, relation_from_full_sets(6, moved_sets))
    assert sorted(map(len, moved.color_classes)) == sorted(map(len, base.color_classes))
    assert tuple(sorted((p[2], p[4]))) in moved.color_classes
