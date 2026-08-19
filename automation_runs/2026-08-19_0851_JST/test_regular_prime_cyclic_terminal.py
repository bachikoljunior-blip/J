from itertools import combinations, permutations
import random

from permutation_group_schreier import compose, inverse, schreier_stabilizer_chain
from regular_prime_cyclic_terminal import canonicalize_regular_prime_subset_relation


def cycle_group(n):
    cycle = tuple((i + 1) % n for i in range(n))
    return cycle, schreier_stabilizer_chain([cycle])


def conjugate_by_relabeling(g, q):
    # q maps old labels to new labels, so g' satisfies g'(q(i)) = q(g(i)).
    return compose(compose(inverse(q), g), q)


def relabel_relation(relation, q):
    return tuple((tuple(sorted(q[x] for x in T)), flag) for T, flag in relation)


def test_all_120_relabelings_of_c5_have_identical_canonical_code():
    n = 5
    cycle, G = cycle_group(n)
    relation = tuple(
        (T, ((sum(T) * 7 + T[0] * 3 + T[-1]) % 3) == 0)
        for T in combinations(range(n), 3)
    )
    base = canonicalize_regular_prime_subset_relation(G, relation)
    assert base.status == "exact_regular_prime_cyclic_subset_terminal"
    assert base.coordinate_systems_checked == 20

    checked = 0
    for q in permutations(range(n)):
        Gq = schreier_stabilizer_chain([conjugate_by_relabeling(cycle, q)])
        rq = canonicalize_regular_prime_subset_relation(Gq, relabel_relation(relation, q))
        assert rq.status == base.status
        assert rq.canonical_code == base.canonical_code
        checked += 1
    assert checked == 120


def test_c29_terminal_checks_all_812_affine_coordinate_systems_and_survives_arbitrary_relabeling():
    n = 29
    cycle, G = cycle_group(n)
    relation = tuple((T, False) for T in combinations(range(n), 3))
    base = canonicalize_regular_prime_subset_relation(G, relation)
    assert base.status == "exact_regular_prime_cyclic_subset_terminal"
    assert base.coordinate_systems_checked == n * (n - 1) == 812
    assert base.canonical_code is not None

    q = list(range(n))
    random.Random(136).shuffle(q)
    q = tuple(q)
    Gq = schreier_stabilizer_chain([conjugate_by_relabeling(cycle, q)])
    rq = canonicalize_regular_prime_subset_relation(Gq, relabel_relation(relation, q))
    assert rq.canonical_code == base.canonical_code


def test_coordinate_bound_fails_closed_without_a_code():
    n = 29
    _, G = cycle_group(n)
    relation = tuple((T, False) for T in combinations(range(n), 3))
    r = canonicalize_regular_prime_subset_relation(
        G, relation, max_coordinate_systems=100
    )
    assert r.status == "undetermined_coordinate_system_limit"
    assert r.canonical_code is None
    assert r.coordinate_systems_checked == 0


def test_composite_degree_cycle_is_not_misclassified_as_prime_regular_terminal():
    _, G = cycle_group(8)
    relation = tuple((T, False) for T in combinations(range(8), 3))
    r = canonicalize_regular_prime_subset_relation(G, relation)
    assert r.status == "not_regular_prime_cyclic"
    assert r.canonical_code is None
