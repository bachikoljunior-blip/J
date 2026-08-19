from itertools import combinations

from design_lemma_symmetry_defect_bridge_rev186 import (
    paired_design_symmetry_defect_bridge,
)


def _fano_colors():
    lines = {
        (0, 1, 2), (0, 3, 4), (0, 5, 6),
        (1, 3, 5), (1, 4, 6), (2, 3, 6), (2, 4, 5),
    }
    return tuple(int(S in lines) for S in combinations(range(7), 3))


def test_fano_pair_certifies_only_exact_symmetry_defect_hypothesis():
    colors = _fano_colors()
    got = paired_design_symmetry_defect_bridge(7, 3, colors, colors, alpha=0.9)
    assert got.status == "design_lemma_symmetry_defect_hypothesis_certified"
    assert got.exact
    assert got.theorem_hypothesis_certified
    assert got.source.largest_symmetric_class == 1
    assert got.target.largest_symmetric_class == 1
    assert "conclusion remains a separate proof obligation" in got.reason


def test_complete_relation_fails_symmetry_defect_hypothesis_closed():
    colors = tuple(0 for _ in combinations(range(8), 3))
    got = paired_design_symmetry_defect_bridge(8, 3, colors, colors, alpha=0.9)
    assert got.status == "design_lemma_symmetry_defect_hypothesis_not_certified"
    assert not got.theorem_hypothesis_certified
    assert got.source.largest_symmetric_class == 8


def test_color_multiplicity_mismatch_is_exact_empty_invariant_gate():
    coords = tuple(combinations(range(7), 3))
    source = _fano_colors()
    target = tuple(0 for _ in coords)
    got = paired_design_symmetry_defect_bridge(7, 3, source, target, alpha=0.9)
    assert got.status == "relation_invariant_mismatch"
    assert not got.theorem_hypothesis_certified
