from itertools import combinations

from colored_subset_design_branch_plan_v1 import build_colored_subset_design_branch_plan


def _fano():
    v, t = 7, 3
    coords = tuple(combinations(range(v), t))
    lines = {
        (0, 1, 2),
        (0, 3, 4),
        (0, 5, 6),
        (1, 3, 5),
        (1, 4, 6),
        (2, 3, 6),
        (2, 4, 5),
    }
    colors = tuple(int(S in lines) for S in coords)
    return v, t, coords, colors


def _relabel(v, t, colors, q):
    coords = tuple(combinations(range(v), t))
    index = {S: i for i, S in enumerate(coords)}
    out = [None] * len(coords)
    for i, S in enumerate(coords):
        image = tuple(sorted(q[x] for x in S))
        out[index[image]] = colors[i]
    return tuple(out)


def test_fano_relabeling_gets_complete_7_by_7_minimal_branch_cover():
    v, t, _coords, colors = _fano()
    q = (3, 5, 1, 6, 0, 4, 2)
    target = _relabel(v, t, colors, q)
    got = build_colored_subset_design_branch_plan(
        v, t, colors, target,
        max_wl_rounds=256,
    )
    assert got.status == "certified_complete_design_branch_plan"
    assert got.complete and not got.exact_empty
    assert got.individualization_length == 1
    assert got.branch_count == 49
    assert len(got.branches) == 49
    # Every true relabeled witness pairing is included in the Cartesian cover.
    for xs in got.source_family.witness_tuples:
        assert (xs, tuple(q[x] for x in xs)) in got.branches


def test_relation_color_multiplicity_mismatch_is_exact_empty():
    v, t, _coords, colors = _fano()
    target = list(colors)
    target[0] = 1 - target[0]
    got = build_colored_subset_design_branch_plan(
        v, t, colors, tuple(target),
        max_wl_rounds=256,
    )
    assert got.status == "exact_empty_design_relation_color_multiplicity"
    assert got.exact_empty and got.complete
    assert got.branches == ()


def test_materialization_limit_fails_closed_without_partial_branch_cover():
    v, t, _coords, colors = _fano()
    got = build_colored_subset_design_branch_plan(
        v, t, colors, colors,
        max_wl_rounds=256,
        max_branch_pairs=10,
    )
    assert got.status == "undetermined_design_branch_pair_limit"
    assert got.branch_count == 49
    assert not got.complete and not got.exact_empty
    assert got.branches == ()
