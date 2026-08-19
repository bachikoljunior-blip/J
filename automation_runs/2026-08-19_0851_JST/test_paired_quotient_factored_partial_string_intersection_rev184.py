from paired_quotient_factored_partial_string_intersection_v1 import (
    paired_quotient_factored_partial_string_intersection,
)
from permutation_group_schreier import identity, schreier_stabilizer_chain


def transposition(n, a, b):
    p = list(range(n))
    p[a], p[b] = p[b], p[a]
    return tuple(p)


def cycle(n, points):
    p = list(range(n))
    pts = tuple(points)
    for a, b in zip(pts, pts[1:] + pts[:1]):
        p[a] = b
    return tuple(p)


def restrict(p, m):
    return tuple(p[i] for i in range(m))


def product_s5_kernel_c2():
    s = transposition(7, 0, 1)
    c = cycle(7, (0, 1, 2, 3, 4))
    z = transposition(7, 5, 6)
    G = schreier_stabilizer_chain((s, c, z))
    images = (restrict(s, 5), restrict(c, 5), identity(5))
    return G, images


def test_uniform_affected_segment_reassembles_the_entire_source_group():
    G, images = product_s5_kernel_c2()
    values = (0, 0, 0, 0, 0, 9, 9)
    got = paired_quotient_factored_partial_string_intersection(
        G, images, values, (0, 1, 2, 3, 4), max_quotient_leaves=200
    )
    assert got.status == "exact_paired_quotient_factored_partial_string_intersection", got
    assert got.coset is not None
    assert got.coset.subgroup.order == G.order
    assert got.image_order == 120
    assert got.quotient_leaves == 120
    assert got.largest_kernel_child_domain == 1
    assert got.certified_kernel_child_bound == 1
    assert got.recurrence_child_bound_verified


def test_colored_affected_segment_returns_exact_color_stabilizer():
    G, images = product_s5_kernel_c2()
    # One distinguished point in the affected S5 orbit leaves an S4 image; the
    # invisible C2 kernel survives, so the exact segment stabilizer has order 48.
    values = (1, 0, 0, 0, 0, 9, 9)
    got = paired_quotient_factored_partial_string_intersection(
        G, images, values, (0, 1, 2, 3, 4), max_quotient_leaves=200
    )
    assert got.status == "exact_paired_quotient_factored_partial_string_intersection", got
    assert got.coset is not None
    assert got.coset.subgroup.order == 48
    assert got.recurrence_child_bound_verified


def test_structural_image_leaf_cap_fails_closed():
    G, images = product_s5_kernel_c2()
    got = paired_quotient_factored_partial_string_intersection(
        G, images, (0,) * 7, (0, 1, 2, 3, 4), max_quotient_leaves=10
    )
    assert got.status == "undetermined_quotient_leaf_limit", got
    assert got.coset is None
    assert not got.recurrence_child_bound_verified
