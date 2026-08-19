from itertools import combinations

from bipartite_uniform_neighborhood_string_iso_v1 import (
    solve_bipartite_incidence_via_uniform_neighborhood,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def _fano_edges(right_perm=None):
    lines = [
        (0, 1, 2),
        (0, 3, 4),
        (0, 5, 6),
        (1, 3, 5),
        (1, 4, 6),
        (2, 3, 6),
        (2, 4, 5),
    ]
    q = tuple(range(7)) if right_perm is None else tuple(right_perm)
    return tuple((a, q[b]) for a, line in enumerate(lines) for b in line)


def _edge_product_permutation(n1, n2, left, right):
    return tuple(left[a] * n2 + right[b] for a in range(n1) for b in range(n2))


def _two_point_right_ambient():
    q = (1, 0, 2, 3, 4, 5, 6)
    p = _edge_product_permutation(7, 7, tuple(range(7)), q)
    return q, p, schreier_stabilizer_chain([p])


def _maps(source, target, p):
    return all(source[i] == target[p[i]] for i in range(len(source)))


def _bits(edges):
    out = [0] * 49
    for a, b in edges:
        out[a * 7 + b] = 1
    return tuple(out)


def _solve(source, target):
    q, p, group = _two_point_right_ambient()
    got = solve_bipartite_incidence_via_uniform_neighborhood(
        group,
        ((q, False),),
        7,
        7,
        source,
        target,
        root_n=49,
        max_tuple_states=1000,
        max_family_work_units=2000000,
        max_branch_work_units=500000,
        max_partition_states=10,
        max_group_order=16,
    )
    return q, p, group, got


def test_same_fano_incidence_filters_false_positive_v2_branches_to_identity_coset():
    source = _fano_edges()
    _, _, group, got = _solve(source, source)
    assert got.status == "exact_bipartite_uniform_neighborhood_string_isomorphism"
    assert got.exact
    assert not got.exact_empty
    assert got.ambient_product_action_certified
    assert got.provenance is not None and got.provenance.derived_relation_certified
    assert got.pipeline is not None and got.pipeline.relation_branch_count == 49
    assert got.pipeline.ambient_survivor_count == 9
    assert got.full_string is not None and got.full_string.coset is not None
    assert got.full_string.coset.subgroup.order == 1
    source_bits = _bits(source)
    assert _maps(source_bits, source_bits, got.full_string.coset.representative)
    assert group.contains(got.full_string.coset.representative)


def test_right_relabelled_fano_reconstructs_unique_edge_position_swap():
    q, p, group = _two_point_right_ambient()
    source = _fano_edges()
    target = _fano_edges(q)
    got = solve_bipartite_incidence_via_uniform_neighborhood(
        group,
        ((q, False),),
        7,
        7,
        source,
        target,
        root_n=49,
        max_tuple_states=1000,
        max_family_work_units=2000000,
        max_branch_work_units=500000,
        max_partition_states=10,
        max_group_order=16,
    )
    assert got.status == "exact_bipartite_uniform_neighborhood_string_isomorphism"
    assert got.full_string is not None and got.full_string.coset is not None
    assert got.full_string.coset.subgroup.order == 1
    source_bits = _bits(source)
    target_bits = _bits(target)
    assert _maps(source_bits, target_bits, got.full_string.coset.representative)
    assert got.full_string.coset.representative == p


def test_inconsistent_lifted_right_action_is_rejected_before_provenance_use():
    source = _fano_edges()
    q, _, group = _two_point_right_ambient()
    wrong = identity(7)
    got = solve_bipartite_incidence_via_uniform_neighborhood(
        group,
        ((wrong, False),),
        7,
        7,
        source,
        source,
    )
    assert got.status == "undetermined_bipartite_ambient_product_action"
    assert not got.ambient_product_action_certified
    assert not got.exact
    assert got.provenance is None
    assert q != wrong


def test_degree_inventory_mismatch_is_exact_empty_end_to_end():
    source = _fano_edges()
    target = list(source)
    target.remove((0, 0))
    _, _, _, got = _solve(source, tuple(target))
    assert got.status == "exact_empty_bipartite_uniform_neighborhood_provenance"
    assert got.exact
    assert got.exact_empty
    assert got.provenance is not None and got.provenance.exact_empty
    assert got.pipeline is None
