from canonical_partition_guided_string_iso_v1 import _all_value_preserving_maps
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import identity, schreier_stabilizer_chain
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from recursive_point_image_coset_intersection import right_coset_intersection_recursive
from s1_string_isomorphism_v1 import s1_string_isomorphism as s1_v1
from s1_string_isomorphism_v2 import s1_string_isomorphism_v2


def cycle(n):
    return tuple((i + 1) % n for i in range(n))


def transposition(n, a=0, b=1):
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def relabel_target(source, p):
    inv = [0] * len(p)
    for i, j in enumerate(p):
        inv[j] = i
    return tuple(source[inv[j]] for j in range(len(p)))


def test_c29_is_exact_small_order_terminal_even_though_degree_is_large():
    n = 29
    c = cycle(n)
    G = schreier_stabilizer_chain([c])
    source = tuple(range(n))

    old = s1_v1(G, source, source, root_n=64, max_explicit_degree=8)
    assert not old.exact
    assert old.status == "undetermined_primitive_non_giant"

    got = s1_string_isomorphism_v2(
        G,
        source,
        source,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=64,
    )
    assert got.status == "exact_small_order_group_coset"
    assert got.exact and got.coset is not None
    assert got.coset.subgroup.order == 1
    assert got.certified_group_order == 29
    assert got.group_elements_checked == 58
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_c29_recovers_nonidentity_string_isomorphism():
    n = 29
    c = cycle(n)
    G = schreier_stabilizer_chain([c])
    source = tuple(range(n))
    target = relabel_target(source, c)
    got = s1_string_isomorphism_v2(
        G,
        source,
        target,
        root_n=64,
        max_group_order=64,
    )
    assert got.exact and got.coset is not None
    assert got.coset.contains(c)
    assert got.certified_group_order == 29


def test_small_instance_matches_existing_exact_coset_oracle():
    n = 7
    c = cycle(n)
    G = schreier_stabilizer_chain([c])
    source = (0, 1, 0, 2, 1, 2, 3)
    target = relabel_target(source, c)
    got = s1_string_isomorphism_v2(
        G,
        source,
        target,
        root_n=32,
        max_group_order=64,
    )
    assert got.exact and got.coset is not None

    value_coset = _all_value_preserving_maps(source, target)
    exact = right_coset_intersection_recursive(
        RightCoset(G, identity(n)), value_coset, max_nodes=100000
    )
    assert exact.status == "exact_intersection_coset"
    assert exact.coset is not None
    assert exact.coset.subgroup.order == got.coset.subgroup.order
    assert exact.coset.contains(got.coset.representative)
    assert got.coset.contains(exact.coset.representative)


def test_large_nonconstant_group_order_falls_back_to_structural_s1_without_enumeration():
    n = 9
    G = schreier_stabilizer_chain([cycle(n), transposition(n)])
    source = tuple(range(n))
    got = s1_string_isomorphism_v2(
        G,
        source,
        source,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=64,
    )
    assert not got.exact
    assert got.status == "undetermined_primitive_giant_local_certificates"
