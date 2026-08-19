from itertools import combinations

from colored_subset_symmetry_defect_v1 import exact_colored_subset_symmetry_defect


def test_complete_relation_has_zero_symmetry_defect_and_fails_gate():
    v, t = 8, 3
    colors = tuple(0 for _ in combinations(range(v), t))
    got = exact_colored_subset_symmetry_defect(v, t, colors, alpha=0.9)
    assert got.largest_symmetric_class == v
    assert got.defect == 0
    assert not got.design_gate_certified
    assert got.twin_classes == (tuple(range(v)),)


def test_distinguished_point_relation_has_exact_one_point_defect_and_passes_point-nine_gate():
    v, t = 8, 3
    colors = tuple(int(0 in S) for S in combinations(range(v), t))
    got = exact_colored_subset_symmetry_defect(v, t, colors, alpha=0.9)
    assert got.largest_symmetric_class == 7
    assert got.defect == 1
    assert got.design_gate_certified
    assert sorted(map(len, got.twin_classes)) == [1, 7]


def test_fano_plane_is_codegree_homogeneous_but_has_large_exact_symmetry_defect():
    # The Fano plane is a 2-(7,3,1) design: point degrees and pair codegrees are
    # homogeneous, so simple incidence/codegree descent does not split it.  Yet no
    # transposition preserves the line set, giving singleton twin classes and an
    # exact symmetry-defect witness for the Design Lemma gate.
    v, t = 7, 3
    lines = {
        (0, 1, 2),
        (0, 3, 4),
        (0, 5, 6),
        (1, 3, 5),
        (1, 4, 6),
        (2, 3, 6),
        (2, 4, 5),
    }
    coords = tuple(combinations(range(v), t))
    colors = tuple(int(S in lines) for S in coords)
    got = exact_colored_subset_symmetry_defect(v, t, colors, alpha=0.9)
    assert got.largest_symmetric_class == 1
    assert got.defect == 6
    assert got.relative_defect == 6 / 7
    assert got.design_gate_certified
    assert all(len(C) == 1 for C in got.twin_classes)
