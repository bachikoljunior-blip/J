import pytest

from paired_action_element_image_v1 import paired_action_image_of_element
from permutation_group_schreier import compose, identity, schreier_stabilizer_chain


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


def test_arbitrary_source_element_is_mapped_to_exact_structural_image():
    s = transposition(7, 0, 1)
    c = cycle(7, (0, 1, 2, 3, 4))
    z = transposition(7, 5, 6)
    G = schreier_stabilizer_chain((s, c, z))
    images = (restrict(s, 5), restrict(c, 5), identity(5))

    h = compose(compose(s, c), z)
    expected = compose(restrict(s, 5), restrict(c, 5))
    got = paired_action_image_of_element(G, images, h)
    assert got.status == "exact_paired_action_element_image", got
    assert got.image == expected

    invisible = paired_action_image_of_element(G, images, z)
    assert invisible.image == identity(5)
    assert invisible.kernel_order == 2


def test_source_element_outside_group_is_rejected_by_domain_sift():
    s = transposition(7, 0, 1)
    c = cycle(7, (0, 1, 2, 3, 4))
    z = transposition(7, 5, 6)
    G = schreier_stabilizer_chain((s, c, z))
    images = (restrict(s, 5), restrict(c, 5), identity(5))
    outside = transposition(7, 0, 5)
    got = paired_action_image_of_element(G, images, outside)
    assert got.status == "target_outside_source_group", got
    assert got.image is None


def test_inconsistent_pairing_is_rejected_before_element_image_is_claimed():
    s = transposition(3, 0, 1)
    t = transposition(3, 1, 2)
    G = schreier_stabilizer_chain((s, t))
    q = transposition(5, 0, 1)
    with pytest.raises(ValueError):
        paired_action_image_of_element(G, (q, identity(5)), identity(3))
