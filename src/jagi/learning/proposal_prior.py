from __future__ import annotations

from dataclasses import dataclass, field
from math import log
from typing import Iterable

from .compositional_search import Add, Expr, Input, Multiply, NumberConst


@dataclass
class ProductionPrior:
    """A lightweight learned prior over successful program productions."""

    alpha: float = 1.0
    counts: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.alpha <= 0:
            raise ValueError("alpha must be positive")

    def observe_solution(self, expr: Expr, weight: float = 1.0) -> None:
        if weight <= 0:
            raise ValueError("weight must be positive")
        for token in production_tokens(expr):
            self.counts[token] = self.counts.get(token, 0.0) + weight

    def probability(self, token: str, vocabulary: Iterable[str]) -> float:
        vocab = tuple(dict.fromkeys(vocabulary))
        if token not in vocab:
            vocab = vocab + (token,)
        total = sum(self.counts.get(t, 0.0) for t in vocab) + self.alpha * len(vocab)
        return (self.counts.get(token, 0.0) + self.alpha) / total

    def log_score(self, expr: Expr) -> float:
        tokens = production_tokens(expr)
        vocab = set(self.counts) | set(tokens)
        return sum(log(self.probability(token, vocab)) for token in tokens)

    def rank(self, expressions: Iterable[Expr]) -> tuple[Expr, ...]:
        return tuple(sorted(expressions, key=lambda e: (-self.log_score(e), e.cost, e.render())))


def production_tokens(expr: Expr) -> tuple[str, ...]:
    if isinstance(expr, Input):
        return ("input",)
    if isinstance(expr, NumberConst):
        return ("const", f"const:{expr.value}")
    if isinstance(expr, Add):
        return ("add",) + production_tokens(expr.left) + production_tokens(expr.right)
    if isinstance(expr, Multiply):
        return ("mul",) + production_tokens(expr.left) + production_tokens(expr.right)
    return (type(expr).__name__.lower(),)
