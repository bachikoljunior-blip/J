from dataclasses import replace

from aggregate_local_certificate_relation import aggregate_fullness_relation
from local_certificate_exact_twl_design_si_v1 import (
    _complete_boolean_palette,
    local_certificate_exact_twl_design_string_isomorphism,
)
from permutation_group_schreier import schreier_stabilizer_chain


def _singletons(n):
    return tuple((i,) for i in range(n))


def test_complete_aggregate_order_is_certified_and_corruption_fails_closed():
    cycle = (1, 2, 3, 4, 5, 6, 0)
    group = schreier_stabilizer_chain((cycle,))
    relation = aggregate_fullness_relation(
        group, _singletons(7), (0,) * 7, test_size=3
    )
    assert _complete_boolean_palette(relation) == (False,) * relation.test_count

    corrupted = replace(relation, relation=tuple(reversed(relation.relation)))
    assert _complete_boolean_palette(corrupted) is None


def test_actual_no_split_relation_reaches_design_gate_and_stays_fail_closed():
    cycle = (1, 2, 3, 4, 5, 6, 0)
    group = schreier_stabilizer_chain((cycle,))
    got = local_certificate_exact_twl_design_string_isomorphism(
        group,
        _singletons(7),
        (0,) * 7,
        (0,) * 7,
        root_n=7,
        test_size=3,
        max_group_order=16,
    )
    assert got.source_relation.status == "canonical_relation_no_significant_split"
    assert got.target_relation.status == "canonical_relation_no_significant_split"
    assert got.relation_order_certified
    assert got.design_result is not None
    assert got.design_result.status == "undetermined_exact_twl_design_branch_plan"
    assert not got.design_result.theorem_hypotheses_certified
    assert not got.exact and not got.complete


def test_existing_significant_split_is_not_relabelled_as_design_progress():
    alternating_three = (1, 2, 0, 3)
    transposition = (1, 0, 2, 3)
    group = schreier_stabilizer_chain((alternating_three, transposition))
    got = local_certificate_exact_twl_design_string_isomorphism(
        group,
        _singletons(4),
        (0,) * 4,
        (0,) * 4,
        root_n=4,
        test_size=3,
        max_group_order=16,
    )
    assert got.source_relation.significant_split
    assert got.target_relation.significant_split
    assert got.status == "local_certificate_split_precedes_design"
    assert got.design_result is None
    assert got.relation_order_certified
    assert not got.exact and not got.complete
