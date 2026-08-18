from jagi.learning.runtime_grammar import RuntimeOperator, synthesize_runtime_grammar
from jagi_eval.microdomain import CandidateTaskView, HiddenCase, OperatorView, SealedMicroDomain, score_microdomain


def task():
    operators = (
        OperatorView("square", ("number",), "number", lambda x: x * x),
        OperatorView("add", ("number", "number"), "number", lambda a, b: a + b),
    )
    view = CandidateTaskView(
        "fresh-domain-1",
        "number",
        "number",
        ((1, 2), (2, 5), (4, 17)),
        operators,
        (("number", 1),),
        4,
    )
    return SealedMicroDomain(view, (HiddenCase(7, 50), HiddenCase(10, 101)))


def candidate_solver(view):
    runtime_ops = [RuntimeOperator(op.name, op.input_types, op.output_type, op.callable) for op in view.operators]
    result = synthesize_runtime_grammar(
        view.demonstrations,
        input_type=view.input_type,
        output_type=view.output_type,
        operators=runtime_ops,
        constants=view.constants,
        max_cost=view.max_program_cost,
    )
    if result.expression is None:
        return None
    op_map = {op.name: op for op in runtime_ops}
    return lambda x: result.expression.evaluate(x, op_map)


def test_candidate_view_has_no_hidden_cases_or_answers():
    sealed = task()
    assert not hasattr(sealed.view, "hidden_cases")
    assert not hasattr(sealed.view, "expected_output")


def test_evaluator_scores_hidden_cases_after_candidate_returns_predictor():
    score = score_microdomain(task(), candidate_solver)
    assert score.solved
    assert score.correct == score.total == 2


def test_unresolved_candidate_scores_failure_without_answer_leakage():
    score = score_microdomain(task(), lambda view: None)
    assert not score.solved
    assert score.error == "unresolved"
