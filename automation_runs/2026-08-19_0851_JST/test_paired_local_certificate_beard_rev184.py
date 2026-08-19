from paired_local_certificate_beard_v1 import paired_local_certificate_beard
from permutation_group_schreier import schreier_stabilizer_chain


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


def test_uniform_s9_instance_reaches_exact_stable_fullness_but_not_outer_theorem_window():
    s = transposition(9, 0, 1)
    c = cycle(9, tuple(range(9)))
    G = schreier_stabilizer_chain((s, c))
    got = paired_local_certificate_beard(
        G, (s, c), (0,) * 9, tuple(range(9))
    )
    assert got.status == "certified_full_by_stable_paired_beard", got
    assert got.full is True
    assert got.full_automorphism_subgroup is not None
    assert got.full_automorphism_subgroup.order == 181440  # A9
    assert len(got.layers) == 1
    assert got.layers[0].giant_type_after == "A_m"
    # |T|=9 cannot satisfy |T|<=m/10 when the outer structural degree is also 9.
    assert not got.parameter_gate.certified
    assert not got.theorem_scale_recurrence_evidence


def test_distinguished_point_breaks_a5_image_and_certifies_nonfullness():
    s = transposition(6, 0, 1)
    c = cycle(6, (0, 1, 2, 3, 4, 5))
    G = schreier_stabilizer_chain((s, c))
    values = (1, 0, 0, 0, 0, 7)
    got = paired_local_certificate_beard(
        G, (s, c), values, (0, 1, 2, 3, 4),
        max_quotient_leaves=100,
    )
    assert got.status == "certified_nonfull_giant_obstruction", got
    assert got.full is False
    assert got.final_group is not None
    assert got.layers
    assert got.layers[-1].giant_type_after is None
    assert got.layers[-1].structural_image_order_after == 12  # A4 point stabilizer
    assert not got.theorem_scale_recurrence_evidence


def test_paired_beard_search_limit_fails_closed():
    s = transposition(6, 0, 1)
    c = cycle(6, (0, 1, 2, 3, 4, 5))
    G = schreier_stabilizer_chain((s, c))
    got = paired_local_certificate_beard(
        G, (s, c), (1, 0, 0, 0, 0, 7), (0, 1, 2, 3, 4),
        max_quotient_leaves=5,
    )
    assert got.status == "undetermined_quotient_leaf_limit", got
    assert got.full is None
    assert got.full_automorphism_subgroup is None
    assert not got.theorem_scale_recurrence_evidence
