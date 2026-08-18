from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Hashable, Protocol, Sequence


class Expr(Protocol):
    cost: int
    type_name: str

    def evaluate(self, x: Any) -> Hashable:
        ...

    def render(self) -> str:
        ...


@dataclass(frozen=True)
class Input:
    cost: int = 1
    type_name: str = "number"

    def evaluate(self, x: Any) -> Hashable:
        return _number(x)

    def render(self) -> str:
        return "x"


@dataclass(frozen=True)
class NumberConst:
    value: Fraction
    cost: int = 1
    type_name: str = "number"

    def evaluate(self, x: Any) -> Hashable:
        return _compact(self.value)

    def render(self) -> str:
        return str(_compact(self.value))


@dataclass(frozen=True)
class Add:
    left: Expr
    right: Expr
    type_name: str = "number"

    @property
    def cost(self) -> int:
        return self.left.cost + self.right.cost + 1

    def evaluate(self, x: Any) -> Hashable:
        return _compact(_fraction(self.left.evaluate(x)) + _fraction(self.right.evaluate(x)))

    def render(self) -> str:
        return f"({self.left.render()}+{self.right.render()})"


@dataclass(frozen=True)
class Multiply:
    left: Expr
    right: Expr
    type_name: str = "number"

    @property
    def cost(self) -> int:
        return self.left.cost + self.right.cost + 1

    def evaluate(self, x: Any) -> Hashable:
        return _compact(_fraction(self.left.evaluate(x)) * _fraction(self.right.evaluate(x)))

    def render(self) -> str:
        return f"({self.left.render()}*{self.right.render()})"


@dataclass(frozen=True)
class SearchResult:
    expression: Expr | None
    explored_behaviors: int
    max_cost_reached: int


def synthesize_numeric_expression(
    examples: Sequence[tuple[Any, Any]],
    *,
    constants: Sequence[int | Fraction] = (-2, -1, 0, 1, 2, 3),
    max_cost: int = 7,
    beam_per_cost: int = 2_000,
) -> SearchResult:
    """Bottom-up typed synthesis with behavioral-equivalence pruning."""
    if not examples:
        raise ValueError("examples are required")
    if max_cost < 1 or beam_per_cost < 1:
        raise ValueError("positive search budgets are required")

    inputs = tuple(x for x, _ in examples)
    target = tuple(_compact(_fraction(y)) for _, y in examples)
    by_cost: dict[int, list[Expr]] = {1: [Input()] + [NumberConst(Fraction(c)) for c in constants]}
    behavior_best: dict[tuple[Hashable, ...], Expr] = {}
    explored = 0

    def register(expr: Expr) -> Expr | None:
        nonlocal explored
        try:
            signature = tuple(expr.evaluate(x) for x in inputs)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
        explored += 1
        previous = behavior_best.get(signature)
        if previous is None or expr.cost < previous.cost or (expr.cost == previous.cost and expr.render() < previous.render()):
            behavior_best[signature] = expr
        if signature == target:
            return behavior_best[signature]
        return None

    for expr in by_cost[1]:
        found = register(expr)
        if found is not None:
            return SearchResult(found, explored, 1)

    for cost in range(2, max_cost + 1):
        generated: dict[str, Expr] = {}
        for left_cost in range(1, cost):
            right_cost = cost - left_cost - 1
            if right_cost < 1:
                continue
            for left in by_cost.get(left_cost, ()): 
                for right in by_cost.get(right_cost, ()): 
                    pair = sorted((left, right), key=lambda e: e.render())
                    for expr in (Add(pair[0], pair[1]), Multiply(pair[0], pair[1])):
                        generated.setdefault(expr.render(), expr)

        candidates = [generated[key] for key in sorted(generated)[:beam_per_cost]]
        kept: list[Expr] = []
        local_signatures: set[tuple[Hashable, ...]] = set()
        for expr in candidates:
            try:
                signature = tuple(expr.evaluate(x) for x in inputs)
            except (TypeError, ValueError, ZeroDivisionError):
                continue
            if signature in local_signatures:
                continue
            local_signatures.add(signature)
            found = register(expr)
            best = behavior_best.get(signature)
            if best is expr:
                kept.append(expr)
            if found is not None:
                return SearchResult(found, explored, cost)
        by_cost[cost] = kept

    return SearchResult(None, explored, max_cost)


def _number(value: Any) -> Hashable:
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise TypeError("numeric expression requires numeric input")
    return _compact(Fraction(value))


def _fraction(value: Any) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise TypeError("numeric value required")
    return Fraction(value)


def _compact(value: Fraction) -> Hashable:
    return value.numerator if value.denominator == 1 else value
