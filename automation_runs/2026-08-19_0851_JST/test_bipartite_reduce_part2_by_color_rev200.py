from bipartite_reduce_part2_by_color_v1 import reduce_part2_by_color_certificate


def test_twin_free_full_graph_selects_side_with_required_defect():
    # C0={0} leaves five left points indistinguishable, so it fails the 1/4
    # defect threshold. C1={1,2,3} separates those points enough to pass.
    edges = {
        (1, 3),
        (2, 2),
        (3, 1),
        (4, 1), (4, 2), (4, 3),
        (5, 0),
    }
    got = reduce_part2_by_color_certificate(
        6, 4, edges, (0,), (1, 2, 3), alpha=0.75
    )
    assert got.status == "certified_reduce_part2_by_color"
    assert got.theorem_gate_verified
    assert got.selected_part_index == 1
    assert got.selected_part == (1, 2, 3)
    assert got.part0_relative_symmetry_defect < 0.25
    assert got.part1_relative_symmetry_defect >= 0.25
    assert all(len(C) == 1 for C in got.full_left_twin_classes)


def test_nontrivial_full_left_twins_fail_before_theorem_selection():
    edges = {(0, 0), (1, 0), (2, 1), (3, 1)}
    got = reduce_part2_by_color_certificate(
        4, 2, edges, (0,), (1,), alpha=0.75
    )
    assert got.status == "reduce_part2_requires_twin_free_left"
    assert not got.theorem_gate_verified
    assert got.selected_part_index is None


def test_invalid_right_partition_is_rejected():
    edges = {(0, 0), (1, 1), (2, 2)}
    try:
        reduce_part2_by_color_certificate(3, 3, edges, (0, 1), (1, 2), alpha=0.75)
    except ValueError as exc:
        assert "disjoint cover" in str(exc)
    else:
        raise AssertionError("overlapping right partition must be rejected")
