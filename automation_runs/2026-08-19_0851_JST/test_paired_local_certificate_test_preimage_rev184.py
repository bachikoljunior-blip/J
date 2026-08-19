from paired_giant_action_certificates_v1 import analyze_paired_giant_action
from paired_local_certificate_test_preimage_v1 import paired_local_certificate_test_preimage
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


def test_exact_embedded_a5_preimage_and_compressed_pairing():
    # S6 structural image with an independent invisible C2 kernel.
    s = transposition(8, 0, 1)
    c6 = cycle(8, (0, 1, 2, 3, 4, 5))
    z = transposition(8, 6, 7)
    G = schreier_stabilizer_chain((s, c6, z))
    images = (restrict(s, 6), restrict(c6, 6), identity(6))

    got = paired_local_certificate_test_preimage(G, images, (0, 1, 2, 3, 4))
    assert got.status == "exact_paired_test_alternating_preimage", got
    assert got.source_group_order == 1440
    assert got.source_image_order == 720
    assert got.source_kernel_order == 2
    assert got.test_alternating_order == 60
    assert got.preimage_group_order == 120
    assert got.preimage_group is not None

    local = schreier_stabilizer_chain(got.paired_test_image_generators)
    assert local.order == 60
    audit = analyze_paired_giant_action(
        got.preimage_group, got.paired_test_image_generators
    )
    assert audit.status == "exact_paired_giant_action_certificate", audit
    assert audit.giant_type == "A_m"
    assert audit.image_order == 60
    assert audit.kernel_order == 2


def test_missing_a5_in_cyclic_structural_image_is_rejected():
    c6 = cycle(7, (0, 1, 2, 3, 4, 5))
    G = schreier_stabilizer_chain((c6,))
    got = paired_local_certificate_test_preimage(
        G, (restrict(c6, 6),), (0, 1, 2, 3, 4)
    )
    assert got.status == "test_alternating_subgroup_outside_image", got
    assert got.preimage_group is None
