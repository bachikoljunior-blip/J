from bipartite_twin_membership_partition_v1 import bipartite_twin_membership_alpha_partition


def test_one_twin_pair_plus_four_singletons_gives_canonical_alpha_split():
    edges = {
        (0, 0), (1, 0),
        (2, 1),
        (3, 2),
        (4, 3),
        (5, 0), (5, 1),
    }
    got = bipartite_twin_membership_alpha_partition(6, 4, edges, alpha=0.75)
    assert got.status == "certified_bipartite_twin_membership_alpha_partition"
    assert got.alpha_partition_certified
    assert got.canonical and got.exact
    assert got.vertices_with_twins == (0, 1)
    assert got.twin_free_vertices == (2, 3, 4, 5)
    assert tuple(sorted(map(len, got.color_cells))) == (2, 4)


def test_three_twin_pairs_do_not_become_falsely_labeled_three_color_partition():
    edges = {(0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (5, 2)}
    got = bipartite_twin_membership_alpha_partition(6, 3, edges, alpha=0.75)
    assert got.status == "bipartite_twin_membership_no_alpha_partition"
    assert not got.alpha_partition_certified
    assert got.vertices_with_twins == tuple(range(6))
    assert got.twin_free_vertices == ()
    assert sorted(map(len, got.twin_classes)) == [2, 2, 2]


def test_twin_free_graph_has_exact_structure_but_no_membership_split():
    edges = {(0, 0), (1, 1), (2, 2), (3, 3)}
    got = bipartite_twin_membership_alpha_partition(4, 4, edges, alpha=0.75)
    assert got.status == "bipartite_twin_membership_no_alpha_partition"
    assert got.vertices_with_twins == ()
    assert got.twin_free_vertices == tuple(range(4))
    assert not got.alpha_partition_certified
    assert got.exact and got.canonical


def test_existing_left_colors_are_part_of_exact_twin_relation():
    edges = {(0, 0), (1, 0), (2, 1), (3, 2)}
    uncolored = bipartite_twin_membership_alpha_partition(4, 3, edges, alpha=0.75)
    colored = bipartite_twin_membership_alpha_partition(
        4, 3, edges, alpha=0.75, left_colors=(0, 1, 0, 0)
    )
    assert any(len(C) == 2 for C in uncolored.twin_classes)
    assert all(len(C) == 1 for C in colored.twin_classes)
    assert not colored.alpha_partition_certified
