from itertools import combinations

from coherent_pair_refinement import coherent_refine_pair_relation
from paired_individualized_subset_twl_v1 import (
    paired_individualized_complete_subset_twl,
)


def fano_lines():
    return {
        (0, 1, 2),
        (0, 3, 4),
        (0, 5, 6),
        (1, 3, 5),
        (1, 4, 6),
        (2, 3, 6),
        (2, 4, 5),
    }


def relabel_subset_colors(v, t, colors, permutation):
    coords = tuple(combinations(range(v), t))
    index = {subset: i for i, subset in enumerate(coords)}
    target = [None] * len(coords)
    for i, subset in enumerate(coords):
        image = tuple(sorted(permutation[x] for x in subset))
        target[index[image]] = colors[i]
    return tuple(target)


def cells_by_color(colors, cells):
    return {colors[cell[0]]: set(cell) for cell in cells}


def test_t2_special_case_matches_existing_coherent_refinement_point_shape():
    v = 5
    coords = tuple(combinations(range(v), 2))
    # Path P5: stable 2-WL has endpoint, near-endpoint, and center fibers.
    edges = {(0, 1), (1, 2), (2, 3), (3, 4)}
    colors = tuple(int(pair in edges) for pair in coords)
    got = paired_individualized_complete_subset_twl(v, 2, colors, colors)
    existing = coherent_refine_pair_relation(
        v, tuple((pair, colors[i]) for i, pair in enumerate(coords))
    )
    assert got.status == "certified_paired_individualized_twl_point_partition", got
    assert got.point_invariant_compatible and not got.exact_empty
    assert tuple(sorted(map(len, got.source_point_cells))) == tuple(
        sorted(map(len, existing.color_classes))
    ) == (1, 2, 2)


def test_fano_without_individualization_stays_homogeneous():
    coords = tuple(combinations(range(7), 3))
    lines = fano_lines()
    colors = tuple(int(subset in lines) for subset in coords)
    got = paired_individualized_complete_subset_twl(7, 3, colors, colors)
    assert got.status == "stable_paired_individualized_twl_relation", got
    assert got.point_invariant_compatible and not got.exact_empty
    assert not got.significant_point_partition
    assert tuple(map(len, got.source_point_cells)) == (7,)


def test_fano_one_paired_individualization_yields_alpha_bounded_partition():
    coords = tuple(combinations(range(7), 3))
    lines = fano_lines()
    colors = tuple(int(subset in lines) for subset in coords)
    got = paired_individualized_complete_subset_twl(
        7,
        3,
        colors,
        colors,
        source_individualized=(0,),
        target_individualized=(0,),
        max_class_fraction=0.9,
    )
    assert got.status == "certified_paired_individualized_twl_point_partition", got
    assert got.significant_point_partition
    assert tuple(sorted(map(len, got.source_point_cells))) == (1, 6)
    assert got.refinement_rounds >= 1
    assert got.tuple_state_count == 7**3


def test_joint_twl_is_equivariant_under_arbitrary_relabeling_with_paired_constants():
    v, t = 7, 3
    coords = tuple(combinations(range(v), t))
    lines = fano_lines()
    source = tuple(int(subset in lines) for subset in coords)
    permutation = (3, 0, 6, 2, 5, 1, 4)
    target = relabel_subset_colors(v, t, source, permutation)
    got = paired_individualized_complete_subset_twl(
        v,
        t,
        source,
        target,
        source_individualized=(0, 1),
        target_individualized=(permutation[0], permutation[1]),
    )
    assert got.point_invariant_compatible and not got.exact_empty, got
    assert got.significant_point_partition
    source_cells = cells_by_color(got.source_point_colors, got.source_point_cells)
    target_cells = cells_by_color(got.target_point_colors, got.target_point_cells)
    assert set(source_cells) == set(target_cells)
    for color, cell in source_cells.items():
        assert {permutation[x] for x in cell} == target_cells[color]


def test_relation_color_multiplicity_mismatch_is_exact_empty_before_twl():
    coords = tuple(combinations(range(6), 3))
    source = tuple(int(0 in subset) for subset in coords)
    target = (0,) * len(coords)
    got = paired_individualized_complete_subset_twl(6, 3, source, target)
    assert got.status == "exact_empty_twl_relation_color_multiplicity", got
    assert got.exact_empty
    assert not got.point_invariant_compatible


def test_tuple_state_cap_fails_closed_without_partial_colors():
    colors = (0,) * len(tuple(combinations(range(8), 4)))
    got = paired_individualized_complete_subset_twl(
        8, 4, colors, colors, max_tuple_states=4095
    )
    assert got.status == "undetermined_twl_tuple_state_cap", got
    assert got.tuple_state_count == 4096
    assert not got.exact_empty
    assert got.source_tuple_colors == ()
    assert got.target_tuple_colors == ()
