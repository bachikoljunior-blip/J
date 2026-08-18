from __future__ import annotations

from dataclasses import dataclass
from math import log2
from typing import Any, Hashable, Protocol, Sequence


class ExecutableHypothesis(Protocol):
    hypothesis_id: str

    def predict(self, example_input: Any) -> Hashable:
        ...


@dataclass(frozen=True)
class Demonstration:
    example_input: Any
    expected_output: Hashable


@dataclass(frozen=True)
class PredictionSet:
    alternatives: tuple[tuple[Hashable, float], ...]

    @property
    def resolved(self) -> bool:
        return len(self.alternatives) == 1

    @property
    def top(self) -> Hashable | None:
        return self.alternatives[0][0] if self.alternatives else None


@dataclass
class VersionSpaceLearner:
    """Exact online elimination over an executable symbolic hypothesis set.

    This mechanism does not itself invent hypotheses; candidate generation is a
    separate child problem.
    """

    hypotheses: list[ExecutableHypothesis]
    observations_seen: int = 0
    contradictions: int = 0

    def __post_init__(self) -> None:
        ids = [h.hypothesis_id for h in self.hypotheses]
        if not ids or any(not i for i in ids):
            raise ValueError("at least one named hypothesis is required")
        if len(set(ids)) != len(ids):
            raise ValueError("hypothesis ids must be unique")

    def observe(self, demo: Demonstration) -> int:
        self.observations_seen += 1
        consistent: list[ExecutableHypothesis] = []
        for hypothesis in self.hypotheses:
            try:
                predicted = hypothesis.predict(demo.example_input)
            except Exception:
                continue
            if predicted == demo.expected_output:
                consistent.append(hypothesis)
        if not consistent:
            self.contradictions += 1
            return 0
        self.hypotheses = consistent
        return len(consistent)

    def predict(self, example_input: Any) -> PredictionSet:
        if not self.hypotheses:
            return PredictionSet(())
        counts: dict[Hashable, int] = {}
        total = 0
        for hypothesis in self.hypotheses:
            try:
                value = hypothesis.predict(example_input)
            except Exception:
                continue
            counts[value] = counts.get(value, 0) + 1
            total += 1
        if total == 0:
            return PredictionSet(())
        alternatives = tuple(sorted(((v, c / total) for v, c in counts.items()), key=lambda x: (-x[1], repr(x[0]))))
        return PredictionSet(alternatives)

    def disagreement_entropy(self, example_input: Any) -> float:
        prediction = self.predict(example_input)
        return -sum(p * log2(p) for _, p in prediction.alternatives if p > 0)

    def choose_disambiguating_query(self, candidate_inputs: Sequence[Any]) -> Any | None:
        if not candidate_inputs or len(self.hypotheses) <= 1:
            return None
        scored = [(self.disagreement_entropy(value), index, value) for index, value in enumerate(candidate_inputs)]
        best_entropy, _, best = max(scored, key=lambda item: (item[0], -item[1]))
        return best if best_entropy > 0 else None
