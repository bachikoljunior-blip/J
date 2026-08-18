from __future__ import annotations

from dataclasses import dataclass
from math import exp, log
from random import Random
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class Observation:
    family: str
    cluster: str
    normalized_utility: float

    def __post_init__(self) -> None:
        if not self.family or not self.cluster:
            raise ValueError("family and cluster are required")
        if self.normalized_utility < 0:
            raise ValueError("normalized_utility must be non-negative")


@dataclass(frozen=True)
class RunDisposition:
    score_as_failure: bool
    eligible_for_rerun: bool
    reason: str


def disposition_for_run(*, infrastructure_failure: bool, candidate_caused: bool) -> RunDisposition:
    """Apply the preregistered failure-handling rule.

    Only evaluator infrastructure failures that are demonstrably outside the
    candidate boundary may be rerun. Candidate-caused failures are scored.
    """
    if infrastructure_failure and not candidate_caused:
        return RunDisposition(False, True, "verified evaluator infrastructure failure")
    if candidate_caused:
        return RunDisposition(True, False, "candidate-caused failure")
    return RunDisposition(False, False, "normal scoreable run")


def hierarchical_family_lcbs(
    observations: Sequence[Observation],
    *,
    repetitions: int = 10_000,
    alpha: float = 0.05,
    seed: int = 0,
) -> dict[str, float]:
    """One-sided lower confidence bounds using cluster-aware bootstrap."""
    if repetitions < 100:
        raise ValueError("repetitions must be at least 100")
    grouped = _group(observations)
    rng = Random(seed)
    draws: dict[str, list[float]] = {family: [] for family in grouped}

    for _ in range(repetitions):
        for family, clusters in grouped.items():
            cluster_names = tuple(clusters)
            sampled_values: list[float] = []
            for _ in cluster_names:
                chosen = rng.choice(cluster_names)
                values = clusters[chosen]
                for _ in values:
                    sampled_values.append(rng.choice(values))
            draws[family].append(sum(sampled_values) / len(sampled_values))

    return {family: _lower_quantile(values, alpha) for family, values in draws.items()}


def geometric_mean_lcb(
    observations: Sequence[Observation],
    *,
    repetitions: int = 10_000,
    alpha: float = 0.05,
    seed: int = 0,
) -> float:
    """LCB for equally weighted geometric mean across task families."""
    if repetitions < 100:
        raise ValueError("repetitions must be at least 100")
    grouped = _group(observations)
    if len(grouped) < 2:
        raise ValueError("at least two families are required")
    rng = Random(seed)
    draw_values: list[float] = []

    for _ in range(repetitions):
        family_means: list[float] = []
        for clusters in grouped.values():
            cluster_names = tuple(clusters)
            sampled_values: list[float] = []
            for _ in cluster_names:
                chosen = rng.choice(cluster_names)
                values = clusters[chosen]
                for _ in values:
                    sampled_values.append(rng.choice(values))
            family_means.append(sum(sampled_values) / len(sampled_values))
        draw_values.append(_geometric_mean(family_means))

    return _lower_quantile(draw_values, alpha)


def validate_template_concentration(
    counts_by_family_and_template: Mapping[str, Mapping[str, int]],
    *,
    max_share: float = 0.10,
    min_templates: int = 20,
    min_tasks: int = 100,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    for family, counts in counts_by_family_and_template.items():
        total = sum(counts.values())
        if total < min_tasks:
            reasons.append(f"{family}: fewer than {min_tasks} tasks")
        if len(counts) < min_templates:
            reasons.append(f"{family}: fewer than {min_templates} templates")
        if total > 0:
            offenders = [name for name, count in counts.items() if count / total > max_share]
            if offenders:
                reasons.append(f"{family}: template share exceeds {max_share:.0%}: {','.join(sorted(offenders))}")
    return (not reasons, tuple(reasons))


def _group(observations: Sequence[Observation]) -> dict[str, dict[str, list[float]]]:
    if not observations:
        raise ValueError("observations are required")
    grouped: dict[str, dict[str, list[float]]] = {}
    for obs in observations:
        grouped.setdefault(obs.family, {}).setdefault(obs.cluster, []).append(obs.normalized_utility)
    return grouped


def _lower_quantile(values: Sequence[float], alpha: float) -> float:
    if not 0 < alpha < 0.5:
        raise ValueError("alpha must be between 0 and 0.5")
    ordered = sorted(values)
    index = max(0, int(alpha * len(ordered)) - 1)
    return ordered[index]


def _geometric_mean(values: Iterable[float]) -> float:
    values = tuple(values)
    if not values or any(v <= 0 for v in values):
        return 0.0
    return exp(sum(log(v) for v in values) / len(values))
