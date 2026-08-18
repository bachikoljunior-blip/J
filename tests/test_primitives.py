from fractions import Fraction

from jagi.learning.compositional_search import Add, Input, Multiply, NumberConst, synthesize_numeric_expression
from jagi.learning.primitives import PrimitiveLibrary


def quadratic_body():
    return Multiply(Add(Input(), NumberConst(Fraction(1))), Add(Input(), NumberConst(Fraction(2))))


def test_verified_subprogram_can_be_promoted_to_one_step_primitive():
    body = quadratic_body()
    examples = [(x, body.evaluate(x)) for x in (1, 2, 4)]
    library = PrimitiveLibrary()
    primitive = library.promote("shifted-product", body, examples)
    assert primitive.cost == 1
    assert primitive.evaluate(10) == body.evaluate(10)
    assert len(primitive.evidence_sha256) == 64


def test_learned_primitive_expands_effective_language_under_same_search_budget():
    body = quadratic_body()
    train = [(x, body.evaluate(x)) for x in (1, 2, 4)]
    library = PrimitiveLibrary()
    library.promote("shifted-product", body, train)
    target_examples = [(x, body.evaluate(x) + 1) for x in (1, 2, 4)]

    without = synthesize_numeric_expression(target_examples, max_cost=3)
    with_primitive = synthesize_numeric_expression(target_examples, max_cost=3, primitives=library.seeds())

    assert without.expression is None
    assert with_primitive.expression is not None
    assert with_primitive.expression.evaluate(7) == body.evaluate(7) + 1


def test_bad_evidence_prevents_promotion():
    library = PrimitiveLibrary()
    try:
        library.promote("bad", quadratic_body(), [(1, 999)])
    except ValueError:
        pass
    else:
        raise AssertionError("unverified primitive must not be promoted")
