from bipartite_split_or_johnson_gate_v1 import certify_bipartite_split_or_johnson_gate


def test_semiregular_three_block_incidence_certifies_bipartite_soj_gate():
    # Six left points are paired onto three right points. Largest twin class = 2,
    # so left relative symmetry defect is 4/6; |V2|/|V1| = 1/2.
    edges = {(0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (5, 2)}
    got = certify_bipartite_split_or_johnson_gate(6, 3, edges, alpha=0.75)
    assert got.status == "certified_bipartite_split_or_johnson_input_gate"
    assert got.theorem_input_gate
    assert got.part_size_gate and got.left_symmetry_defect_gate
    assert got.semiregular
    assert got.left_largest_twin_class == 2
    assert got.left_relative_symmetry_defect == 4 / 6


def test_large_left_twin_class_fails_defect_gate_without_claiming_progress():
    # Five identical left neighborhoods form a 5/6 twin class: defect 1/6 < 1/4.
    edges = {(a, 0) for a in range(5)} | {(5, 1)}
    got = certify_bipartite_split_or_johnson_gate(6, 3, edges, alpha=0.75)
    assert got.part_size_gate
    assert not got.left_symmetry_defect_gate
    assert not got.theorem_input_gate
    assert got.status == "bipartite_split_or_johnson_input_gate_not_met"


def test_equal_parts_fail_small_part_gate_even_with_zero_twins():
    edges = {(0, 0), (1, 1), (2, 2), (3, 3)}
    got = certify_bipartite_split_or_johnson_gate(4, 4, edges, alpha=0.75)
    assert not got.part_size_gate
    assert got.left_symmetry_defect_gate
    assert not got.theorem_input_gate


def test_bipartite_complement_preserves_twin_classes_and_normalizes_density():
    sparse = {(0, 0), (1, 0), (2, 1), (3, 1), (4, 2), (5, 2)}
    dense = {(a, b) for a in range(6) for b in range(3)} - sparse
    a = certify_bipartite_split_or_johnson_gate(6, 3, sparse, alpha=0.75)
    b = certify_bipartite_split_or_johnson_gate(6, 3, dense, alpha=0.75)
    assert not a.complemented
    assert b.complemented
    assert a.left_twin_classes == b.left_twin_classes
    assert a.right_twin_classes == b.right_twin_classes
    assert a.edge_count == b.edge_count == len(sparse)
    assert a.theorem_input_gate == b.theorem_input_gate
