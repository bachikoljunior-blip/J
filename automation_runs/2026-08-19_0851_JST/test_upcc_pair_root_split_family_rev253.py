from itertools import combinations, permutations

import upcc_pair_root_split_family_v1 as pair_root


def _petersen_relation():
    vertices = tuple(combinations(range(5), 2))
    edges = {
        (i, j)
        for i in range(10)
        for j in range(i + 1, 10)
        if set(vertices[i]).isdisjoint(vertices[j])
    }
    coords = tuple(combinations(range(10), 2))
    return tuple(int(pair in edges) for pair in coords)


def _solve(colors=None, **kwargs):
    return pair_root.certify_upcc_pair_root_split_family(
        10,
        2,
        _petersen_relation() if colors is None else colors,
        root_n=64,
        alpha=0.5,
        max_pair_branches=100,
        max_tuple_states=1_000,
        max_rounds=100,
        per_run_work_cap=1_000_000,
        max_total_work_units=100_000_000,
        **kwargs,
    )


def test_petersen_upcc_gets_complete_ordered_pair_root_split_family():
    got = _solve()
    assert got.status == "certified_complete_upcc_pair_root_split_family"
    assert got.design_status == "certified_twl_upcc"
    assert got.exact and got.complete and got.aux_shrink_certified
    assert got.branch_count == 90
    assert got.root_pairs[0] == (0, 1)
    assert got.root_pairs[-1] == (9, 8)
    assert len(set(got.root_pairs)) == 90
    assert set(got.branch_statuses) == {"certified_twl_alpha_coloring"}
    assert got.max_child_aux_size == 4
    assert got.used_work_units <= got.reserved_work_units


def test_complete_pair_family_is_relabeling_equivariant_by_profiles():
    colors = _petersen_relation()
    coords = tuple(combinations(range(10), 2))
    by_pair = dict(zip(coords, colors))
    permutation = (3, 9, 1, 7, 4, 0, 8, 2, 6, 5)
    relabeled = tuple(
        by_pair[tuple(sorted((permutation[a], permutation[b])))]
        for a, b in coords
    )
    a = _solve(colors)
    b = _solve(relabeled)
    assert a.status == b.status == "certified_complete_upcc_pair_root_split_family"
    profile_a = sorted((status, tuple(sorted(row))) for status, row in zip(a.branch_statuses, a.child_aux_sizes))
    profile_b = sorted((status, tuple(sorted(row))) for status, row in zip(b.branch_statuses, b.child_aux_sizes))
    assert profile_a == profile_b


def test_petersen_partitions_are_equivariant_under_all_s5_automorphisms():
    got = _solve()
    vertices = tuple(combinations(range(5), 2))
    index = {pair: i for i, pair in enumerate(vertices)}
    by_root = dict(zip(got.root_pairs, got.partitions))
    for ground_permutation in permutations(range(5)):
        image = tuple(
            index[tuple(sorted((ground_permutation[a], ground_permutation[b])))]
            for a, b in vertices
        )
        for (a, b), partition in by_root.items():
            mapped = {frozenset(image[x] for x in cell) for cell in partition}
            target = {frozenset(cell) for cell in by_root[(image[a], image[b])]}
            assert mapped == target


def test_branch_cap_rejects_before_any_twl_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("preflight rejection must happen before the base k-WL run")

    monkeypatch.setattr(pair_root, "stable_colored_subset_twl", forbidden)
    got = pair_root.certify_upcc_pair_root_split_family(
        10, 2, _petersen_relation(), root_n=64, alpha=0.5,
        max_pair_branches=89, max_tuple_states=1_000,
        per_run_work_cap=1_000_000, max_total_work_units=100_000_000,
    )
    assert got.status == "undetermined_upcc_pair_root_branch_cap"
    assert got.used_work_units == 0
    assert not got.exact and not got.complete


def test_total_work_cap_rejects_complete_cover_before_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("total reservation rejection must not execute k-WL")

    monkeypatch.setattr(pair_root, "stable_colored_subset_twl", forbidden)
    got = pair_root.certify_upcc_pair_root_split_family(
        10, 2, _petersen_relation(), root_n=64, alpha=0.5,
        max_pair_branches=100, max_tuple_states=1_000,
        per_run_work_cap=1_000_000, max_total_work_units=90_999_999,
    )
    assert got.status == "undetermined_upcc_pair_root_total_work_cap"
    assert got.reserved_work_units == 91_000_000
    assert got.used_work_units == 0


def test_rank_two_clique_is_not_promoted_to_pair_root_upcc_progress():
    clique = tuple(0 for _ in combinations(range(10), 2))
    got = _solve(clique)
    assert got.status == "not_full_ground_upcc_pair_root_leaf"
    assert got.design_status == "stable_twl_clique_continue"
    assert got.exact and not got.complete and not got.aux_shrink_certified


def test_invalid_relation_is_rejected_even_when_resource_preflight_would_close():
    try:
        pair_root.certify_upcc_pair_root_split_family(
            10, 2, (), root_n=64, alpha=0.5, max_pair_branches=1,
            max_tuple_states=1, per_run_work_cap=1,
            max_total_work_units=1,
        )
    except ValueError as exc:
        assert "one entry for every k-subset" in str(exc)
    else:
        raise AssertionError("malformed relation input must not be hidden by a resource-cap result")
