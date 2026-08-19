from itertools import combinations

from paired_uniform_neighborhood_design_branches_v1 import (
    pair_uniform_neighborhood_design_branches,
)
from paired_uniform_neighborhood_full_string_union_v1 import (
    solve_paired_uniform_neighborhood_full_string,
)
from paired_uniform_neighborhood_tuple_transport_v1 import (
    transport_paired_uniform_neighborhood_design_branches,
)
from permutation_group_schreier import schreier_stabilizer_chain


def _fano_transport():
    lines = {
        (0, 1, 2),
        (0, 3, 4),
        (0, 5, 6),
        (1, 3, 5),
        (1, 4, 6),
        (2, 3, 6),
        (2, 4, 5),
    }
    coords = tuple(combinations(range(7), 3))
    colors = tuple(int(T in lines) for T in coords)
    plan = pair_uniform_neighborhood_design_branches(
        7, 3, coords, colors, coords, colors,
        root_n=7,
        max_tuple_states=1000,
        max_family_work_units=2000000,
        max_branch_work_units=500000,
    )
    swap = (1, 0, 2, 3, 4, 5, 6)
    group = schreier_stabilizer_chain([swap])
    transport = transport_paired_uniform_neighborhood_design_branches(
        group, ((swap, False),), plan, max_partition_states=10
    )
    assert transport.status == "certified_complete_paired_uniform_neighborhood_tuple_transport"
    return group, transport


def _maps(source, target, p):
    return all(source[i] == target[p[i]] for i in range(len(source)))


def test_provenance_gate_is_required_before_full_string_promotion():
    group, transport = _fano_transport()
    source = tuple(range(7))
    target = (1, 0, 2, 3, 4, 5, 6)
    got = solve_paired_uniform_neighborhood_full_string(
        group, transport, source, target, root_n=7,
        relation_provenance_certified=False,
    )
    assert got.status == "undetermined_uniform_neighborhood_relation_provenance"
    assert not got.exact
    assert not got.complete
    assert got.coset is None


def test_exact_full_string_union_reconstructs_unique_swap_when_provenance_is_certified():
    group, transport = _fano_transport()
    source = tuple(range(7))
    target = (1, 0, 2, 3, 4, 5, 6)
    got = solve_paired_uniform_neighborhood_full_string(
        group, transport, source, target, root_n=7,
        relation_provenance_certified=True,
        max_explicit_degree=8,
        max_group_order=16,
    )
    assert got.status == "exact_paired_uniform_neighborhood_full_string_union_coset"
    assert got.exact
    assert got.complete
    assert got.relation_provenance_certified
    assert got.coset is not None
    assert group.contains(got.coset.representative)
    assert _maps(source, target, got.coset.representative)
    assert got.coset.subgroup.order == 1
    assert got.nonempty_branches >= 1


def test_all_distinct_identity_string_reconstructs_identity_only():
    group, transport = _fano_transport()
    values = tuple(range(7))
    got = solve_paired_uniform_neighborhood_full_string(
        group, transport, values, values, root_n=7,
        relation_provenance_certified=True,
        max_explicit_degree=8,
        max_group_order=16,
    )
    assert got.status == "exact_paired_uniform_neighborhood_full_string_union_coset"
    assert got.coset is not None
    assert _maps(values, values, got.coset.representative)
    assert got.coset.subgroup.order == 1


def test_value_multiplicity_mismatch_makes_every_complete_branch_empty():
    group, transport = _fano_transport()
    source = tuple(range(7))
    target = (0,) * 7
    got = solve_paired_uniform_neighborhood_full_string(
        group, transport, source, target, root_n=7,
        relation_provenance_certified=True,
        max_explicit_degree=8,
        max_group_order=16,
    )
    assert got.status == "exact_empty_paired_uniform_neighborhood_full_string_union"
    assert got.exact
    assert got.complete
    assert got.coset is None
    assert got.nonempty_branches == 0
