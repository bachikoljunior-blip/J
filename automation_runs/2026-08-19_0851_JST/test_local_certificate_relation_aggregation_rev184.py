from itertools import combinations

from local_certificate_relation_aggregation_v1 import aggregate_local_certificate_relation


def relabel_sets(test_sets, p):
    return tuple(tuple(sorted(p[x] for x in T)) for T in test_sets)


def mapped_cells(cells, p):
    return {tuple(sorted(p[x] for x in C)) for C in cells}


def test_complete_higher_arity_relation_yields_canonical_significant_point_split():
    m, t = 8, 3
    sets = tuple(combinations(range(m), t))
    # Canonical toy certificate relation: a test-set color records how many points
    # it contains from an unlabeled 3/5 structural block.  This is exactly the type
    # of higher-arity relation-to-incidence projection rev184 must preserve.
    A = {0, 1, 2}
    tokens = tuple(sum(x in A for x in T) for T in sets)
    got = aggregate_local_certificate_relation(m, sets, tokens, shrink_fraction=0.9)
    assert got.status == "canonical_significant_point_split_from_local_certificates", got
    assert got.relation_rank == 4
    assert set(got.point_cells) == {(0, 1, 2), (3, 4, 5, 6, 7)}
    assert got.largest_point_cell == 5
    assert got.significant_split


def test_aggregation_is_equivariant_under_arbitrary_quotient_relabeling():
    m, t = 8, 3
    sets = tuple(combinations(range(m), t))
    A = {0, 1, 2}
    tokens_by_set = {T: sum(x in A for x in T) for T in sets}
    base = aggregate_local_certificate_relation(
        m, sets, tuple(tokens_by_set[T] for T in sets)
    )

    p = (5, 2, 7, 0, 6, 3, 1, 4)
    relabeled = relabel_sets(sets, p)
    relabeled_tokens = tuple(tokens_by_set[T] for T in sets)
    got = aggregate_local_certificate_relation(m, relabeled, relabeled_tokens)
    assert got.status == base.status
    assert mapped_cells(base.point_cells, p) == set(got.point_cells)


def test_nontrivial_homogeneous_relation_is_preserved_for_design_descent():
    m, t = 7, 2
    sets = tuple(combinations(range(m), t))
    # Cycle-edge/non-edge coloring is nontrivial but every point has the same
    # incidence histogram, so first-order point profiles cannot split the points.
    edges = {
        tuple(sorted((i, (i + 1) % m)))
        for i in range(m)
    }
    tokens = tuple(T in edges for T in sets)
    got = aggregate_local_certificate_relation(m, sets, tokens)
    assert got.status == "homogeneous_nontrivial_local_certificate_relation_requires_design_descent", got
    assert got.relation_rank == 2
    assert got.point_cells == (tuple(range(m)),)
    assert not got.significant_split


def test_partial_test_set_sampling_fails_closed():
    m, t = 8, 3
    sets = tuple(combinations(range(m), t))
    got = aggregate_local_certificate_relation(m, sets[:-1], (0,) * (len(sets) - 1))
    assert got.status == "incomplete_local_certificate_relation", got
    assert not got.significant_split
    assert got.test_sets_checked + 1 == got.expected_test_sets
