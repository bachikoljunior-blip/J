from paired_affected_segment_automorphism_v1 import (
    paired_affected_segment_automorphism_group,
)
from paired_giant_action_certificates_v1 import analyze_paired_giant_action
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


def test_invariant_uniform_segment_uses_exact_no_recursion_fast_path():
    G, images = product_s5_kernel_c2()
    got = paired_affected_segment_automorphism_group(
        G, images, (0, 0, 0, 0, 0, 9, 9), (0, 1, 2, 3, 4)
    )
    assert got.status == "exact_paired_affected_segment_automorphism_group", got
    assert got.exact
    assert got.subgroup is G
    assert got.execution is None
    assert got.recurrence_child_bound_verified
    assert got.paired_image_generators == images


def test_nonuniform_segment_recurses_and_retains_exact_subgroup_image_pairing():
    G, images = product_s5_kernel_c2()
    got = paired_affected_segment_automorphism_group(
        G, images, (1, 0, 0, 0, 0, 9, 9), (0, 1, 2, 3, 4),
        max_quotient_leaves=200,
    )
    assert got.status == "exact_paired_affected_segment_automorphism_group", got
    assert got.exact and got.subgroup is not None and got.execution is not None
    assert got.subgroup.order == 48
    assert got.recurrence_child_bound_verified

    after = analyze_paired_giant_action(got.subgroup, got.paired_image_generators)
    assert after.status == "exact_paired_nongiant_action", after
    assert after.image_order == 24
    assert after.kernel_order == 2


def test_recursion_limit_remains_fail_closed():
    G, images = product_s5_kernel_c2()
    got = paired_affected_segment_automorphism_group(
        G, images, (1, 0, 0, 0, 0, 9, 9), (0, 1, 2, 3, 4),
        max_quotient_leaves=10,
    )
    assert got.status == "undetermined_quotient_leaf_limit", got
    assert not got.exact and got.subgroup is None
    assert not got.recurrence_child_bound_verified
