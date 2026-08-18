from jagi.learning.compositional_search import synthesize_numeric_expression


def test_compositional_search_discovers_rule_not_in_single_step_dsl():
    result = synthesize_numeric_expression([(1, 3), (2, 5), (4, 9)], max_cost=7)
    assert result.expression is not None
    assert [result.expression.evaluate(x) for x in (3, 10)] == [7, 21]
    assert result.expression.cost <= 7


def test_behavioral_pruning_keeps_search_bounded():
    result = synthesize_numeric_expression([(1, 4), (2, 6), (3, 8)], max_cost=7, beam_per_cost=500)
    assert result.expression is not None
    assert result.explored_behaviors < 10_000


def test_search_returns_unresolved_instead_of_fabricating_when_budget_is_too_small():
    result = synthesize_numeric_expression([(1, 7), (2, 13), (3, 19)], max_cost=3)
    assert result.expression is None
    assert result.max_cost_reached == 3
