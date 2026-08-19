from bipartite_degree_alpha_partition_v1 import bipartite_degree_alpha_partition


def test_degree_classes_give_canonical_alpha_partition():
    edges = {
        (0, 0),
        (1, 1),
        (2, 2),
        (3, 0), (3, 1),
        (4, 1), (4, 2),
        (5, 0), (5, 2),
    }
    got = bipartite_degree_alpha_partition(6, 3, edges, alpha=2 / 3)
    assert got.status == "certified_bipartite_degree_alpha_partition"
    assert got.alpha_partition_certified
    assert tuple(sorted(map(len, got.color_cells))) == (3, 3)
    assert got.canonical and got.exact


def test_unique_dominant_regular_twin_free_cell_is_exposed_for_hypergraph_stage():
    edges = {
        (0, 0), (0, 1),
        (1, 0), (1, 2),
        (2, 0), (2, 3),
        (3, 1), (3, 2),
        (4, 1), (4, 3),
        (5, 2),
    }
    got = bipartite_degree_alpha_partition(6, 4, edges, alpha=0.75)
    assert got.status == "certified_bipartite_degree_dominant_cell"
    assert not got.alpha_partition_certified
    assert got.dominant_cell == (0, 1, 2, 3, 4)
    assert got.dominant_degree == 2
    assert got.dominant_twin_free


def test_dominant_regular_cell_reports_remaining_twins_without_progress_claim():
    edges = {
        (0, 0), (1, 0),
        (2, 1), (3, 1),
        (4, 2),
        (5, 2), (5, 3),
    }
    got = bipartite_degree_alpha_partition(6, 4, edges, alpha=0.75)
    assert got.status == "certified_bipartite_degree_dominant_cell"
    assert got.dominant_degree == 1
    assert got.dominant_cell == (0, 1, 2, 3, 4)
    assert not got.dominant_twin_free


def test_existing_left_colors_refine_degree_partition_canonically():
    edges = {(0, 0), (1, 1), (2, 2), (3, 0)}
    got = bipartite_degree_alpha_partition(
        4, 3, edges, alpha=0.75, left_colors=(0, 0, 1, 1)
    )
    assert got.status == "certified_bipartite_degree_alpha_partition"
    assert tuple(sorted(map(len, got.color_cells))) == (2, 2)
