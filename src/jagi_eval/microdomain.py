from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Hashable, Mapping, Sequence


@dataclass(frozen=True)
class OperatorView:
    name: str
    input_types: tuple[str, ...]
    output_type: str
    callable: Callable[..., Hashable]


@dataclass(frozen=True)
class CandidateTaskView:
    task_id: str
    input_type: str
    output_type: str
    demonstrations: tuple[tuple[Any, Hashable], ...]
    operators: tuple[OperatorView, ...]
    constants: tuple[tuple[str, Hashable], ...] = ()
    max_program_cost: int = 7


@dataclass(frozen=True)
class HiddenCase:
    input_value: Any
    expected_output: Hashable


@dataclass(frozen=True)
class SealedMicroDomain:
    view: CandidateTaskView
    hidden_cases: tuple[HiddenCase, ...]

    def __post_init__(self) -> None:
        if not self.hidden_cases:
            raise ValueError("sealed micro-domain requires hidden cases")


@dataclass(frozen=True)
class MicroDomainScore:
    task_id: str
    correct: int
    total: int
    solved: bool
    error: str | None = None


Solver = Callable[[CandidateTaskView], Callable[[Any], Hashable] | None]


def score_microdomain(task: SealedMicroDomain, solver: Solver) -> MicroDomainScore:
    """Run a candidate solver without passing hidden inputs or answers to it."""
    try:
        predictor = solver(task.view)
    except Exception as exc:
        return MicroDomainScore(task.view.task_id, 0, len(task.hidden_cases), False, f"solver_error:{type(exc).__name__}")
    if predictor is None:
        return MicroDomainScore(task.view.task_id, 0, len(task.hidden_cases), False, "unresolved")

    correct = 0
    for case in task.hidden_cases:
        try:
            if predictor(case.input_value) == case.expected_output:
                correct += 1
        except Exception:
            pass
    return MicroDomainScore(task.view.task_id, correct, len(task.hidden_cases), correct == len(task.hidden_cases))


def aggregate_scores(scores: Sequence[MicroDomainScore]) -> Mapping[str, float | int]:
    if not scores:
        raise ValueError("scores required")
    tasks = len(scores)
    solved = sum(score.solved for score in scores)
    cases = sum(score.total for score in scores)
    correct = sum(score.correct for score in scores)
    return {
        "tasks": tasks,
        "tasks_solved": solved,
        "task_success_rate": solved / tasks,
        "hidden_cases": cases,
        "hidden_case_accuracy": correct / cases if cases else 0.0,
    }
