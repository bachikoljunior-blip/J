from __future__ import annotations

from itertools import permutations

import pytest

from paired_bipartite_right_partition_provenance_v1 import (
    certify_paired_right_partition_provenance,
    derive_canonical_right_partition,
)


def _relabel(edges, left_perm, right_perm):
    return {(left_perm[a], right_perm[b]) for a, b in edges}


def _relabel_palette(palette, perm):
    out = [None] * len(palette)
    for old, new in enumerate(perm):
        out[new] = palette[old]
    return tuple(out)


def _base_instance():
    edges = {
        (0, 0),
        (1, 0),
        (1, 1),
        (2, 1),
        (2, 2),
        (3, 2),
        (3, 3),
        (0, 3),
    }
    left_colors = ("a", "a", "b", "b")
    right_colors = ("x", "x", "y", "z")
    return edges, left_colors, right_colors


def test_relabelled_pair_has_complete_canonical_restriction_provenance():
    edges, left_colors, right_colors = _base_instance()
    left_perm = (2, 0, 3, 1)
    right_perm = (3, 1, 0, 2)
    target_edges = _relabel(edges, left_perm, right_perm)
    target_left = _relabel_palette(left_colors, left_perm)
    target_right = _relabel_palette(right_colors, right_perm)

    got = certify_paired_right_partition_provenance(
        4,
        4,
        edges,
        target_edges,
        source_left_colors=left_colors,
        target_left_colors=target_left,
        source_right_colors=right_colors,
        target_right_colors=target_right,
    )
    assert got.status == "paired_right_partition_provenance"
    assert got.provenance_verified and got.restriction_pair_complete
    assert got.source_partition.right_signature_inventory == got.target_partition.right_signature_inventory
    assert got.source_restriction.selected_part_index == got.target_restriction.selected_part_index
    assert got.selected_signature_inventory


def test_right_signature_inventory_mismatch_is_exact_nonisomorphism_invariant():
    edges, left_colors, right_colors = _base_instance()
    target_edges = set(edges)
    target_edges.remove((0, 0))
    got = certify_paired_right_partition_provenance(
        4,
        4,
        edges,
        target_edges,
        source_left_colors=left_colors,
        target_left_colors=left_colors,
        source_right_colors=right_colors,
        target_right_colors=right_colors,
    )
    assert got.status == "right_signature_inventory_mismatch"
    assert got.exact
    assert not got.restriction_pair_complete


def test_single_signature_class_fails_closed_without_higher_arity_claim():
    edges = {(a, b) for a in range(3) for b in range(3)}
    got = certify_paired_right_partition_provenance(3, 3, edges, edges)
    assert got.status == "canonical_right_partition_no_progress"
    assert got.provenance_verified
    assert not got.restriction_pair_complete


def test_unsupported_opaque_color_is_rejected():
    class Opaque:
        pass

    with pytest.raises(TypeError, match="canonical atoms"):
        derive_canonical_right_partition(2, 2, {(0, 0)}, left_colors=(Opaque(), Opaque()))


def test_all_relabelings_preserve_inventory_and_selected_signature_union():
    edges, left_colors, right_colors = _base_instance()
    source = derive_canonical_right_partition(
        4,
        4,
        edges,
        left_colors=left_colors,
        right_colors=right_colors,
    )
    assert source.status == "canonical_right_partition"

    # 4! x 4! = 576 exact relabelings.
    for lp in permutations(range(4)):
        for rp in permutations(range(4)):
            target_edges = _relabel(edges, lp, rp)
            got = certify_paired_right_partition_provenance(
                4,
                4,
                edges,
                target_edges,
                source_left_colors=left_colors,
                target_left_colors=_relabel_palette(left_colors, lp),
                source_right_colors=right_colors,
                target_right_colors=_relabel_palette(right_colors, rp),
            )
            assert got.status == "paired_right_partition_provenance"
            assert got.source_partition.right_signature_inventory == got.target_partition.right_signature_inventory
            assert got.source_restriction.selected_part_index == got.target_restriction.selected_part_index


def test_same_degree_signature_inventory_but_different_twin_invariants_is_exact_mismatch():
    # Both graphs have right-degree inventory 3x degree-1 and 1x degree-2, so the
    # degree/color provenance split agrees.  Their exact restricted left-twin
    # profiles differ, which an isomorphism preserving that canonical split cannot do.
    source_edges = {
        (0, 0), (0, 2), (0, 3), (1, 1), (2, 0),
    }
    target_edges = {
        (0, 1), (0, 3), (1, 1), (1, 2), (2, 0),
    }
    got = certify_paired_right_partition_provenance(
        4, 4, source_edges, target_edges
    )
    assert got.status == "paired_restriction_invariant_mismatch"
    assert got.exact
    assert not got.restriction_pair_complete
