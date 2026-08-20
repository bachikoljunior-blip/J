from itertools import permutations

import pytest

from paired_bipartite_higher_arity_right_relation_v1 import (
    certify_paired_higher_arity_right_relation_provenance,
    derive_canonical_higher_arity_right_relation,
)


def _relabel(edges, left_perm, right_perm):
    return {(left_perm[a], right_perm[b]) for a, b in edges}


def _cycle_incidence():
    return {
        (0, 0), (1, 0),
        (1, 1), (2, 1),
        (2, 2), (3, 2),
        (3, 3), (0, 3),
    }


def _fano_incidence():
    lines = (
        (0, 1, 2),
        (0, 3, 4),
        (0, 5, 6),
        (1, 3, 5),
        (1, 4, 6),
        (2, 3, 6),
        (2, 4, 5),
    )
    return {(point, line) for line, block in enumerate(lines) for point in block}


def test_pair_relation_breaks_homogeneous_degree_residual_under_all_4_by_4_relabelings():
    source = _cycle_incidence()
    base = derive_canonical_higher_arity_right_relation(4, 4, source)
    assert base.status == "canonical_higher_arity_right_relation"
    assert base.selected_arity == 2
    assert base.relation_nonconstant

    for left_perm in permutations(range(4)):
        for right_perm in permutations(range(4)):
            target = _relabel(source, left_perm, right_perm)
            got = certify_paired_higher_arity_right_relation_provenance(4, 4, source, target)
            assert got.status == "paired_higher_arity_right_relation_provenance"
            assert got.selected_arity == 2
            assert got.provenance_verified
            assert got.source_relation.relation_inventory == got.target_relation.relation_inventory


def test_fano_lines_need_arity_three_after_homogeneous_pair_relation():
    edges = _fano_incidence()
    got = derive_canonical_higher_arity_right_relation(7, 7, edges)
    assert got.status == "canonical_higher_arity_right_relation"
    assert got.tested_arities == (2, 3)
    assert got.selected_arity == 3
    assert len(dict(got.arity_relation_inventories)[2]) == 1
    assert len(got.relation_inventory) > 1


def test_exact_higher_arity_inventory_mismatch_rejects_nonisomorphism():
    source = _cycle_incidence()
    target = {
        (0, 0), (1, 0),
        (0, 1), (1, 1),
        (2, 2), (3, 2),
        (2, 3), (3, 3),
    }
    got = certify_paired_higher_arity_right_relation_provenance(4, 4, source, target)
    assert got.status == "higher_arity_relation_inventory_mismatch"
    assert got.selected_arity == 2
    assert not got.provenance_verified
    assert got.exact


def test_fully_homogeneous_incidence_fails_closed():
    complete = {(a, b) for a in range(4) for b in range(4)}
    got = certify_paired_higher_arity_right_relation_provenance(4, 4, complete, complete)
    assert got.status == "higher_arity_right_relation_no_progress"
    assert got.provenance_verified
    assert got.selected_arity is None
    assert got.source_relation.tested_arities == (2,)


def test_first_order_progress_is_not_reclassified_as_higher_arity():
    edges = {(0, 0), (0, 1), (1, 2), (0, 3), (1, 3)}
    got = derive_canonical_higher_arity_right_relation(2, 4, edges)
    assert got.status == "first_order_right_partition_available"
    assert got.selected_arity is None


def test_subset_enumeration_cap_fails_closed():
    complete = {(a, b) for a in range(3) for b in range(20)}
    got = derive_canonical_higher_arity_right_relation(
        3,
        20,
        complete,
        max_arity=2,
        max_relation_subsets=100,
    )
    assert got.status == "higher_arity_relation_test_cap_exceeded"
    assert got.tested_arities == ()
    assert got.tested_subset_count == 0


def test_opaque_colors_are_rejected():
    class Opaque:
        pass

    with pytest.raises(TypeError):
        derive_canonical_higher_arity_right_relation(
            2,
            3,
            {(0, 0), (1, 1)},
            right_colors=(Opaque(), Opaque(), Opaque()),
        )
