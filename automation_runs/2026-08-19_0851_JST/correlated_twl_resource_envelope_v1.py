from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil, log2


@dataclass(frozen=True)
class PairedCorrelatedTWLResourceEnvelope:
    status: str
    original_root_degree: int
    vertex_count: int
    arity: int
    theorem_arity_cap: int
    tuple_states_per_run: int
    individualization_runs_per_side_upper_bound: int
    stabilization_rounds_per_run_upper_bound: int
    initial_work_per_run_upper_bound: int
    replacement_work_per_round_upper_bound: int
    work_per_run_upper_bound: int
    work_per_side_upper_bound: int
    paired_work_upper_bound: int
    max_paired_work: int
    root_lift_certified: bool
    admitted: bool
    executed_source_runs: int
    executed_target_runs: int
    executed_source_work: int
    executed_target_work: int
    charged_paired_work: int
    complete: bool
    reason: str


def _ordered_partial_tuple_count(n: int, k: int) -> int:
    total = 0
    falling = 1
    for ell in range(k):
        if ell:
            falling *= n - (ell - 1)
        total += falling
    return total


def paired_correlated_twl_resource_envelope(
    original_root_degree: int,
    vertex_count: int,
    arity: int,
    max_paired_work: int,
) -> PairedCorrelatedTWLResourceEnvelope:
    """Reserve every possible source/target correlated-k-WL primitive.

    The existing executor can stop at the first successful individualization
    level, but the proof boundary cannot assume that early stop.  It therefore
    reserves all ordered individualizations of lengths ``0..k-1``, all ``n^k``
    tuple states, one initialization pass, and at most ``n^k`` refinement
    rounds.  A round scans every common replacement ``y`` in every coordinate.

    Runtime ``max_states``, ``max_tuple_states``, ``max_rounds`` and per-side
    work caps remain engineering fail-closed limits.  They are deliberately not
    inputs to this theorem-side upper bound.
    """
    root, n, k, cap = map(int, (
        original_root_degree, vertex_count, arity, max_paired_work,
    ))
    if root <= 0 or n <= 0 or k <= 0 or k > n or cap <= 0:
        raise ValueError("invalid paired correlated-tWL resource parameters")

    arity_cap = max(1, ceil(log2(max(2, root))))
    tuple_states = n ** k
    runs = _ordered_partial_tuple_count(n, k)
    rounds = tuple_states
    initial = tuple_states
    replacement = tuple_states * n * k
    per_run = initial + rounds * replacement
    per_side = runs * per_run
    paired = 2 * per_side
    root_lift = n <= root and k <= arity_cap
    admitted = root_lift and paired <= cap
    if not root_lift:
        status = "correlated_twl_original_root_lift_unavailable"
        reason = (
            "the auxiliary tuple ground or arity exceeds the original-root "
            "quasipolynomial lift gate"
        )
    elif paired > cap:
        status = "correlated_twl_paired_work_cap_exceeded"
        reason = (
            "the complete source/target correlated-tWL upper bound exceeds "
            "the finite original-root budget before the first t-WL run"
        )
    else:
        status = "certified_paired_correlated_twl_work_bound"
        reason = (
            "all source/target tuple initialization, correlated replacement, "
            "stabilization-round, and individualization multiplicities fit the "
            "finite original-root budget"
        )
    return PairedCorrelatedTWLResourceEnvelope(
        status, root, n, k, arity_cap, tuple_states, runs, rounds, initial,
        replacement, per_run, per_side, paired, cap, root_lift, admitted,
        0, 0, 0, 0, 0, False, reason,
    )


def record_paired_correlated_twl_execution(
    envelope: PairedCorrelatedTWLResourceEnvelope,
    *,
    executed_source_runs: int,
    executed_target_runs: int,
    executed_source_work: int,
    executed_target_work: int,
    complete: bool,
) -> PairedCorrelatedTWLResourceEnvelope:
    if not envelope.admitted:
        raise ValueError("cannot record execution for a rejected t-WL envelope")
    sr, tr, sw, tw = map(int, (
        executed_source_runs, executed_target_runs,
        executed_source_work, executed_target_work,
    ))
    if min(sr, tr, sw, tw) < 0:
        raise ValueError("executed t-WL counts must be nonnegative")
    if sr > envelope.individualization_runs_per_side_upper_bound:
        raise ValueError("source t-WL run count exceeds the proven bound")
    if tr > envelope.individualization_runs_per_side_upper_bound:
        raise ValueError("target t-WL run count exceeds the proven bound")
    if sw > envelope.work_per_side_upper_bound:
        raise ValueError("source t-WL work exceeds the proven bound")
    if tw > envelope.work_per_side_upper_bound:
        raise ValueError("target t-WL work exceeds the proven bound")
    charged = sw + tw
    if charged > envelope.paired_work_upper_bound:
        raise ValueError("paired t-WL work exceeds the proven bound")
    return replace(
        envelope,
        executed_source_runs=sr,
        executed_target_runs=tr,
        executed_source_work=sw,
        executed_target_work=tw,
        charged_paired_work=charged,
        complete=bool(complete),
    )


__all__ = [
    "PairedCorrelatedTWLResourceEnvelope",
    "paired_correlated_twl_resource_envelope",
    "record_paired_correlated_twl_execution",
]
