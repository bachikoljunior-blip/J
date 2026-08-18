from jagi.learning.runtime_grammar import RuntimeOperator, synthesize_runtime_grammar


def test_post_implementation_numeric_operators_can_define_new_search_grammar():
    operators = [
        RuntimeOperator("square", ("number",), "number", lambda x: x * x),
        RuntimeOperator("add", ("number", "number"), "number", lambda a, b: a + b),
    ]
    examples = [(1, 2), (2, 5), (4, 17)]
    result = synthesize_runtime_grammar(examples, input_type="number", output_type="number", operators=operators, constants=[("number", 1)], max_cost=4)
    assert result.expression is not None
    op_map = {o.name: o for o in operators}
    assert result.expression.evaluate(7, op_map) == 50


def test_runtime_grammar_handles_non_numeric_string_domain():
    operators = [
        RuntimeOperator("reverse", ("text",), "text", lambda s: s[::-1]),
        RuntimeOperator("wrap", ("text",), "text", lambda s: "<" + s + ">"),
    ]
    examples = [("ab", "<ba>"), ("cat", "<tac>")]
    result = synthesize_runtime_grammar(examples, input_type="text", output_type="text", operators=operators, max_cost=3)
    assert result.expression is not None
    op_map = {o.name: o for o in operators}
    assert result.expression.evaluate("owl", op_map) == "<lwo>"


def test_missing_operator_budget_returns_unresolved():
    operators = [RuntimeOperator("double", ("number",), "number", lambda x: x * 2)]
    result = synthesize_runtime_grammar([(1, 3), (2, 5)], input_type="number", output_type="number", operators=operators, max_cost=2)
    assert result.expression is None
