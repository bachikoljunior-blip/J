from itertools import combinations

from colored_subset_exact_twl_design_v1 import (
    find_exact_twl_design_witness_family,
    paired_exact_twl_design_witness_families,
)


def _fano():
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
    return v, k, coords, lines, tuple(int(S in lines) for S in coords)


def test_fano_3wl_is_fail_closed_outside_extended_design_parameter_gate():
    v, k, _coords, _lines, colors = _fano()
    got = find_exact_twl_design_witness_family(
        v, k, colors,
        max_states=100,
        max_tuple_states=1000,
        max_rounds=32,
        max_work_units=30_000_000,
    )
    assert got.status == "undetermined_twl_design_theorem_parameter_gate"
    assert not got.theorem_parameter_gate and not got.exact


def test_prime_cycle11_exact_2wl_certifies_upcc_at_empty_individualization():
    v, k = 11, 2
    edges = {tuple(sorted((i, (i + 1) % v))) for i in range(v)}
    coords = tuple(combinations(range(v), k))
    colors = tuple(int(S in edges) for S in coords)
    got = find_exact_twl_design_witness_family(
        v, k, colors, max_tuple_states=200, max_rounds=16, max_work_units=1_000_000
    )
    assert got.status == "certified_exact_twl_design_witness_family"
    assert got.minimal_individualization_length == 0
    assert len(got.witness_outcomes) == 1
    outcome = got.witness_outcomes[0]
    assert outcome.status == "certified_twl_upcc"
    assert outcome.two_skeleton_rank == 6
    assert len(outcome.dominant_cell) == v


def test_cycle8_exact_2wl_uses_imprimitive_split():
    v, k = 8, 2
    edges = {tuple(sorted((i, (i + 1) % v))) for i in range(v)}
    coords = tuple(combinations(range(v), k))
    colors = tuple(int(S in edges) for S in coords)
    got = find_exact_twl_design_witness_family(
        v, k, colors, max_tuple_states=100, max_rounds=16, max_work_units=2_000_000
    )
    assert got.status == "certified_exact_twl_design_witness_family"
    outcome = got.witness_outcomes[0]
    assert outcome.status == "certified_twl_imprimitive_alpha_partition"
    assert sorted(map(len, outcome.output_partition)) == [2, 2, 2, 2]
    assert sorted(map(len, outcome.constituent_components)) == [2, 2, 2, 2]


def test_paired_fano_family_is_fail_closed_before_relabeling_comparison():
    v, k, coords, lines, source = _fano()
    image = (2, 0, 4, 1, 6, 3, 5)
    inverse = {image[x]: x for x in range(v)}
    target = tuple(
        int(tuple(sorted(inverse[x] for x in S)) in lines)
        for S in coords
    )
    got = paired_exact_twl_design_witness_families(
        v, k, source, target,
        max_states=100,
        max_tuple_states=1000,
        max_rounds=32,
        max_work_units=60_000_000,
    )
    assert got.status == "undetermined_paired_exact_twl_design_family"
    assert not got.invariant_compatible and not got.complete and not got.exact_empty
    assert not got.source.theorem_parameter_gate
    assert not got.target.theorem_parameter_gate


def test_homogeneous_relation_and_resource_cap_fail_closed():
    v, k = 12, 3
    homogeneous = tuple(0 for _ in combinations(range(v), k))
    closed = find_exact_twl_design_witness_family(v, k, homogeneous)
    assert closed.status == "undetermined_twl_design_symmetry_defect_gate"
    assert not closed.exact

    fv, fk = 11, 2
    edges = {tuple(sorted((i, (i + 1) % fv))) for i in range(fv)}
    fano = tuple(int(S in edges) for S in combinations(range(fv), fk))
    capped = find_exact_twl_design_witness_family(
        fv, fk, fano, max_tuple_states=100
    )
    assert capped.status == "undetermined_twl_design_tuple_state_cap"
    assert not capped.exact
