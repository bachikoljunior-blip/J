from bipartite_twin_quotient_refinement_v1 import refine_bipartite_twin_quotient_pair


def _source_matching_blocks():
    return {(0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (5, 2)}


def _target_permuted_matching_blocks():
    # right colors below are (c,a,b): map source a-cell -> target vertices 4,5
    # through right vertex 1; source b-cell -> target 0,1 through right 2;
    # source c-cell -> target 2,3 through right 0.
    return {(4, 1), (5, 1), (0, 2), (1, 2), (2, 0), (3, 0)}


def test_joint_refinement_finds_unique_quotient_mapping_when_right_colors_anchor_cells():
    got = refine_bipartite_twin_quotient_pair(
        6,
        3,
        _source_matching_blocks(),
        _target_permuted_matching_blocks(),
        source_right_colors=("a", "b", "c"),
        target_right_colors=("c", "a", "b"),
    )
    assert got.status == "exact_unique_twin_quotient_mapping"
    assert got.unique_quotient_mapping
    assert got.exact and got.complete_for_quotient
    assert len(got.left_cell_pairing) == 3
    assert len(got.right_cell_pairing) == 3
    assert {tuple(sorted((len(got.source_left_cells[i]), len(got.target_left_cells[j])))) for i, j in got.left_cell_pairing} == {(2, 2)}


def test_regular_uncolored_matching_quotient_stays_ambiguous_without_arbitrary_choice():
    got = refine_bipartite_twin_quotient_pair(
        6,
        3,
        _source_matching_blocks(),
        _target_permuted_matching_blocks(),
    )
    assert got.status == "ambiguous_twin_quotient_refinement"
    assert not got.invariant_mismatch
    assert not got.unique_quotient_mapping
    assert got.exact and not got.complete_for_quotient
    assert got.left_cell_pairing == ()
    assert got.right_cell_pairing == ()


def test_joint_refinement_detects_exact_color_profile_mismatch():
    got = refine_bipartite_twin_quotient_pair(
        6,
        3,
        _source_matching_blocks(),
        _target_permuted_matching_blocks(),
        source_right_colors=("a", "b", "c"),
        target_right_colors=("a", "b", "b"),
    )
    assert got.status == "exact_twin_quotient_invariant_mismatch"
    assert got.invariant_mismatch
    assert got.exact and got.complete_for_quotient
    assert not got.unique_quotient_mapping


def test_dense_complement_normalization_preserves_unique_quotient_result():
    sparse_s = _source_matching_blocks()
    sparse_t = _target_permuted_matching_blocks()
    dense_s = {(a, b) for a in range(6) for b in range(3)} - sparse_s
    dense_t = {(a, b) for a in range(6) for b in range(3)} - sparse_t
    got = refine_bipartite_twin_quotient_pair(
        6,
        3,
        dense_s,
        dense_t,
        source_right_colors=("a", "b", "c"),
        target_right_colors=("c", "a", "b"),
    )
    assert got.status == "exact_unique_twin_quotient_mapping"
    assert got.unique_quotient_mapping
    assert got.exact and got.complete_for_quotient
