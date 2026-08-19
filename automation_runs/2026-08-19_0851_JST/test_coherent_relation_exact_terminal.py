from itertools import combinations

from coherent_relation_exact_terminal import canonicalize_pair_relation_terminal


def cycle_distance_weights(n):
    return tuple(
        ((u, v), min((u - v) % n, (v - u) % n))
        for u, v in combinations(range(n), 2)
    )


def test_cyclic_distance_relation_has_exact_relabeling_invariant_terminal_code():
    n = 7
    weights = dict(cycle_distance_weights(n))
    base = canonicalize_pair_relation_terminal(n, tuple(weights.items()))
    assert base.status == "exact_pair_relation_canonical_code"

    p = tuple(reversed(range(n)))
    moved = []
    for (u, v), w in weights.items():
        a, b = sorted((p[u], p[v]))
        moved.append(((a, b), w))
    again = canonicalize_pair_relation_terminal(n, moved)
    assert again.status == "exact_pair_relation_canonical_code"
    assert again.canonical_code == base.canonical_code
    assert again.automorphism_order == base.automorphism_order


def test_size_limit_fails_closed_before_quadratic_expansion():
    n = 25
    weights = tuple(((u, v), 0) for u, v in combinations(range(n), 2))
    r = canonicalize_pair_relation_terminal(n, weights, max_quotient_size=24)
    assert r.status == "undetermined_size_limit"
    assert r.canonical_code is None
