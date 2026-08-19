from itertools import combinations

from design_codegree_refinement import refine_design_codegrees


def complete_binary_relation(v, k, selected):
    selected = {tuple(sorted(S)) for S in selected}
    return tuple((S, int(S in selected)) for S in combinations(range(v), k))


def test_first_order_split_for_colored_pairs():
    rows = tuple((S, int(0 in S)) for S in combinations(range(5), 2))
    r = refine_design_codegrees(5, rows)
    assert r.status == "certified_design_codegree_split"
    assert r.decisive_subset_size == 1
    assert sorted(map(len, r.color_classes)) == [1, 4]
    assert (0,) in r.color_classes


def test_pair_codegrees_split_regular_three_uniform_relation():
    selected = {
        (0, 1, 2), (0, 3, 4), (0, 4, 5),
        (1, 2, 3), (1, 4, 5), (2, 3, 5),
    }
    r = refine_design_codegrees(6, complete_binary_relation(6, 3, selected))
    assert r.status == "certified_design_codegree_split"
    assert r.decisive_subset_size == 2
    assert sorted(map(len, r.color_classes)) == [2, 4]
    assert (2, 4) in r.color_classes


def test_fano_plane_is_correctly_left_as_codegree_homogeneous_design_obstruction():
    fano = {
        (0, 1, 2), (0, 3, 4), (0, 5, 6),
        (1, 3, 5), (1, 4, 6), (2, 3, 6), (2, 4, 5),
    }
    r = refine_design_codegrees(7, complete_binary_relation(7, 3, fano))
    assert r.status == "certified_codegree_homogeneous_through_limit"
    assert r.decisive_subset_size == 2
    assert r.color_classes == (tuple(range(7)),)


def test_ground_relabeling_moves_the_structural_split():
    selected = {
        (0, 1, 2), (0, 3, 4), (0, 4, 5),
        (1, 2, 3), (1, 4, 5), (2, 3, 5),
    }
    p = (3, 5, 1, 0, 4, 2)
    moved = {tuple(sorted(p[u] for u in S)) for S in selected}
    r = refine_design_codegrees(6, complete_binary_relation(6, 3, moved))
    assert tuple(sorted((p[2], p[4]))) in r.color_classes
