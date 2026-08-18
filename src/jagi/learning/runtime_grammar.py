from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Hashable, Sequence


@dataclass(frozen=True)
class RuntimeOperator:
    name: str
    input_types: tuple[str, ...]
    output_type: str
    function: Callable[..., Hashable]
    cost: int = 1

    def __post_init__(self) -> None:
        if not self.name or not self.input_types or not self.output_type or self.cost < 1:
            raise ValueError("runtime operator requires name, types, and positive cost")


@dataclass(frozen=True)
class RuntimeExpr:
    type_name: str
    kind: str
    payload: Any
    children: tuple["RuntimeExpr", ...] = ()
    cost: int = 1

    def evaluate(self, x: Any, operators: dict[str, RuntimeOperator]) -> Hashable:
        if self.kind == "input":
            return x
        if self.kind == "const":
            return self.payload
        if self.kind == "op":
            operator = operators[self.payload]
            values = [child.evaluate(x, operators) for child in self.children]
            return operator.function(*values)
        raise ValueError(self.kind)

    def render(self) -> str:
        if self.kind == "input":
            return "x"
        if self.kind == "const":
            return repr(self.payload)
        return f"{self.payload}({','.join(child.render() for child in self.children)})"


@dataclass(frozen=True)
class RuntimeSearchResult:
    expression: RuntimeExpr | None
    explored_behaviors: int


def synthesize_runtime_grammar(
    examples: Sequence[tuple[Any, Hashable]],
    *,
    input_type: str,
    output_type: str,
    operators: Sequence[RuntimeOperator],
    constants: Sequence[tuple[str, Hashable]] = (),
    max_cost: int = 7,
    beam_per_cost: int = 2_000,
) -> RuntimeSearchResult:
    """Typed bottom-up synthesis over operators supplied at runtime."""
    if not examples:
        raise ValueError("examples required")
    operator_map = {op.name: op for op in operators}
    if len(operator_map) != len(operators):
        raise ValueError("runtime operator names must be unique")

    by_cost_type: dict[tuple[int, str], list[RuntimeExpr]] = {}
    by_cost_type[(1, input_type)] = [RuntimeExpr(input_type, "input", None)]
    for type_name, value in constants:
        by_cost_type.setdefault((1, type_name), []).append(RuntimeExpr(type_name, "const", value))

    target = tuple(out for _, out in examples)
    inputs = tuple(inp for inp, _ in examples)
    behavior_best: dict[tuple[str, tuple[Hashable, ...]], RuntimeExpr] = {}
    explored = 0

    def signature(expr: RuntimeExpr):
        nonlocal explored
        values = tuple(expr.evaluate(x, operator_map) for x in inputs)
        explored += 1
        return (expr.type_name, values)

    def register(expr: RuntimeExpr):
        try:
            sig = signature(expr)
        except Exception:
            return None
        current = behavior_best.get(sig)
        if current is None or expr.cost < current.cost or (expr.cost == current.cost and expr.render() < current.render()):
            behavior_best[sig] = expr
        if expr.type_name == output_type and sig[1] == target:
            return behavior_best[sig]
        return None

    for (cost, _), expressions in list(by_cost_type.items()):
        if cost == 1:
            for expr in expressions:
                found = register(expr)
                if found:
                    return RuntimeSearchResult(found, explored)

    for total_cost in range(2, max_cost + 1):
        generated: dict[tuple[str, str], RuntimeExpr] = {}
        for op in operators:
            child_budget = total_cost - op.cost
            if child_budget < len(op.input_types):
                continue
            for child_costs in _compositions(child_budget, len(op.input_types)):
                pools = [by_cost_type.get((cost, type_name), ()) for cost, type_name in zip(child_costs, op.input_types)]
                if any(not pool for pool in pools):
                    continue
                for children in _product(pools):
                    expr = RuntimeExpr(op.output_type, "op", op.name, tuple(children), total_cost)
                    generated.setdefault((op.output_type, expr.render()), expr)

        candidates = [generated[key] for key in sorted(generated, key=lambda k: (k[0], k[1]))[:beam_per_cost]]
        kept_by_type: dict[str, list[RuntimeExpr]] = {}
        local: set[tuple[str, tuple[Hashable, ...]]] = set()
        for expr in candidates:
            try:
                sig = signature(expr)
            except Exception:
                continue
            if sig in local:
                continue
            local.add(sig)
            current = behavior_best.get(sig)
            if current is None or expr.cost < current.cost or (expr.cost == current.cost and expr.render() < current.render()):
                behavior_best[sig] = expr
                kept_by_type.setdefault(expr.type_name, []).append(expr)
            if expr.type_name == output_type and sig[1] == target:
                return RuntimeSearchResult(behavior_best[sig], explored)
        for type_name, exprs in kept_by_type.items():
            by_cost_type[(total_cost, type_name)] = exprs

    return RuntimeSearchResult(None, explored)


def _compositions(total: int, parts: int):
    if parts == 1:
        if total >= 1:
            yield (total,)
        return
    for first in range(1, total - parts + 2):
        for rest in _compositions(total - first, parts - 1):
            yield (first,) + rest


def _product(pools):
    if not pools:
        yield ()
        return
    for head in pools[0]:
        for tail in _product(pools[1:]):
            yield (head,) + tail
