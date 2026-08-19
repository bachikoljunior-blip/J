from itertools import combinations

from colored_subset_design_branch_plan_v1 import build_colored_subset_design_branch_plan
from design_branch_tuple_transport_v1 import transport_complete_design_tuple_branches
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _fano_colors():
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
    return v, t, coords, tuple(int(S in lines) for S in coords)


def _relabel(v, t, colors, q):
    coords = tuple(combinations(range(v), t))
    index = {S: i for i, S in enumerate(coords)}
    out = [None] * len(coords)
    for i, S in enumerate(coords):
        out[index[tuple(sorted(q[x] for x in S))]] = colors[i]
    return tuple(out)


def _symmetric_group(v):
    swap = list(range(v))
    swap[0], swap[1] = swap[1], swap[0]
    cycle = tuple((i + 1) % v for i in range(v))
    return schreier_stabilizer_chain([tuple(swap), cycle])


def test_full_symmetric_ground_action_transports_every_fano_point_branch_pair():
    v, t, _coords, colors = _fano_colors()
    q = (3, 5, 1, 6, 0, 4, 2)
    target = _relabel(v, t, colors, q)
    branch_plan = build_colored_subset_design_branch_plan(
        v, t, colors, target, max_wl_rounds=256
    )
    group = _symmetric_group(v)
    lifted = tuple((g, False) for g in group.original_generators)
    got = transport_complete_design_tuple_branches(
        group, lifted, branch_plan, max_partition_states=32
    )
    assert got.status == "certified_complete_design_tuple_transport_cover"
    assert got.complete and not got.exact_empty
    assert got.input_branch_count == 49
    assert got.surviving_branch_count == 49
    assert all(branch.coset is not None for branch in got.branches)


def test_identity_ground_action_keeps_only_equal_singleton_tuple_pairs():
    v, t, _coords, colors = _fano_colors()
    branch_plan = build_colored_subset_design_branch_plan(
        v, t, colors, colors, max_wl_rounds=256
    )
    ident = identity(v)
    group = schreier_stabilizer_chain([ident])
    lifted = tuple((g, False) for g in group.original_generators)
    got = transport_complete_design_tuple_branches(
        group, lifted, branch_plan, max_partition_states=8
    )
    assert got.status == "certified_complete_design_tuple_transport_cover"
    assert got.surviving_branch_count == v
    assert {(b.source_tuple, b.target_tuple) for b in got.branches} == {
        ((u,), (u,)) for u in range(v)
    }


def test_partition_orbit_limit_fails_closed_for_complete_cover():
    v, t, _coords, colors = _fano_colors()
    branch_plan = build_colored_subset_design_branch_plan(
        v, t, colors, colors, max_wl_rounds=256
    )
    group = _symmetric_group(v)
    lifted = tuple((g, False) for g in group.original_generators)
    got = transport_complete_design_tuple_branches(
        group, lifted, branch_plan, max_partition_states=1
    )
    assert got.status == "undetermined_signed_ground_partition_orbit_limit"
    assert not got.complete and not got.exact_empty
    assert got.branches == ()
