from itertools import combinations

from colored_subset_design_witness_v1 import (
    _incidence_two_wl,
    find_colored_subset_design_witness_family,
)


def _fano_colors():
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
    return v, t, coords, tuple(int(S in lines) for S in coords)


def _relabel_colors(v, t, colors, q):
    coords = tuple(combinations(range(v), t))
    index = {S: i for i, S in enumerate(coords)}
    out = [None] * len(coords)
    for i, S in enumerate(coords):
        image = tuple(sorted(q[x] for x in S))
        out[index[image]] = colors[i]
    return tuple(out)


def test_homogeneous_relation_fails_exact_symmetry_defect_gate():
    v, t = 8, 3
    colors = tuple(0 for _ in combinations(range(v), t))
    got = find_colored_subset_design_witness_family(v, t, colors)
    assert got.status == "undetermined_design_symmetry_defect_gate"
    assert got.theorem_parameter_gate
    assert not got.symmetry_defect_gate
    assert not got.exact


def test_incidence_two_wl_stops_when_partition_stabilizes_even_if_color_ids_renumber():
    v, t = 8, 3
    colors = tuple(int(0 in S) for S in combinations(range(v), t))
    got = _incidence_two_wl(v, t, colors, (), alpha=0.9, max_rounds=32)
    assert got.status != "undetermined_wl_round_limit"
    assert got.refinement_rounds < 32


def test_distinguished_point_relation_has_zero_length_design_witness_family():
    v, t = 8, 3
    colors = tuple(int(0 in S) for S in combinations(range(v), t))
    got = find_colored_subset_design_witness_family(v, t, colors, max_wl_rounds=256)
    assert got.status == "certified_design_witness_family"
    assert got.exact
    assert got.minimal_individualization_length == 0
    assert got.witness_tuples == ((),)
    assert got.witness_kinds == ("certified_alpha_coloring",)


def test_fano_design_requires_and_finds_single_point_individualization():
    v, t, _coords, colors = _fano_colors()
    got = find_colored_subset_design_witness_family(v, t, colors, max_wl_rounds=256)
    assert got.status == "certified_design_witness_family"
    assert got.exact and got.symmetry_defect_gate
    assert got.minimal_individualization_length == 1
    assert set(got.witness_tuples) == {(u,) for u in range(v)}
    assert set(got.witness_kinds) <= {
        "certified_alpha_coloring",
        "certified_dominant_nonclique_coherent_fiber",
    }


def test_complete_minimal_witness_family_is_equivariant_under_relabeling():
    v, t, _coords, colors = _fano_colors()
    q = (3, 5, 1, 6, 0, 4, 2)
    relabeled = _relabel_colors(v, t, colors, q)
    base = find_colored_subset_design_witness_family(v, t, colors, max_wl_rounds=256)
    moved = find_colored_subset_design_witness_family(v, t, relabeled, max_wl_rounds=256)
    assert base.status == moved.status == "certified_design_witness_family"
    assert base.minimal_individualization_length == moved.minimal_individualization_length
    assert {tuple(q[x] for x in T) for T in base.witness_tuples} == set(moved.witness_tuples)


def test_incomplete_individualization_level_fails_closed_before_partial_family():
    v, t, _coords, colors = _fano_colors()
    got = find_colored_subset_design_witness_family(
        v, t, colors,
        max_states=1,
        max_wl_rounds=256,
    )
    assert got.status == "undetermined_design_individualization_state_limit"
    assert got.states_checked == 1
    assert not got.exact
    assert got.witness_tuples == ()
