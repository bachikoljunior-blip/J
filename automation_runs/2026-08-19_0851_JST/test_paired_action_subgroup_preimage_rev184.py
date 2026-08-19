import pytest

from paired_action_subgroup_preimage_v1 import paired_action_subgroup_preimage
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


def test_exact_a5_preimage_retains_generator_pairing_and_kernel():
    s = transposition(7, 0, 1)
    c5 = cycle(7, (0, 1, 2, 3, 4))
    z = transposition(7, 5, 6)
    G = schreier_stabilizer_chain((s, c5, z))
    images = (restrict(s, 5), restrict(c5, 5), identity(5))

    a3 = cycle(5, (0, 1, 2))
    a5 = cycle(5, (0, 1, 2, 3, 4))
    A5 = schreier_stabilizer_chain((a3, a5))
    assert A5.order == 60

    got = paired_action_subgroup_preimage(G, images, A5)
    assert got.status == "exact_paired_action_subgroup_preimage", got
    assert got.source_group_order == 240
    assert got.source_image_order == 120
    assert got.kernel_order == 2
    assert got.target_subgroup_order == 60
    assert got.preimage_subgroup_order == 120
    assert got.preimage_subgroup is not None
    assert len(got.paired_domain_generators) == len(got.paired_image_generators)

    regenerated_image = schreier_stabilizer_chain(got.paired_image_generators)
    assert regenerated_image.order == A5.order
    assert all(A5.contains(q) for q in got.paired_image_generators)


def test_target_subgroup_outside_source_image_is_exactly_rejected():
    c5d = cycle(6, (0, 1, 2, 3, 4))
    G = schreier_stabilizer_chain((c5d,))
    image_c5 = (restrict(c5d, 5),)
    A5 = schreier_stabilizer_chain(
        (cycle(5, (0, 1, 2)), cycle(5, (0, 1, 2, 3, 4)))
    )
    got = paired_action_subgroup_preimage(G, image_c5, A5)
    assert got.status == "target_subgroup_outside_image", got
    assert got.preimage_subgroup is None


def test_bad_generator_pairing_fails_before_recursive_preimage_is_claimed():
    s = transposition(3, 0, 1)
    t = transposition(3, 1, 2)
    G = schreier_stabilizer_chain((s, t))
    q = transposition(5, 0, 1)
    trivial = schreier_stabilizer_chain((identity(5),))
    with pytest.raises(ValueError, match="well-defined action homomorphism"):
        paired_action_subgroup_preimage(G, (q, identity(5)), trivial)
