from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Hashable, Sequence

from .compositional_search import Expr


@dataclass(frozen=True)
class LearnedPrimitive:
    primitive_id: str
    body: Expr
    evidence_sha256: str
    cost: int = 1
    type_name: str = "number"

    def evaluate(self, x: Any) -> Hashable:
        return self.body.evaluate(x)

    def render(self) -> str:
        return f"<{self.primitive_id}>"


@dataclass
class PrimitiveLibrary:
    """Promote verified solved subprograms into reusable one-step productions."""

    primitives: dict[str, LearnedPrimitive] = field(default_factory=dict)

    def promote(self, primitive_id: str, body: Expr, verified_examples: Sequence[tuple[Any, Any]]) -> LearnedPrimitive:
        if not primitive_id or primitive_id in self.primitives:
            raise ValueError("primitive_id must be new and non-empty")
        if not verified_examples:
            raise ValueError("verified_examples are required")
        for x, expected in verified_examples:
            if body.evaluate(x) != expected:
                raise ValueError("body does not satisfy verified evidence")
        digest = hashlib.sha256(repr(tuple(verified_examples)).encode("utf-8")).hexdigest()
        primitive = LearnedPrimitive(primitive_id, body, digest)
        self.primitives[primitive_id] = primitive
        return primitive

    def seeds(self) -> tuple[LearnedPrimitive, ...]:
        return tuple(self.primitives[key] for key in sorted(self.primitives))
