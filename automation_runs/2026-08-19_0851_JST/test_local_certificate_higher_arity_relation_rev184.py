from itertools import combinations

from local_certificate_higher_arity_relation_v1 import aggregate_local_certificate_relation


def complete_relation(m, k, token_fn):
    return tuple((T, token_fn(T)) for T in combinations(range(m), k))


def class_sets(result):
    return {frozenset(C) for C in result.color_classes}


def test_exact_incidence_relation_produces_significant_point_split():
    m, k = 8, 2
    left = {0, 1, 2, 3}
    relation = complete_relation(m, k, lambda T: int(set(T) <= left))
    got = aggregate_local_certificate_relation(64, m, k, relation)
    assert got.status == "certified_significant_point_split", got
    assert got.complete_test_family
    assert got.significant_point_split
    assert got.largest_color_class == 4
    assert class_sets(got) == {frozenset(left), frozenset(set(range(m)) - left)}
    assert not got.local_certificate_parameter_gate.certified
    assert not got.theorem_scale_recurrence_evidence


def test_regular_nontrivial_relation_reaches_design_gate_without_fake_theorem_scale():
    m, k = 8, 2
    cycle_edges = {
        tuple(sorted((i, (i + 1) % m)))
        for i in range(m)
    }
    relation = complete_relation(m, k, lambda T: int(T in cycle_edges))
    got = aggregate_local_certificate_relation(64, m, k, relation)
    assert got.status == "certified_higher_arity_relation_for_design_lemma", got
    assert got.relation_rank == 2
    assert not got.significant_point_split
    assert got.design_lemma_parameter_gate
    assert got.relative_strong_symmetry_defect >= 0.25
    assert not got.theorem_scale_recurrence_evidence


def test_uniform_relation_is_fail_closed():
    relation = complete_relation(7, 3, lambda _T: "same")
    got = aggregate_local_certificate_relation(64, 7, 3, relation)
    assert got.status == "uniform_certificate_relation_no_progress", got
    assert got.relation_rank == 1
    assert not got.significant_point_split
    assert not got.theorem_scale_recurrence_evidence


def test_sparse_relation_is_not_promoted_to_canonical_structure():
    relation = complete_relation(7, 3, lambda T: sum(T) % 2)[:-1]
    got = aggregate_local_certificate_relation(64, 7, 3, relation)
    assert got.status == "undetermined_incomplete_certificate_family", got
    assert not got.complete_test_family
    assert not got.theorem_scale_recurrence_evidence


def test_theorem_window_can_be_certified_while_resource_limit_stays_fail_closed():
    # For n=64 the strict lower theorem threshold is 8 and m/10 is 9, so k=9
    # lies exactly in the local-certificate theorem window.  C(90,9) is far too
    # large for this regression and must be rejected before relation materialization.
    got = aggregate_local_certificate_relation(
        64, 90, 9, (), max_test_sets=1000
    )
    assert got.status == "undetermined_certificate_family_limit", got
    assert got.local_certificate_parameter_gate.certified
    assert got.logarithmic_test_size_certified
    assert not got.theorem_scale_recurrence_evidence
    assert got.relation == ()


def test_incidence_partition_is_equivariant_under_ground_relabeling():
    m, k = 8, 2
    left = {0, 1, 2, 3}
    relation = complete_relation(m, k, lambda T: int(set(T) <= left))
    base = aggregate_local_certificate_relation(64, m, k, relation)

    q = (4, 6, 0, 2, 7, 1, 5, 3)
    relabeled = tuple(
        (tuple(sorted(q[x] for x in T)), token)
        for T, token in relation
    )
    got = aggregate_local_certificate_relation(64, m, k, relabeled)
    mapped_classes = {frozenset(q[x] for x in C) for C in base.color_classes}
    assert got.status == base.status
    assert class_sets(got) == mapped_classes
    assert got.relative_strong_symmetry_defect == base.relative_strong_symmetry_defect
