import random

from permutation_group_schreier import identity, schreier_stabilizer_chain
from proof_carrying_certificate_incidence_descent_v1 import certificate_incidence_descent


def _cyclic_windows(points, width, token):
    pts = tuple(points)
    return [
        (tuple(pts[(i + j) % len(pts)] for j in range(width)), token)
        for i in range(len(pts))
    ]


def _relabel(certificates, p):
    return [(tuple(p[x] for x in T), token) for T, token in certificates]


def _conjugate(g, p):
    pinv = [0] * len(p)
    for x, y in enumerate(p):
        pinv[y] = x
    return tuple(p[g[pinv[x]]] for x in range(len(p)))


def _classes_as_sets(result):
    return {frozenset(xs) for xs in result.color_classes}


def _half_cycle_group(m=100):
    g = tuple(
        ((x + 1) % 50) if x < 50 else 50 + ((x - 50 + 1) % 50)
        for x in range(m)
    )
    return g, schreier_stabilizer_chain([g])


def _step_two_group(m=100):
    g = tuple((x + 2) % m for x in range(m))
    return g, schreier_stabilizer_chain([g])


def test_certificate_incidence_finds_label_invariant_significant_split():
    m = 100
    t = 10
    certificates = (
        _cyclic_windows(range(0, 50), t, "left-certificate")
        + _cyclic_windows(range(50, 100), t, "right-certificate")
    )
    g, action = _half_cycle_group(m)
    got = certificate_incidence_descent(
        64, m, t, certificates,
        canonical_action_group=action,
        certificate_tokens_canonical=True,
    )
    assert got.status == "certified_significant_point_split", got
    assert got.significant_split and got.exact_invariant and got.local_cost_certified
    assert got.canonical_inputs_certified
    assert sorted(map(len, got.color_classes)) == [50, 50]
    assert got.certificate_rank == 2

    p = list(range(m))
    random.Random(184).shuffle(p)
    relabeled_action = schreier_stabilizer_chain([_conjugate(g, p)])
    relabeled = certificate_incidence_descent(
        64, m, t, _relabel(certificates, p),
        canonical_action_group=relabeled_action,
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
    _, action = _step_two_group(m)
    got = certificate_incidence_descent(
        64, m, t, certificates,
        canonical_action_group=action,
        certificate_tokens_canonical=True,
    )
    assert got.status == "certified_homogeneous_nontrivial_relation", got
    assert got.homogeneous_nontrivial_relation
    assert not got.significant_split
    assert len(got.color_classes) == 1 and len(got.color_classes[0]) == m
    assert got.certificate_rank == 2


def test_theorem_window_and_action_invariance_fail_closed():
    certificates = [
        (tuple((i + j) % 100 for j in range(10)), i % 2)
        for i in range(100)
    ]
    _, step_two = _step_two_group(100)
    too_large_n = certificate_incidence_descent(
        2 ** 20, 100, 10, certificates,
        canonical_action_group=step_two,
        certificate_tokens_canonical=True,
    )
    assert too_large_n.status == "theorem_parameter_gate_failed"
    assert not too_large_n.exact_invariant and not too_large_n.local_cost_certified

    step_one = schreier_stabilizer_chain([tuple((x + 1) % 100 for x in range(100))])
    noninvariant = certificate_incidence_descent(
        64, 100, 10, certificates,
        canonical_action_group=step_one,
        certificate_tokens_canonical=True,
    )
    assert noninvariant.status == "colored_test_family_not_invariant"
    assert noninvariant.theorem_gate_certified
    assert not noninvariant.canonical_inputs_certified
    assert not noninvariant.exact_invariant

    uncertified_tokens = certificate_incidence_descent(
        64, 100, 10, certificates,
        canonical_action_group=step_two,
        certificate_tokens_canonical=False,
    )
    assert uncertified_tokens.status == "uncertified_certificate_tokens"
    assert not uncertified_tokens.exact_invariant


def test_duplicate_tests_and_polynomial_count_accounting_fail_closed():
    trivial_action = schreier_stabilizer_chain([identity(100)])
    duplicate = [(tuple(range(10)), "a"), (tuple(range(10)), "b")]
    got = certificate_incidence_descent(
        64, 100, 10, duplicate,
        canonical_action_group=trivial_action,
        certificate_tokens_canonical=True,
    )
    assert got.status == "duplicate_test_set"

    many = [
        (tuple((i + j) % 100 for j in range(10)), i % 2)
        for i in range(100)
    ]
    _, step_two = _step_two_group(100)
    capped = certificate_incidence_descent(
        64, 100, 10, many,
        canonical_action_group=step_two,
        certificate_tokens_canonical=True,
        certificate_count_poly_power=1,
    )
    assert capped.status == "uncertified_certificate_count_cost"
    assert capped.theorem_gate_certified
    assert not capped.exact_invariant and not capped.local_cost_certified
