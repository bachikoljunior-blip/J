from paired_bipartite_large_relation_twin_restriction_v1 import (
    certify_paired_large_relation_twin_restriction,
)


def _orbit_design_incidence():
    # Right points 0..3 are symmetric; point 4 is distinguished only at pair level.
    # Left blocks are the S4-orbits of types (1,0) and (3,1): four singleton
    # ordinary blocks and four {special + three ordinary} blocks. Every right
    # point has degree 4, while ordinary/ordinary pair codegree is 2 and
    # ordinary/special pair codegree is 3. All eight left neighborhoods are distinct.
    edges = set()
    for i in range(4):
        edges.add((i, i))
    ordinary = set(range(4))
    for i in range(4):
        row = 4 + i
        for b in (ordinary - {i}) | {4}:
            edges.add((row, b))
    return edges


def _relabel(edges, left_perm, right_perm):
    return {(left_perm[a], right_perm[b]) for a, b in edges}


def _cycle_incidence():
    return {
        (0, 0), (1, 0),
        (1, 1), (2, 1),
        (2, 2), (3, 2),
        (3, 3), (0, 3),
    }


def test_large_relation_twin_class_reconnects_to_exact_right_restriction():
    source = _orbit_design_incidence()
    target = _relabel(
        source,
        (6, 0, 5, 2, 7, 1, 4, 3),
        (3, 4, 1, 0, 2),
    )
    got = certify_paired_large_relation_twin_restriction(
        8,
        5,
        source,
        target,
        relation_alpha=0.75,
        restriction_alpha=0.75,
    )
    assert got.status == "certified_paired_large_relation_twin_restriction"
    assert got.dominant_twin_size == 4
    assert got.selected_part_index == 1
    assert got.selected_part_size == 1
    assert got.provenance_verified and got.restriction_pair_complete
    assert got.exact and not got.exact_empty
    assert not got.source_symmetry.design_gate_certified
    assert got.source_restriction.selected_alpha_shrink


def test_design_gate_success_redirects_to_twl_design_path():
    cycle = _cycle_incidence()
    got = certify_paired_large_relation_twin_restriction(
        4,
        4,
        cycle,
        cycle,
        relation_alpha=0.75,
    )
    assert got.status == "design_gate_available_not_large_twin_residual"
    assert got.provenance_verified
    assert got.source_symmetry.design_gate_certified
    assert not got.restriction_pair_complete


def test_large_twin_partition_fails_closed_when_full_left_side_has_twins():
    source = {(a, b) for b in range(4) for a in (0, 1)} | {(2, 4), (3, 4)}
    got = certify_paired_large_relation_twin_restriction(
        4,
        5,
        source,
        source,
        relation_alpha=0.75,
    )
    assert got.status == "large_twin_partition_restriction_no_progress"
    assert got.provenance_verified
    assert got.source_restriction.status == "reduce_part2_requires_twin_free_left"
    assert not got.restriction_pair_complete


def test_relation_inventory_mismatch_remains_exact_empty():
    source = {(a, b) for b in range(4) for a in (0, 1)} | {(2, 4), (3, 4)}
    target = {(a, b) for b in range(5) for a in (0, 1)}
    got = certify_paired_large_relation_twin_restriction(
        4,
        5,
        source,
        target,
        relation_alpha=0.75,
    )
    assert got.status == "exact_empty_right_relation_invariant"
    assert got.exact_empty and got.exact
