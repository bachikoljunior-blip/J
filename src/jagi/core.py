from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


@dataclass(frozen=True)
class Observation:
    modality: str
    content: Any
    source: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Goal:
    goal_id: str
    description: str
    success_criteria: tuple[str, ...]
    constraints: tuple[str, ...] = ()
    priority: float = 1.0

    def __post_init__(self) -> None:
        if not self.goal_id or not self.description or not self.success_criteria:
            raise ValueError("goal_id, description, and success_criteria are required")
        if self.priority <= 0:
            raise ValueError("priority must be positive")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: Mapping[str, Any]
    permission_scope: tuple[str, ...]


@dataclass(frozen=True)
class Action:
    action_id: str
    kind: str
    target: str
    arguments: Mapping[str, Any]
    intent: str
    expected_observation: str | None = None


@dataclass(frozen=True)
class Feedback:
    source: str
    signals: Mapping[str, float]
    verified: bool
    terminal: bool = False
    note: str | None = None


@dataclass(frozen=True)
class CognitiveState:
    episode_id: str
    step: int
    active_goal_ids: tuple[str, ...]
    working_items: tuple[str, ...] = ()
    learned_skill_ids: tuple[str, ...] = ()
    uncertainty: float = 1.0

    def __post_init__(self) -> None:
        if self.step < 0:
            raise ValueError("step must be non-negative")
        if not 0.0 <= self.uncertainty <= 1.0:
            raise ValueError("uncertainty must be in [0,1]")


@dataclass(frozen=True)
class Transition:
    previous: CognitiveState
    observations: tuple[Observation, ...]
    action: Action
    feedback: Feedback | None
    current: CognitiveState

    def __post_init__(self) -> None:
        if self.current.episode_id != self.previous.episode_id:
            raise ValueError("episode_id cannot change within a transition")
        if self.current.step != self.previous.step + 1:
            raise ValueError("each transition must advance exactly one step")


@runtime_checkable
class CognitiveCore(Protocol):
    """Boundary for the AGI candidate's cognitive implementation.

    Implementations may contain learned models, planners, memory, and online
    learning. They must not depend on the recursive project-management solver.
    """

    def initialize(self, episode_id: str, goals: Sequence[Goal], tools: Sequence[ToolSpec]) -> CognitiveState:
        ...

    def act(self, state: CognitiveState, observations: Sequence[Observation], goals: Sequence[Goal], tools: Sequence[ToolSpec]) -> Action:
        ...

    def learn(self, state: CognitiveState, transition: Transition) -> CognitiveState:
        ...

    def snapshot(self) -> bytes:
        """Return sufficient candidate-owned state to resume the cognitive process."""
        ...
