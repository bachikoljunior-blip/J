from cartesian_string_marginal_filter_v1 import cartesian_string_marginal_filter
from permutation_group_schreier import schreier_stabilizer_chain


def cycle(m):
    return tuple((i + 1) % m for i in range(m))


def swap(m):
    p = list(range(m))
    p[0], p[1] = p[1], p[0]
    return tuple(p)


def product_action_generator(m, factor, p):
    out = list(range(m * m))
    for a in range(m):
        for b in range(m):
            aa, bb = (p[a], b) if factor == 0 else (a, p[b])
            out[a * m + b] = aa * m + bb
    return tuple(out)


def product_symmetric_group(m):
    return schreier_stabilizer_chain([
        product_action_generator(m, 0, cycle(m)),
        product_action_generator(m, 0, swap(m)),
        product_action_generator(m, 1, cycle(m)),
        product_action_generator(m, 1, swap(m)),
    ])


def relabel_target(source, p):
    inv = [0] * len(p)
    for i, j in enumerate(p):
        inv[j] = i
    return tuple(source[inv[j]] for j in range(len(p)))


def test_row_versus_diagonal_shape_is_exactly_rejected_by_reduced_marginals():
    m = 5
    G = product_symmetric_group(m)
    source = tuple(1 if a == 0 else 0 for a in range(m) for b in range(m))
    target = tuple(1 if a == b else 0 for a in range(m) for b in range(m))
    assert sum(source) == sum(target) == 5

    got = cartesian_string_marginal_filter(
        G,
        source,
        target,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=256,
    )
    assert got.status == "exact_empty_cartesian_marginal"
    assert got.exact_empty
    assert got.reduced_exact
    assert not got.reduced_candidate_nonempty
    assert got.original_degree == 25
    assert got.reduced_degree == 10
    assert got.reduced_proof is not None and got.reduced_proof.coset is None


def test_true_product_action_isomorphism_survives_as_candidate_not_false_success():
    m = 5
    G = product_symmetric_group(m)
    source = tuple((a + 2 * b) % 3 for a in range(m) for b in range(m))
    p = product_action_generator(m, 0, cycle(m))
    target = relabel_target(source, p)

    got = cartesian_string_marginal_filter(
        G,
        source,
        target,
        root_n=64,
        max_explicit_degree=8,
        max_group_order=256,
    )
    assert got.status == "cartesian_marginal_candidate_requires_exact_lift"
    assert not got.exact_empty
    assert got.reduced_exact
    assert got.reduced_candidate_nonempty
    assert got.reduced_proof is not None and got.reduced_proof.coset is not None


def test_noncartesian_family_does_not_use_the_filter():
    a = (1, 0, 3, 2)
    b = (2, 3, 0, 1)
    G = schreier_stabilizer_chain([a, b])
    got = cartesian_string_marginal_filter(G, (0, 1, 0, 1), (0, 1, 0, 1), root_n=8)
    assert got.status == "cartesian_marginal_filter_unavailable"
    assert not got.exact_empty
    assert got.reduced_proof is None
