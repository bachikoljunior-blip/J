from paired_partition_transporter_v1 import paired_partition_transporter
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
    return G, (restrict(s, 5), restrict(c, 5), identity(5))


def test_ordered_partition_transporter_is_lifted_with_complete_kernel_preimage():
    G, images = product_s5_kernel_c2()
    source = ((0, 1), (2, 3, 4))
    target = ((3, 4), (0, 1, 2))
    got = paired_partition_transporter(G, images, source, target)
    assert got.status == "exact_paired_partition_transporter_coset", got
    assert got.image_coset is not None and got.lifted_coset is not None
    # Ordered 2+3 set partition stabilizer in S5 has order 2!*3!=12;
    # the invisible C2 kernel doubles the original-domain candidate subgroup.
    assert got.image_coset.subgroup.order == 12
    assert got.lifted_coset.subgroup.order == 24

    q = got.image_coset.representative
    assert tuple(tuple(sorted(q[x] for x in C)) for C in source) == target
    assert got.lifted_coset.subgroup.order * 10 == G.order


def test_partition_shape_mismatch_is_exactly_empty_before_search():
    G, images = product_s5_kernel_c2()
    got = paired_partition_transporter(
        G, images, ((0, 1), (2, 3, 4)), ((0,), (1, 2, 3, 4))
    )
    assert got.status == "partition_shape_mismatch", got
    assert got.image_coset is None and got.lifted_coset is None


def test_partition_orbit_budget_is_fail_closed():
    G, images = product_s5_kernel_c2()
    got = paired_partition_transporter(
        G, images, ((0, 1), (2, 3, 4)), ((3, 4), (0, 1, 2)), max_states=1
    )
    assert got.status == "undetermined_partition_orbit_limit", got
    assert got.lifted_coset is None
