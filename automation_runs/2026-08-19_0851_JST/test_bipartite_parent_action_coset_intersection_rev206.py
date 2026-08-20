from __future__ import annotations

from itertools import permutations

from bipartite_parent_action_coset_intersection_v1 import (
    intersect_parent_bipartite_string_through_right_alignment,
)
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain


LEFT = (0, 1, 2)
RIGHT = (3, 4, 5)


def _embed_diagonal(local):
    local = tuple(local)
    return tuple(local[i] for i in range(3)) + tuple(3 + local[i] for i in range(3))


def _diagonal_s3():
    cycle = _embed_diagonal((1, 2, 0))
    swap = _embed_diagonal((1, 0, 2))
    return schreier_stabilizer_chain([cycle, swap])


def _right_images(parent_group):
    index = {x: i for i, x in enumerate(RIGHT)}
    return tuple(
        tuple(index[g[x]] for x in RIGHT)
        for g in parent_group.original_generators
    )


def _right_group(parent_group):
    images = _right_images(parent_group)
    return images, schreier_stabilizer_chain(images)


def _map_edges(edges, local):
    local = tuple(local)
    return {(local[a], local[b]) for a, b in edges}


def _maps_colored_bipartite(source_edges, target_edges, p, source_left_colors=None, target_left_colors=None,
                            source_right_colors=None, target_right_colors=None):
    local = tuple(p[i] for i in range(3))
    mapped = _map_edges(source_edges, local)
    if mapped != set(target_edges):
        return False
    if source_left_colors is not None:
        for a in range(3):
            if source_left_colors[a] != target_left_colors[local[a]]:
                return False
    if source_right_colors is not None:
        for b in range(3):
            if source_right_colors[b] != target_right_colors[local[b]]:
                return False
    return True


def test_exact_parent_coset_matches_direct_diagonal_s3_enumeration():
    parent = _diagonal_s3()
    right_images, right_group = _right_group(parent)
    source = {(0, 0), (0, 1), (1, 2), (2, 0)}
    relabel = (1, 2, 0)
    target = _map_edges(source, relabel)

    got = intersect_parent_bipartite_string_through_right_alignment(
        parent,
        right_images,
        RightCoset(right_group, identity(3)),
        LEFT,
        RIGHT,
        source,
        target,
        max_auxiliary_degree=20,
        max_image_group_order=64,
    )
    assert got.status == "exact_parent_bipartite_coset_intersection"
    assert got.exact and not got.exact_empty
    assert got.coset is not None
    assert got.parent_action_coupling_preserved
    assert got.right_alignment_preimage_verified

    all_parent = tuple(_embed_diagonal(p) for p in permutations(range(3)))
    expected = {
        p for p in all_parent
        if _maps_colored_bipartite(source, target, p)
    }
    actual = {p for p in all_parent if got.coset.contains(p)}
    assert actual == expected
    assert _embed_diagonal(relabel) in actual


def test_right_only_alignment_is_rejected_when_parent_action_is_diagonal():
    parent = _diagonal_s3()
    right_images, right_group = _right_group(parent)
    # Independent left/right symmetry could send (0,0) to (0,1) by fixing the
    # left side and swapping right 0/1.  The actual parent action is diagonal,
    # so no allowed parent permutation does this.
    source = {(0, 0)}
    target = {(0, 1)}
    got = intersect_parent_bipartite_string_through_right_alignment(
        parent,
        right_images,
        RightCoset(right_group, identity(3)),
        LEFT,
        RIGHT,
        source,
        target,
        max_auxiliary_degree=20,
        max_image_group_order=64,
    )
    assert got.status == "exact_empty_parent_bipartite_candidate"
    assert got.exact and got.exact_empty
    assert got.coset is None


def test_vertex_colors_are_part_of_the_exact_coupled_string():
    parent = _diagonal_s3()
    right_images, right_group = _right_group(parent)
    source = {(0, 0), (1, 1), (2, 2)}
    target = set(source)
    left_colors = ("red", "blue", "blue")
    right_colors = ("x", "y", "y")
    got = intersect_parent_bipartite_string_through_right_alignment(
        parent,
        right_images,
        RightCoset(right_group, identity(3)),
        LEFT,
        RIGHT,
        source,
        target,
        source_left_colors=left_colors,
        target_left_colors=left_colors,
        source_right_colors=right_colors,
        target_right_colors=right_colors,
        max_auxiliary_degree=20,
        max_image_group_order=64,
    )
    assert got.status == "exact_parent_bipartite_coset_intersection"
    assert got.coset is not None

    all_parent = tuple(_embed_diagonal(p) for p in permutations(range(3)))
    expected = {
        p for p in all_parent
        if _maps_colored_bipartite(
            source, target, p,
            left_colors, left_colors,
            right_colors, right_colors,
        )
    }
    actual = {p for p in all_parent if got.coset.contains(p)}
    assert actual == expected
    assert len(actual) == 2


def test_right_candidate_restriction_is_respected_inside_parent_preimage():
    parent = _diagonal_s3()
    right_images, right_group = _right_group(parent)
    identity_right = schreier_stabilizer_chain([identity(3)])
    right_candidate = RightCoset(identity_right, (1, 2, 0))
    source = {(0, 0), (1, 1), (2, 2)}
    target = _map_edges(source, (1, 2, 0))

    got = intersect_parent_bipartite_string_through_right_alignment(
        parent,
        right_images,
        right_candidate,
        LEFT,
        RIGHT,
        source,
        target,
        max_auxiliary_degree=20,
        max_image_group_order=64,
    )
    assert got.status == "exact_parent_bipartite_coset_intersection"
    assert got.coset is not None
    expected = _embed_diagonal((1, 2, 0))
    assert got.coset.subgroup.order == 1
    assert got.coset.contains(expected)
    assert not got.coset.contains(identity(6))


def test_auxiliary_degree_cap_fails_closed_not_empty():
    parent = _diagonal_s3()
    right_images, right_group = _right_group(parent)
    got = intersect_parent_bipartite_string_through_right_alignment(
        parent,
        right_images,
        RightCoset(right_group, identity(3)),
        LEFT,
        RIGHT,
        {(0, 0)},
        {(0, 0)},
        max_auxiliary_degree=14,
        max_image_group_order=64,
    )
    assert got.status == "undetermined_parent_bipartite_auxiliary_degree_limit"
    assert not got.exact and not got.exact_empty
    assert got.coset is None


def test_invalid_parent_right_generator_pairing_is_rejected_not_fabricated():
    parent = _diagonal_s3()
    right_images, right_group = _right_group(parent)
    bad_images = tuple(reversed(right_images))
    try:
        intersect_parent_bipartite_string_through_right_alignment(
            parent,
            bad_images,
            RightCoset(right_group, identity(3)),
            LEFT,
            RIGHT,
            {(0, 0)},
            {(0, 0)},
            max_auxiliary_degree=20,
            max_image_group_order=64,
        )
    except ValueError as exc:
        assert "homomorphism" in str(exc) or "paired" in str(exc)
    else:
        raise AssertionError("invalid generator pairing must not be accepted as parent provenance")
