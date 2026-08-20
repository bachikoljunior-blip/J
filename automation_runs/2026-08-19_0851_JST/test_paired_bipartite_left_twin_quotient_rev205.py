from paired_bipartite_left_twin_quotient_v1 import (
    build_paired_left_twin_quotient,
    lift_twin_quotient_isomorphism,
)


def _relabel(edges, left_perm, right_perm):
    return {(left_perm[a], right_perm[b]) for a, b in edges}


def _relabel_palette(palette, perm):
    out = [None] * len(palette)
    for i, value in enumerate(palette):
        out[perm[i]] = value
    return tuple(out)


def _twin_instance():
    edges = {
        (0, 0), (0, 1),
        (1, 0), (1, 1),
        (2, 1), (2, 2),
        (3, 1), (3, 2),
    }
    left_colors = ("a", "a", "b", "b")
    right_colors = ("x", "y", "z")
    return edges, left_colors, right_colors


def test_paired_twin_quotient_strictly_reduces_and_lifts_exactly():
    source_edges, source_left, source_right = _twin_instance()
    left_perm = (2, 0, 3, 1)
    right_perm = (2, 0, 1)
    target_edges = _relabel(source_edges, left_perm, right_perm)
    target_left = _relabel_palette(source_left, left_perm)
    target_right = _relabel_palette(source_right, right_perm)

    got = build_paired_left_twin_quotient(
        4, 3,
        source_edges, target_edges,
        source_left_colors=source_left,
        target_left_colors=target_left,
        source_right_colors=source_right,
        target_right_colors=target_right,
    )
    assert got.status == "paired_left_twin_quotient_reduction"
    assert got.quotient_reduction_complete and got.exact and not got.exact_empty
    assert len(got.source.class_members) == len(got.target.class_members) == 2
    assert got.source.strict_left_reduction and got.target.strict_left_reduction

    target_class_of = {
        vertex: index
        for index, cell in enumerate(got.target.class_members)
        for vertex in cell
    }
    qmap = tuple(target_class_of[left_perm[cell[0]]] for cell in got.source.class_members)
    lifted = lift_twin_quotient_isomorphism(got.source, got.target, qmap, right_perm)
    assert lifted.status == "lifted_twin_quotient_isomorphism"
    assert lifted.exact
    assert {(lifted.left_map[a], lifted.right_map[b]) for a, b in source_edges} == target_edges
    assert all(source_left[a] == target_left[lifted.left_map[a]] for a in range(4))
    assert all(source_right[b] == target_right[lifted.right_map[b]] for b in range(3))


def test_twin_descriptor_inventory_mismatch_is_exact_empty():
    source_edges, source_left, source_right = _twin_instance()
    target_left = ("a", "a", "b", "c")
    got = build_paired_left_twin_quotient(
        4, 3,
        source_edges, source_edges,
        source_left_colors=source_left,
        target_left_colors=target_left,
        source_right_colors=source_right,
        target_right_colors=source_right,
    )
    assert got.status == "exact_empty_left_twin_descriptor_inventory"
    assert got.exact_empty and got.exact


def test_right_color_inventory_mismatch_is_exact_empty():
    source_edges, source_left, source_right = _twin_instance()
    got = build_paired_left_twin_quotient(
        4, 3,
        source_edges, source_edges,
        source_left_colors=source_left,
        target_left_colors=source_left,
        source_right_colors=source_right,
        target_right_colors=("x", "y", "q"),
    )
    assert got.status == "exact_empty_right_color_inventory"
    assert got.exact_empty and got.exact


def test_twin_free_pair_has_no_strict_quotient_progress():
    edges = {(0, 0), (1, 1), (2, 2)}
    got = build_paired_left_twin_quotient(3, 3, edges, edges)
    assert got.status == "left_twin_quotient_no_progress"
    assert got.invariant_compatible and not got.exact_empty
    assert not got.quotient_reduction_complete
    assert got.exact


def test_invalid_quotient_map_is_rejected_before_lift():
    source_edges, source_left, source_right = _twin_instance()
    got = build_paired_left_twin_quotient(
        4, 3,
        source_edges, source_edges,
        source_left_colors=source_left,
        target_left_colors=source_left,
        source_right_colors=source_right,
        target_right_colors=source_right,
    )
    lifted = lift_twin_quotient_isomorphism(got.source, got.target, (0, 0), (0, 1, 2))
    assert lifted.status == "invalid_quotient_left_permutation"
    assert not lifted.exact
