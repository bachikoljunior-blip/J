from __future__ import annotations

from collections import Counter
from itertools import combinations, permutations

from upcc_pair_root_split_family_v1 import certify_upcc_pair_root_split_family
from upcc_subconstituent_split_family_v1 import certify_upcc_subconstituent_split_family


def _rook_relation(side: int) -> tuple[int, ...]:
    vertices = tuple((row, col) for row in range(side) for col in range(side))
    edges = {
        (a, b)
        for a, (ra, ca) in enumerate(vertices)
        for b, (rb, cb) in enumerate(vertices)
        if a < b and (ra == rb or ca == cb)
    }
    return tuple(int(pair in edges) for pair in combinations(range(len(vertices)), 2))


def _relabel_pair_relation(colors: tuple[int, ...], permutation: tuple[int, ...]) -> tuple[int, ...]:
    vertex_count = len(permutation)
    coordinates = tuple(combinations(range(vertex_count), 2))
    color_by_pair = dict(zip(coordinates, colors))
    return tuple(
        color_by_pair[tuple(sorted((permutation[a], permutation[b])))]
        for a, b in coordinates
    )


def test_rook16_closes_after_one_root_family_fails_alpha_half():
    vertex_count = 16
    colors = _rook_relation(4)
    one_root = certify_upcc_subconstituent_split_family(
        vertex_count,
        2,
        colors,
        root_n=64,
        alpha=0.5,
        max_tuple_states=1000,
        max_rounds=8,
        max_work_units=2_000_000,
    )
    assert one_root.status == "upcc_subconstituent_not_alpha_shrinking"
    assert one_root.max_child_aux_size == 9
    assert not one_root.aux_shrink_certified

    got = certify_upcc_pair_root_split_family(
        vertex_count,
        2,
        colors,
        root_n=64,
        alpha=0.5,
        max_root_pairs=1000,
        max_tuple_states=1000,
        max_rounds=8,
        max_work_units=2_000_000,
        max_total_work_units=100_000_000,
    )
    assert got.status == "certified_complete_upcc_pair_root_split_family"
    assert got.base_design_status == "certified_twl_upcc"
    assert got.exact and got.complete and got.aux_shrink_certified
    assert got.complete_root_cover and got.equivariant_family
    assert got.branch_count == got.checked_root_pairs == 16 * 15
    assert got.root_pairs == tuple(permutations(range(vertex_count), 2))
    assert len(set(got.root_pairs)) == got.branch_count
    assert got.max_child_aux_size == 6
    assert all(max(row) <= 8 for row in got.child_aux_sizes)
    assert got.executed_work_units <= got.preflight_work_upper_bound


def test_relabeling_preserves_complete_pair_root_size_profile_multiset():
    vertex_count = 9
    colors = _rook_relation(3)
    permutation = (5, 2, 8, 0, 7, 4, 1, 6, 3)
    relabeled = _relabel_pair_relation(colors, permutation)

    common = dict(
        root_n=32,
        alpha=0.5,
        max_root_pairs=1000,
        max_tuple_states=1000,
        max_rounds=8,
        max_work_units=1_000_000,
        max_total_work_units=20_000_000,
    )
    a = certify_upcc_pair_root_split_family(vertex_count, 2, colors, **common)
    b = certify_upcc_pair_root_split_family(vertex_count, 2, relabeled, **common)

    assert a.status == b.status == "certified_complete_upcc_pair_root_split_family"
    assert Counter(a.branch_design_statuses) == Counter(b.branch_design_statuses)
    assert Counter(a.child_aux_sizes) == Counter(b.child_aux_sizes)
    assert a.branch_count == b.branch_count == vertex_count * (vertex_count - 1)

    a_by_pair = {
        pair: (status, sizes, partition)
        for pair, status, sizes, partition in zip(
            a.root_pairs, a.branch_design_statuses, a.child_aux_sizes, a.partitions
        )
    }
    b_by_pair = {
        pair: (status, sizes, partition)
        for pair, status, sizes, partition in zip(
            b.root_pairs, b.branch_design_statuses, b.child_aux_sizes, b.partitions
        )
    }

    def canonical_partition(partition):
        return tuple(
            sorted(
                (tuple(sorted(cell)) for cell in partition),
                key=lambda cell: (len(cell), cell),
            )
        )

    # ``relabeled[a,b] = original[permutation[a],permutation[b]]``.  Thus each
    # marked branch, not only the aggregate multiset, is transported by the
    # same relabeling while preserving the ordered mark positions.
    for pair, (status, sizes, partition) in b_by_pair.items():
        old_pair = (permutation[pair[0]], permutation[pair[1]])
        old_status, old_sizes, old_partition = a_by_pair[old_pair]
        mapped_partition = canonical_partition(
            tuple(tuple(permutation[x] for x in cell) for cell in partition)
        )
        assert status == old_status
        assert sizes == old_sizes
        assert mapped_partition == canonical_partition(old_partition)


def test_rank_two_clique_is_not_promoted_to_upcc_pair_root_progress():
    vertex_count = 6
    colors = tuple(0 for _ in combinations(range(vertex_count), 2))
    got = certify_upcc_pair_root_split_family(
        vertex_count,
        2,
        colors,
        root_n=16,
        alpha=0.5,
        max_tuple_states=100,
        max_rounds=8,
        max_work_units=100_000,
        max_total_work_units=10_000_000,
    )
    assert got.status == "not_upcc_pair_root_split_leaf"
    assert got.base_design_status == "stable_twl_clique_continue"
    assert got.exact
    assert not got.complete
    assert not got.aux_shrink_certified
    assert got.checked_root_pairs == 0


def test_total_work_preflight_fails_before_any_k_wl_execution():
    colors = _rook_relation(3)
    got = certify_upcc_pair_root_split_family(
        9,
        2,
        colors,
        root_n=16,
        alpha=0.5,
        max_root_pairs=1000,
        max_tuple_states=1000,
        max_rounds=8,
        max_work_units=1_000_000,
        max_total_work_units=1,
    )
    assert got.status == "upcc_pair_root_total_work_preflight_closed"
    assert not got.exact
    assert got.executed_work_units == 0
    assert got.checked_root_pairs == 0


def test_complete_cover_cap_fails_closed_instead_of_sampling_root_pairs():
    colors = _rook_relation(3)
    got = certify_upcc_pair_root_split_family(
        9,
        2,
        colors,
        root_n=16,
        alpha=0.5,
        max_root_pairs=71,
        max_tuple_states=1000,
        max_rounds=8,
        max_work_units=1_000_000,
        max_total_work_units=20_000_000,
    )
    assert got.branch_count == 72
    assert got.status == "upcc_pair_root_branch_cap_closed"
    assert not got.complete_root_cover
    assert not got.aux_shrink_certified
