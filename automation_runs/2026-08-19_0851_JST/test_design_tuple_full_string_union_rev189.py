from itertools import combinations

from colored_subset_design_branch_plan_v1 import build_colored_subset_design_branch_plan
from design_branch_tuple_transport_v1 import transport_complete_design_tuple_branches
from design_tuple_full_string_union_si_v1 import solve_design_tuple_transport_full_string
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
    return v, t, tuple(int(S in lines) for S in coords)


def _cyclic_group(v):
    cycle = tuple((i + 1) % v for i in range(v))
    return cycle, schreier_stabilizer_chain([cycle])


def _transport_for_c7_fano():
    v, t, colors = _fano_colors()
    plan = build_colored_subset_design_branch_plan(
        v, t, colors, colors, max_wl_rounds=64
    )
    cycle, group = _cyclic_group(v)
    transport = transport_complete_design_tuple_branches(
        group,
        ((cycle, False),),
        plan,
        max_partition_states=32,
    )
    assert transport.status == "certified_complete_design_tuple_transport_cover"
    return v, cycle, group, transport


def test_constant_full_string_reconstructs_entire_cyclic_ambient_coset():
    v, cycle, group, transport = _transport_for_c7_fano()
    source = tuple(0 for _ in range(v))
    got = solve_design_tuple_transport_full_string(
        group,
        transport,
        source,
        source,
        root_n=v,
        max_group_order=8,
    )
    assert got.status == "exact_design_tuple_full_string_union_coset"
    assert got.exact and got.complete and got.coset is not None
    assert got.coset.subgroup.order == group.order == v
    assert got.coset.contains(identity(v))
    assert got.coset.contains(cycle)


def test_distinct_full_string_filters_all_nonidentity_tuple_transporters():
    v, _cycle, group, transport = _transport_for_c7_fano()
    source = tuple(range(v))
    got = solve_design_tuple_transport_full_string(
        group,
        transport,
        source,
        source,
        root_n=v,
        max_group_order=8,
    )
    assert got.status == "exact_design_tuple_full_string_union_coset"
    assert got.exact and got.complete and got.coset is not None
    assert got.coset.subgroup.order == 1
    assert got.coset.contains(identity(v))
    assert got.nonempty_branches >= 1


def test_exact_empty_upstream_transport_remains_exact_empty_without_branch_recursion():
    v = 7
    ident = identity(v)
    group = schreier_stabilizer_chain([ident])
    from design_branch_tuple_transport_v1 import DesignTupleTransportPlan

    empty = DesignTupleTransportPlan(
        "exact_empty_design_tuple_transport_cover",
        v, v, 1, 49, 0, (), 10.0, True, True,
        "fixture exact empty cover",
    )
    got = solve_design_tuple_transport_full_string(
        group,
        empty,
        tuple(range(v)),
        tuple(range(v)),
        root_n=v,
    )
    assert got.status == "exact_empty_design_tuple_transport"
    assert got.exact and got.complete and got.coset is None
    assert got.branches_checked == 0
