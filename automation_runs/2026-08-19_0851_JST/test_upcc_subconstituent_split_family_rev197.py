from itertools import combinations

from upcc_subconstituent_split_family_v1 import certify_upcc_subconstituent_split_family


def _cycle_relation(v):
    edges = {tuple(sorted((i, (i + 1) % v))) for i in range(v)}
    coords = tuple(combinations(range(v), 2))
    return tuple(int(S in edges) for S in coords)


def test_cycle5_upcc_gets_complete_one_point_alpha_split_family():
    v, k = 5, 2
    got = certify_upcc_subconstituent_split_family(
        v,
        k,
        _cycle_relation(v),
        root_n=32,
        max_tuple_states=100,
        max_rounds=16,
        max_work_units=1_000_000,
    )
    assert got.status == "certified_complete_upcc_subconstituent_split_family"
    assert got.design_status == "certified_twl_upcc"
    assert got.exact and got.complete and got.aux_shrink_certified
    assert got.roots == tuple(range(v))
    assert got.branch_count == v
    assert all(sorted(row) == [1, 2, 2] for row in got.child_aux_sizes)
    assert got.max_child_aux_size == 2


def test_cycle5_relabeling_preserves_complete_branch_size_profiles():
    v, k = 5, 2
    colors = _cycle_relation(v)
    coords = tuple(combinations(range(v), k))
    color_by_set = dict(zip(coords, colors))
    p = (2, 4, 1, 3, 0)
    relabeled = tuple(
        color_by_set[tuple(sorted((p[a], p[b])))]
        for a, b in coords
    )
    a = certify_upcc_subconstituent_split_family(
        v, k, colors, root_n=32,
        max_tuple_states=100, max_rounds=16, max_work_units=1_000_000,
    )
    b = certify_upcc_subconstituent_split_family(
        v, k, relabeled, root_n=32,
        max_tuple_states=100, max_rounds=16, max_work_units=1_000_000,
    )
    assert a.status == b.status == "certified_complete_upcc_subconstituent_split_family"
    assert sorted(tuple(sorted(row)) for row in a.child_aux_sizes) == sorted(
        tuple(sorted(row)) for row in b.child_aux_sizes
    )


def test_homogeneous_pair_clique_is_not_misreported_as_upcc_progress():
    v, k = 6, 2
    colors = tuple(0 for _ in combinations(range(v), k))
    got = certify_upcc_subconstituent_split_family(
        v, k, colors, root_n=32,
        max_tuple_states=100, max_rounds=16, max_work_units=1_000_000,
    )
    assert got.status == "not_upcc_subconstituent_leaf"
    assert not got.aux_shrink_certified
    assert got.exact
    assert not got.complete


def test_state_cap_fails_closed_before_any_split_claim():
    v, k = 8, 3
    colors = tuple(0 for _ in combinations(range(v), k))
    got = certify_upcc_subconstituent_split_family(
        v, k, colors, root_n=64,
        max_tuple_states=100,
        max_rounds=8,
        max_work_units=100_000,
    )
    assert not got.aux_shrink_certified
    assert not got.complete
    assert not got.exact
