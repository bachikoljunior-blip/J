from __future__ import annotations

from itertools import combinations

import pytest

from bipartite_reduce_part2_by_color_v1 import reduce_part2_by_color_certificate


def test_selects_side_with_exact_exercise55_bound():
    # C0 creates classes of sizes 4 and 2: defect 1/3 passes the old alpha=3/4
    # threshold but violates Exercise 5.5's exact max-class bound 3.  C1 is
    # twin-free, so the corrected gate must select C1 rather than C0.
    edges = {
        (4, 0),
        (5, 0),
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 1), (3, 2),
        (4, 1), (4, 3),
        (5, 2), (5, 3),
    }
    got = reduce_part2_by_color_certificate(6, 4, edges, (0,), (1, 2, 3), alpha=0.75)
    assert got.status == "certified_reduce_part2_by_color"
    assert got.theorem_gate_verified
    assert got.part0_largest_left_twin_class == 4
    assert got.part0_relative_symmetry_defect >= 0.25
    assert not got.part0_exercise55_gate
    assert got.part1_exercise55_gate
    assert got.selected_part_index == 1
    assert got.selected_part == (1, 2, 3)


def test_smallest_eligible_side_is_selected_canonically():
    # Both restrictions meet Exercise 5.5; selecting the smaller eligible part
    # maximizes right-part descent, with input color order as the deterministic tie.
    edges = {
        (0, 0), (1, 0),
        (2, 1), (3, 1),
        (4, 2), (5, 2),
        (0, 3), (2, 3), (4, 3),
    }
    got = reduce_part2_by_color_certificate(6, 4, edges, (3,), (0, 1, 2), alpha=0.75)
    assert got.status == "certified_reduce_part2_by_color"
    assert got.part0_exercise55_gate and got.part1_exercise55_gate
    assert got.selected_part_index == 0
    assert got.selected_part == (3,)
    assert got.selected_alpha_shrink


def test_nontrivial_full_left_twins_fail_before_selection():
    edges = {(0, 0), (1, 0), (2, 1), (3, 1)}
    got = reduce_part2_by_color_certificate(4, 2, edges, (0,), (1,), alpha=0.75)
    assert got.status == "reduce_part2_requires_twin_free_left"
    assert not got.theorem_gate_verified
    assert got.selected_part_index is None


def test_empty_or_overlapping_right_partition_is_rejected():
    edges = {(0, 0), (1, 1), (2, 2)}
    with pytest.raises(ValueError, match="both be nonempty"):
        reduce_part2_by_color_certificate(3, 3, edges, (), (0, 1, 2))
    with pytest.raises(ValueError, match="disjoint cover"):
        reduce_part2_by_color_certificate(3, 3, edges, (0, 1), (1, 2))


def test_left_colors_are_part_of_exact_twin_relation():
    # Vertices 0 and 1 have the same full neighborhood but distinct input colors.
    edges = {(0, 0), (1, 0), (2, 1)}
    got = reduce_part2_by_color_certificate(
        3,
        2,
        edges,
        (0,),
        (1,),
        left_colors=("red", "blue", "red"),
    )
    assert got.status == "certified_reduce_part2_by_color"
    assert all(len(cell) == 1 for cell in got.full_left_twin_classes)


def test_exhaustive_exercise55_property_for_small_uncolored_graphs():
    # Exhaust all 2^(4*3)=4096 bipartite graphs and all proper ordered covers of V2.
    # Whenever the full left side is twin-free, the implementation must find at
    # least one restriction with max twin class <= ceil(|V1|/2), as Exercise 5.5 says.
    n1, n2 = 4, 3
    positions = [(a, b) for a in range(n1) for b in range(n2)]
    right = set(range(n2))
    proper_part0 = [set(c) for r in range(1, n2) for c in combinations(range(n2), r)]
    twin_free_cases = 0
    for mask in range(1 << len(positions)):
        edges = {positions[i] for i in range(len(positions)) if mask & (1 << i)}
        # Use one partition to cheaply determine whether the full graph is twin-free.
        probe = reduce_part2_by_color_certificate(n1, n2, edges, (0,), (1, 2))
        if probe.status == "reduce_part2_requires_twin_free_left":
            continue
        twin_free_cases += 1
        for C0 in proper_part0:
            C1 = right - C0
            got = reduce_part2_by_color_certificate(n1, n2, edges, C0, C1)
            assert got.status == "certified_reduce_part2_by_color"
            assert got.part0_exercise55_gate or got.part1_exercise55_gate
            assert got.selected_part
            assert len(got.selected_part) < n2
    assert twin_free_cases > 0
