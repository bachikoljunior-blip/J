from __future__ import annotations

from fractions import Fraction
from random import Random

from jagi.learning.compositional_search import Add, Input, Multiply, NumberConst, synthesize_numeric_expression


def random_expr(rng: Random, cost: int):
    if cost <= 1:
        return Input() if rng.random() < 0.45 else NumberConst(Fraction(rng.choice([-2, -1, 0, 1, 2, 3])))
    pairs = [(left, cost - left - 1) for left in range(1, cost) if cost - left - 1 >= 1]
    if not pairs:
        return random_expr(rng, 1)
    left_cost, right_cost = rng.choice(pairs)
    left = random_expr(rng, left_cost)
    right = random_expr(rng, right_cost)
    return Add(left, right) if rng.random() < 0.5 else Multiply(left, right)


def run(cost: int, trials: int, seed: int, beam: int = 2000) -> dict[str, float | int]:
    rng = Random(seed)
    found = generalized = 0
    explored: list[int] = []
    for _ in range(trials):
        target = random_expr(rng, cost)
        examples = [(x, target.evaluate(x)) for x in (1, 2, 4)]
        result = synthesize_numeric_expression(examples, max_cost=cost, beam_per_cost=beam)
        explored.append(result.explored_behaviors)
        if result.expression is not None:
            found += 1
            if all(result.expression.evaluate(x) == target.evaluate(x) for x in (3, 5, 7, 11)):
                generalized += 1
    return {
        "cost": cost,
        "trials": trials,
        "found": found,
        "generalized": generalized,
        "mean_explored_behaviors": sum(explored) / len(explored),
        "max_explored_behaviors": max(explored),
    }


if __name__ == "__main__":
    for cost, trials in ((3, 30), (5, 30), (7, 30), (9, 10), (11, 10)):
        print(run(cost, trials, seed=100 + cost))
