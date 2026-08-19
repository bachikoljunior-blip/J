from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from recursive_point_image_coset_intersection import right_coset_intersection_recursive
from u2_imprimitive_small_quotient_v1 import imprimitive_small_quotient_string_isomorphism_u2


def block_cycle(k, b=2):
    n = k * b
    p = list(range(n))
    for i in range(k):
        for j in range(b):
            p[i * b + j] = ((i + 1) % k) * b + j
    return tuple(p)


def first_block_swap(k, b=2):
    n = k * b
    p = list(range(n))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def wreath_like(k):
    return schreier_stabilizer_chain([block_cycle(k), first_block_swap(k)])


def test_small_canonical_quotient_is_exact_and_matches_whole_domain_oracle():
    G = wreath_like(3)
    values = tuple(range(6))
    got = imprimitive_small_quotient_string_isomorphism_u2(
        G, values, values,
        root_n=64,
        max_explicit_degree=2,
        max_explicit_quotient_degree=3,
    )
    assert got.status == "exact_imprimitive_small_quotient_coset"
    assert got.exact and got.coset is not None
    assert got.coset.subgroup.order == 1
    # C3 quotient: all three image fibers are actual retained child proofs.
    assert len(got.children) == 3
    assert all(c.exact for c in got.children)
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified

    value_coset = _all_value_preserving_maps(values, values)
    exact = right_coset_intersection_recursive(
        RightCoset(G, identity(6)), value_coset, max_nodes=100000
    )
    assert exact.status == "exact_intersection_coset"
    assert exact.coset is not None
    assert exact.coset.subgroup.order == got.coset.subgroup.order
    assert exact.coset.contains(got.coset.representative)
    assert got.coset.contains(exact.coset.representative)


def test_related_strings_recover_nonidentity_quotient_fiber():
    G = wreath_like(3)
    source = tuple(range(6))
    q = block_cycle(3)
    inv = [0] * 6
    for i, j in enumerate(q):
        inv[j] = i
    target = tuple(source[inv[j]] for j in range(6))
    got = imprimitive_small_quotient_string_isomorphism_u2(
        G, source, target,
        root_n=64,
        max_explicit_degree=2,
        max_explicit_quotient_degree=3,
    )
    assert got.status == "exact_imprimitive_small_quotient_coset"
    assert got.exact and got.coset is not None
    assert got.coset.contains(q)
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_large_explicit_quotient_fails_closed_without_fiber_enumeration():
    G = wreath_like(5)
    n = G.degree
    got = imprimitive_small_quotient_string_isomorphism_u2(
        G, (0,) * n, (0,) * n,
        root_n=64,
        max_explicit_degree=2,
        max_explicit_quotient_degree=3,
    )
    assert got.status == "undetermined_explicit_quotient_cap"
    assert not got.exact and got.coset is None
    assert got.permutation_candidates_checked == 0
