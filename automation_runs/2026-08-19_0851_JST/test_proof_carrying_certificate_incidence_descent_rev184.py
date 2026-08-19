import random

from proof_carrying_certificate_incidence_descent_v1 import certificate_incidence_descent


def _cyclic_windows(points, width, token):
    pts = tuple(points)
    return [
        (tuple(pts[(i + j) % len(pts)] for j in range(width)), token)
        for i in range(len(pts))
    ]


def _relabel(certificates, p):
    return [(tuple(p[x] for x in T), token) for T, token in certificates]


def _classes_as_sets(result):
    return {frozenset(xs) for xs in result.color_classes}


def test_certificate_incidence_finds_label_invariant_significant_split():
    m = 100
    t = 10
    certificates = (
        _cyclic_windows(range(0, 50), t, "left-certificate")
        + _cyclic_windows(range(50, 100), t, "right-certificate")
    )
    got = certificate_incidence_descent(
        64, m, t, certificates,
        test_family_canonical=True,
        certificate_tokens_canonical=True,
    )
    assert got.status == "certified_significant_point_split", got
    assert got.significant_split and got.exact_invariant and got.local_cost_certified
    assert sorted(map(len, got.color_classes)) == [50, 50]
    assert got.certificate_rank == 2

    p = list(range(m))
    random.Random(184).shuffle(p)
    relabeled = certificate_incidence_descent(
        64, m, t, _relabel(certificates, p),
        test_family_canonical=True,
        certificate_tokens_canonical=True,
    )
    assert relabeled.status == got.status
    expected = {frozenset(p[x] for x in cls) for cls in got.color_classes}
    assert _classes_as_sets(relabeled) == expected


def test_homogeneous_points_preserve_nontrivial_higher_arity_relation():
    m = 100
    t = 10
    certificates = [
        (tuple((i + j) % m for j in range(t)), i % 2)
        for i in range(m)
    ]
    got = certificate_incidence_descent(
        64, m, t, certificates,
        test_family_canonical=True,
        certificate_tokens_canonical=True,
    )
    assert got.status == "certified_homogeneous_nontrivial_relation", got
    assert got.homogeneous_nontrivial_relation
    assert not got.significant_split
    assert len(got.color_classes) == 1 and len(got.color_classes[0]) == m
    assert got.certificate_rank == 2


def test_theorem_window_and_canonical_input_proofs_fail_closed():
    certificates = [
        (tuple((i + j) % 100 for j in range(10)), i % 2)
        for i in range(100)
    ]
    too_large_n = certificate_incidence_descent(
        2 ** 20, 100, 10, certificates,
        test_family_canonical=True,
        certificate_tokens_canonical=True,
    )
    assert too_large_n.status == "theorem_parameter_gate_failed"
    assert not too_large_n.exact_invariant and not too_large_n.local_cost_certified

    noncanonical = certificate_incidence_descent(
        64, 100, 10, certificates,
        test_family_canonical=False,
        certificate_tokens_canonical=True,
    )
    assert noncanonical.status == "uncertified_canonical_inputs"
    assert noncanonical.theorem_gate_certified
    assert not noncanonical.exact_invariant


def test_duplicate_tests_and_polynomial_count_accounting_fail_closed():
    duplicate = [(tuple(range(10)), "a"), (tuple(range(10)), "b")]
    got = certificate_incidence_descent(
        64, 100, 10, duplicate,
        test_family_canonical=True,
        certificate_tokens_canonical=True,
    )
    assert got.status == "duplicate_test_set"

    many = [
        (tuple((i + j) % 100 for j in range(10)), i)
        for i in range(100)
    ]
    capped = certificate_incidence_descent(
        64, 100, 10, many,
        test_family_canonical=True,
        certificate_tokens_canonical=True,
        certificate_count_poly_power=1,
    )
    assert capped.status == "uncertified_certificate_count_cost"
    assert capped.theorem_gate_certified and capped.canonical_inputs_certified
    assert not capped.exact_invariant and not capped.local_cost_certified
