from itertools import combinations

from correlated_replacement_twl_v1 import (
    paired_individualization_twl_family,
    stable_correlated_replacement_twl,
)


def _fano_colors():
    v, k = 7, 3
    lines = {
        (0, 1, 2),
        (0, 3, 4),
        (0, 5, 6),
        (1, 3, 5),
        (1, 4, 6),
        (2, 3, 6),
        (2, 4, 5),
    }
    coords = tuple(combinations(range(v), k))
    return v, k, coords, tuple(int(S in lines) for S in coords), lines


def test_exact_correlated_replacement_twl_stabilizes_and_individualizes():
    v, k, _coords, colors, _lines = _fano_colors()
    base = stable_correlated_replacement_twl(v, k, colors, max_work_units=20_000_000)
    marked = stable_correlated_replacement_twl(
        v, k, colors, individualized=(0,), max_work_units=20_000_000
    )
    assert base.exact_stable and marked.exact_stable
    assert base.point_cells == (tuple(range(v)),)
    assert sorted(map(len, marked.point_cells)) == [1, 6]
    assert marked.work_units >= marked.tuple_states


def test_full_family_is_equivariant_under_ground_relabeling_and_finds_alpha_split():
    v, k, coords, colors, lines = _fano_colors()
    image = (2, 0, 4, 1, 6, 3, 5)
    inverse = {image[x]: x for x in range(v)}
    target = tuple(
        int(tuple(sorted(inverse[x] for x in S)) in lines) for S in coords
    )
    got = paired_individualization_twl_family(
        v,
        k,
        colors,
        target,
        alpha=0.9,
        max_family_size=100,
        max_tuple_states=1000,
        max_work_units=30_000_000,
    )
    assert got.status == "verified_paired_twl_alpha_partition_family"
    assert got.family_size == 1 + 7 + 7 * 6
    assert got.invariant_compatible and got.alpha_partition_certified
    assert got.source_alpha_witnesses == got.target_alpha_witnesses == 49


def test_family_inventory_mismatch_is_exact_empty_invariant():
    v, k = 5, 2
    coords = tuple(combinations(range(v), k))
    source = tuple(int(0 in S) for S in coords)
    target = tuple(int(S in {(0, 1), (2, 3)}) for S in coords)
    got = paired_individualization_twl_family(
        v,
        k,
        source,
        target,
        max_family_size=10,
        max_tuple_states=100,
        max_work_units=2_000_000,
    )
    assert got.status == "exact_empty_paired_twl_family_invariant"
    assert got.exact_empty
    assert not got.invariant_compatible


def test_resource_caps_fail_closed_without_structural_claim():
    v, k, _coords, colors, _lines = _fano_colors()
    got = paired_individualization_twl_family(
        v,
        k,
        colors,
        colors,
        max_family_size=10,
    )
    assert got.status == "paired_twl_resource_gate_closed"
    assert not got.exact_empty
    assert not got.alpha_partition_certified
