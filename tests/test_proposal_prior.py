from fractions import Fraction

from jagi.learning.compositional_search import Add, Input, Multiply, NumberConst
from jagi.learning.proposal_prior import ProductionPrior, production_tokens


def useful_expression():
    return Add(Multiply(NumberConst(Fraction(2)), Input()), NumberConst(Fraction(1)))


def irrelevant_expression():
    return Multiply(NumberConst(Fraction(-2)), NumberConst(Fraction(-1)))


def test_verified_solution_updates_production_counts():
    prior = ProductionPrior()
    prior.observe_solution(useful_expression())
    assert prior.counts["add"] == 1
    assert prior.counts["mul"] == 1
    assert prior.counts["input"] == 1
    assert prior.counts["const:1"] == 1


def test_learned_prior_ranks_structurally_familiar_program_higher():
    prior = ProductionPrior(alpha=0.5)
    for _ in range(5):
        prior.observe_solution(useful_expression())
    ranked = prior.rank([irrelevant_expression(), useful_expression()])
    assert ranked[0] == useful_expression()


def test_prior_never_replaces_exact_evidence_consistency():
    prior = ProductionPrior()
    prior.observe_solution(useful_expression())
    expr = useful_expression()
    assert expr.evaluate(10) == 21
    assert "add" in production_tokens(expr)
