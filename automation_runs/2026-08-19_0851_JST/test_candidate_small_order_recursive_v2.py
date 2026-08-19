from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import compose, identity, schreier_stabilizer_chain
from proof_carrying_small_order_candidate_v1 import exact_small_order_candidate_string_isomorphism
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3
from v2_imprimitive_small_image_v1 import imprimitive_small_image_string_isomorphism_v2
from v2_imprimitive_small_image_v2 import imprimitive_small_image_string_isomorphism_v2_recursive


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


def block_cycle(k, b):
    n = k * b
    p = list(range(n))
    for i in range(k):
        for j in range(b):
            p[i * b + j] = ((i + 1) % k) * b + j
    return tuple(p)


def within_first_block_cycle(k, b):
    n = k * b
    p = list(range(n))
    for j in range(b):
        p[j] = (j + 1) % b
    return tuple(p)


def cyclic_block_kernel(k=3, b=11):
    return schreier_stabilizer_chain([block_cycle(k, b), within_first_block_cycle(k, b)])


def test_small_transitive_candidate_coset_is_exact_without_symmetric_group_scan():
    n = 11
    H = schreier_stabilizer_chain([cycle(n)])
    r = transposition(n, 0, 1)
    candidate = RightCoset(H, r)
    h = cycle(n)
    witness = compose(r, h)
    source = tuple(range(n))
    target = relabel_target(source, witness)

    got = exact_small_order_candidate_string_isomorphism(
        candidate,
        source,
        target,
        root_n=64,
        max_group_order=64,
    )
    assert got.status == "exact_small_order_candidate_coset"
    assert got.exact and got.coset is not None
    assert got.coset.contains(witness)
    assert got.certified_subgroup_order == 11
    assert got.subgroup_elements_checked == 11
    assert got.permutation_candidates_checked == 22
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_large_kernel_with_small_orbit_images_closes_where_rev169_stops():
    G = cyclic_block_kernel(3, 11)
    n = G.degree
    source = tuple(range(n))
    q = block_cycle(3, 11)
    target = relabel_target(source, q)

    old = imprimitive_small_image_string_isomorphism_v2(
        G,
        source,
        target,
        root_n=64,
        max_explicit_degree=8,
        max_quotient_image_order=64,
    )
    assert not old.exact
    assert old.status == "undetermined_imprimitive_kernel_child_requires_v2"

    got = imprimitive_small_image_string_isomorphism_v2_recursive(
        G,
        source,
        target,
        root_n=64,
        max_explicit_degree=8,
        max_quotient_image_order=64,
        max_candidate_group_order=64,
    )
    assert got.status == "exact_imprimitive_small_image_recursive_coset"
    assert got.exact and got.coset is not None
    assert got.coset.contains(q)
    assert got.coset.subgroup.order == 1
    assert got.quotient_image_order == 3
    assert got.quotient_image_elements_checked == 3
    assert len(got.children) == 3
    assert validate_quasipoly_recurrence_tree_v3(got.accounting).certified


def test_large_transitive_candidate_above_cap_stays_fail_closed():
    n = 9
    H = schreier_stabilizer_chain([cycle(n), transposition(n)])
    candidate = RightCoset(H, identity(n))
    got = exact_small_order_candidate_string_isomorphism(
        candidate,
        (0,) * n,
        (0,) * n,
        root_n=64,
        max_group_order=64,
    )
    assert got.status == "undetermined_candidate_group_order_cap"
    assert not got.exact and got.coset is None
    assert got.certified_subgroup_order == H.order
    assert got.subgroup_elements_checked == 0
    assert got.permutation_candidates_checked == 0
