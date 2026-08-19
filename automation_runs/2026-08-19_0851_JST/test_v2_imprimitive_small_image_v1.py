from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from recursive_point_image_coset_intersection import right_coset_intersection_recursive
from u2_imprimitive_small_quotient_v1 import imprimitive_small_quotient_string_isomorphism_u2
from v2_imprimitive_small_image_v1 import (
    enumerate_schreier_group_exact,
    imprimitive_small_image_string_isomorphism_v2,
)


def block_cycle(k, b=2):
    n = k * b
    p = list(range(n))
    for i in range(k):
        for j in range(b):
            p[i * b + j] = ((i + 1) % k) * b + j
    return tuple(p)


def block_transposition(k, b=2):
    n = k * b
    p = list(range(n))
    for j in range(b):
        p[j], p[b + j] = p[b + j], p[j]
    return tuple(p)


def first_block_swap(k, b=2):
    n = k * b
    p = list(range(n))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def cyclic_block_wreath(k):
    return schreier_stabilizer_chain([block_cycle(k), first_block_swap(k)])


def symmetric_block_wreath(k):
    return schreier_stabilizer_chain(
        [block_cycle(k), block_transposition(k), first_block_swap(k)]
    )


def relabel_target(source, p):
    inv = [0] * len(p)
    for i, j in enumerate(p):
        inv[j] = i
    return tuple(source[inv[j]] for j in range(len(p)))


def test_generator_bfs_matches_schreier_order_without_symmetric_group_scan():
    G = schreier_stabilizer_chain([tuple((i + 1) % 31 for i in range(31))])
    elements = enumerate_schreier_group_exact(G, max_elements=64)
    assert elements is not None
    assert len(elements) == G.order == 31
    assert identity(31) in elements


def test_large_quotient_degree_small_image_is_exact_where_rev167_degree_cap_stops():
    G = cyclic_block_wreath(11)
    source = tuple(range(G.degree))

    old = imprimitive_small_quotient_string_isomorphism_u2(
        G,
        source,
        source,
        root_n=64,
        max_explicit_degree=2,
        max_explicit_quotient_degree=7,
    )
    assert old.status == "undetermined_explicit_quotient_cap"
    assert not old.exact

    got = imprimitive_small_image_string_isomorphism_v2(
        G,
        source,
        source,
        root_n=64,
        max_explicit_degree=2,
        max_quotient_image_order=64,
    )
    assert got.status == "exact_imprimitive_small_image_coset"
    assert got.exact and got.coset is not None
    assert got.coset.subgroup.order == 1
    assert got.quotient_image_order == 11
    assert got.quotient_image_elements_checked == 11
    assert len(got.children) == 11
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_large_degree_cyclic_quotient_recovers_nonidentity_fiber_exactly():
    G = cyclic_block_wreath(11)
    source = tuple(range(G.degree))
    q = block_cycle(11)
    target = relabel_target(source, q)

    got = imprimitive_small_image_string_isomorphism_v2(
        G,
        source,
        target,
        root_n=64,
        max_explicit_degree=2,
        max_quotient_image_order=64,
    )
    assert got.status == "exact_imprimitive_small_image_coset"
    assert got.exact and got.coset is not None
    assert got.coset.contains(q)
    assert got.quotient_image_order == 11
    assert got.quotient_image_elements_checked == 11
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_small_instance_matches_whole_domain_exact_oracle():
    G = cyclic_block_wreath(3)
    source = tuple(range(G.degree))
    q = block_cycle(3)
    target = relabel_target(source, q)
    got = imprimitive_small_image_string_isomorphism_v2(
        G,
        source,
        target,
        root_n=64,
        max_explicit_degree=2,
        max_quotient_image_order=64,
    )
    assert got.exact and got.coset is not None

    value_coset = _all_value_preserving_maps(source, target)
    exact = right_coset_intersection_recursive(
        RightCoset(G, identity(G.degree)), value_coset, max_nodes=100000
    )
    assert exact.status == "exact_intersection_coset"
    assert exact.coset is not None
    assert exact.coset.subgroup.order == got.coset.subgroup.order
    assert exact.coset.contains(got.coset.representative)
    assert got.coset.contains(exact.coset.representative)


def test_large_order_quotient_fails_closed_before_enumeration():
    G = symmetric_block_wreath(5)
    n = G.degree
    got = imprimitive_small_image_string_isomorphism_v2(
        G,
        (0,) * n,
        (0,) * n,
        root_n=64,
        max_explicit_degree=2,
        max_quotient_image_order=64,
    )
    assert got.status == "undetermined_quotient_image_order_cap"
    assert not got.exact and got.coset is None
    assert got.quotient_image_order == 120
    assert got.quotient_image_elements_checked == 0
    assert got.permutation_candidates_checked == 0
