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


def _half_cycle_group(m=200):
    half = m // 2
    g = tuple(
        ((x + 1) % half) if x < half else half + ((x - half + 1) % half)
        for x in range(m)
    )
    return g, schreier_stabilizer_chain([g])


def _step_two_group(m=200):
    g = tuple((x + 2) % m for x in range(m))
    return g, schreier_stabilizer_chain([g])


def _alternating_windows(m=200, t=20):
    return [
        (tuple((i + j) % m for j in range(t)), i % 2)
        for i in range(m)
    ]


def test_certificate_incidence_finds_label_invariant_significant_split():
    n = m = 200
    t = 20
    certificates = (
        _cyclic_windows(range(0, 100), t, "left-certificate")
        + _cyclic_windows(range(100, 200), t, "right-certificate")
    )
    g, action = _half_cycle_group(m)
    got = certificate_incidence_descent(
        n, m, t, certificates,
        canonical_action_group=action,
        certificate_tokens_canonical=True,
    )
    assert got.status == "certified_significant_point_split", got
    assert got.significant_split and got.exact_invariant and got.local_cost_certified
    assert got.canonical_inputs_certified
    assert sorted(map(len, got.color_classes)) == [100, 100]
    assert got.certificate_rank == 2
    assert got.local_log2_cost_bound <= got.allowed_local_log2_work

    p = list(range(m))
    random.Random(184).shuffle(p)
    relabeled_action = schreier_stabilizer_chain([_conjugate(g, p)])
    relabeled = certificate_incidence_descent(
        n, m, t, _relabel(certificates, p),
        canonical_action_group=relabeled_action,
        certificate_tokens_canonical=True,
    )
    assert relabeled.status == got.status
    expected = {frozenset(p[x] for x in cls) for cls in got.color_classes}
    assert _classes_as_sets(relabeled) == expected


def test_homogeneous_points_preserve_nontrivial_higher_arity_relation():
    n = m = 200
    t = 20
    certificates = _alternating_windows(m, t)
    _, action = _step_two_group(m)
    got = certificate_incidence_descent(
        n, m, t, certificates,
        canonical_action_group=action,
        certificate_tokens_canonical=True,
    )
    assert got.status == "certified_homogeneous_nontrivial_relation", got
    assert got.homogeneous_nontrivial_relation
    assert not got.significant_split
    assert len(got.color_classes) == 1 and len(got.color_classes[0]) == m
    assert got.certificate_rank == 2


def test_theorem_window_measure_and_action_invariance_fail_closed():
    certificates = _alternating_windows()
    _, step_two = _step_two_group()
    too_large_n = certificate_incidence_descent(
        2 ** 20, 200, 20, certificates,
        canonical_action_group=step_two,
        certificate_tokens_canonical=True,
    )
    assert too_large_n.status == "theorem_parameter_gate_failed"
    assert not too_large_n.exact_invariant and not too_large_n.local_cost_certified

    invalid_measure = certificate_incidence_descent(
        199, 200, 20, certificates,
        canonical_action_group=step_two,
        certificate_tokens_canonical=True,
    )
    assert invalid_measure.status == "invalid_recurrence_measure"

    step_one = schreier_stabilizer_chain([tuple((x + 1) % 200 for x in range(200))])
    noninvariant = certificate_incidence_descent(
        200, 200, 20, certificates,
        canonical_action_group=step_one,
        certificate_tokens_canonical=True,
    )
    assert noninvariant.status == "colored_test_family_not_invariant"
    assert noninvariant.theorem_gate_certified
    assert not noninvariant.canonical_inputs_certified
    assert not noninvariant.exact_invariant

    uncertified_tokens = certificate_incidence_descent(
        200, 200, 20, certificates,
        canonical_action_group=step_two,
        certificate_tokens_canonical=False,
    )
    assert uncertified_tokens.status == "uncertified_certificate_tokens"
    assert not uncertified_tokens.exact_invariant


def test_duplicate_resource_and_qpoly_accounting_fail_closed():
    trivial_action = schreier_stabilizer_chain([identity(200)])
    duplicate = [(tuple(range(20)), "a"), (tuple(range(20)), "b")]
    got = certificate_incidence_descent(
        200, 200, 20, duplicate,
        canonical_action_group=trivial_action,
        certificate_tokens_canonical=True,
    )
    assert got.status == "duplicate_test_set"

    certificates = _alternating_windows()
    _, step_two = _step_two_group()
    resource = certificate_incidence_descent(
        200, 200, 20, certificates,
        canonical_action_group=step_two,
        certificate_tokens_canonical=True,
        max_certificates=100,
    )
    assert resource.status == "certificate_resource_limit_exceeded"

    overcharged = certificate_incidence_descent(
        200, 200, 20, certificates,
        canonical_action_group=step_two,
        certificate_tokens_canonical=True,
        quasipoly_power=1,
        quasipoly_constant=0.01,
    )
    assert overcharged.status == "quasipolynomial_local_bound_exceeded"
    assert overcharged.exact_invariant and not overcharged.local_cost_certified
