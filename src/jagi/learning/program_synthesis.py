from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Hashable, Mapping, Protocol, Sequence


class Program(Protocol):
    program_id: str

    def execute(self, value: Any) -> Hashable:
        ...

    def predict(self, value: Any) -> Hashable:
        ...


@dataclass(frozen=True)
class Identity:
    program_id: str = "identity"

    def execute(self, value: Any) -> Hashable:
        return _hashable(value)

    predict = execute


@dataclass(frozen=True)
class Constant:
    value: Hashable

    @property
    def program_id(self) -> str:
        return f"const:{self.value!r}"

    def execute(self, value: Any) -> Hashable:
        return self.value

    predict = execute


@dataclass(frozen=True)
class Affine:
    a: Fraction
    b: Fraction

    @property
    def program_id(self) -> str:
        return f"affine:{self.a}:{self.b}"

    def execute(self, value: Any) -> Hashable:
        if not isinstance(value, (int, float, Fraction)) or isinstance(value, bool):
            raise TypeError("affine input must be numeric")
        out = self.a * Fraction(value) + self.b
        return out.numerator if out.denominator == 1 else out

    predict = execute


@dataclass(frozen=True)
class Field:
    key: Hashable

    @property
    def program_id(self) -> str:
        return f"field:{self.key!r}"

    def execute(self, value: Any) -> Hashable:
        if not isinstance(value, Mapping):
            raise TypeError("field input must be a mapping")
        return _hashable(value[self.key])

    predict = execute


@dataclass(frozen=True)
class StringPrefix:
    prefix: str

    @property
    def program_id(self) -> str:
        return f"str-prefix:{self.prefix!r}"

    def execute(self, value: Any) -> Hashable:
        if not isinstance(value, str):
            raise TypeError("string prefix input must be text")
        return self.prefix + value

    predict = execute


@dataclass(frozen=True)
class StringSuffix:
    suffix: str

    @property
    def program_id(self) -> str:
        return f"str-suffix:{self.suffix!r}"

    def execute(self, value: Any) -> Hashable:
        if not isinstance(value, str):
            raise TypeError("string suffix input must be text")
        return value + self.suffix

    predict = execute


@dataclass(frozen=True)
class StringReverse:
    program_id: str = "str-reverse"

    def execute(self, value: Any) -> Hashable:
        if not isinstance(value, str):
            raise TypeError("string reverse input must be text")
        return value[::-1]

    predict = execute


@dataclass(frozen=True)
class SequenceReverse:
    program_id: str = "seq-reverse"

    def execute(self, value: Any) -> Hashable:
        if not isinstance(value, (list, tuple)):
            raise TypeError("sequence reverse input must be list/tuple")
        return tuple(reversed(value))

    predict = execute


def synthesize_programs(examples: Sequence[tuple[Any, Hashable]]) -> tuple[Program, ...]:
    """Generate a compact typed program set consistent with all examples."""
    if not examples:
        raise ValueError("at least one example is required")

    candidates: list[Program] = [Identity()]
    outputs = [_hashable(output) for _, output in examples]
    if all(output == outputs[0] for output in outputs):
        candidates.append(Constant(outputs[0]))

    candidates.extend(_numeric_candidates(examples))
    candidates.extend(_mapping_candidates(examples))
    candidates.extend(_string_candidates(examples))
    candidates.extend([StringReverse(), SequenceReverse()])

    unique: dict[str, Program] = {}
    for candidate in candidates:
        try:
            if all(candidate.execute(inp) == _hashable(out) for inp, out in examples):
                unique[candidate.program_id] = candidate
        except (TypeError, KeyError, ValueError, ZeroDivisionError):
            continue
    return tuple(unique[key] for key in sorted(unique))


def _numeric_candidates(examples: Sequence[tuple[Any, Hashable]]) -> list[Program]:
    if not all(_numeric(inp) and _numeric(out) for inp, out in examples):
        return []
    pairs = [(Fraction(inp), Fraction(out)) for inp, out in examples]
    candidates: list[Program] = []
    if len(pairs) >= 2:
        for i in range(len(pairs)):
            x1, y1 = pairs[i]
            for j in range(i + 1, len(pairs)):
                x2, y2 = pairs[j]
                if x1 == x2:
                    continue
                a = (y2 - y1) / (x2 - x1)
                b = y1 - a * x1
                candidates.append(Affine(a, b))
                return candidates
    x, y = pairs[0]
    candidates.append(Affine(Fraction(1), y - x))
    if x != 0:
        candidates.append(Affine(y / x, Fraction(0)))
    return candidates


def _mapping_candidates(examples: Sequence[tuple[Any, Hashable]]) -> list[Program]:
    if not all(isinstance(inp, Mapping) for inp, _ in examples):
        return []
    common_keys = set(examples[0][0].keys())
    for inp, _ in examples[1:]:
        common_keys &= set(inp.keys())
    return [Field(key) for key in sorted(common_keys, key=repr)]


def _string_candidates(examples: Sequence[tuple[Any, Hashable]]) -> list[Program]:
    if not all(isinstance(inp, str) and isinstance(out, str) for inp, out in examples):
        return []
    first_in, first_out = examples[0]
    candidates: list[Program] = []
    if first_out.endswith(first_in):
        candidates.append(StringPrefix(first_out[: len(first_out) - len(first_in)]))
    if first_out.startswith(first_in):
        candidates.append(StringSuffix(first_out[len(first_in) :]))
    return candidates


def _numeric(value: Any) -> bool:
    return isinstance(value, (int, float, Fraction)) and not isinstance(value, bool)


def _hashable(value: Any) -> Hashable:
    if isinstance(value, list):
        return tuple(_hashable(v) for v in value)
    if isinstance(value, dict):
        return tuple(sorted((k, _hashable(v)) for k, v in value.items()))
    if isinstance(value, Hashable):
        return value
    raise TypeError("program output is not hashable")
