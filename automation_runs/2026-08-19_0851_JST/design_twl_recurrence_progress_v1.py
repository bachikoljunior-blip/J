from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import log2

from colored_subset_exact_twl_design_v1 import (
    ExactTWLDesignOutcome,
    classify_stable_twl_design,
    stable_colored_subset_twl,
)
from master_canonical_reduction import CanonicalReductionResult, reduce_canonical_pair_structure
from quasipoly_recurrence_accounting_v1 import RecurrenceAccountingNode


@dataclass(frozen=True)
class DesignTWLRecurrenceProgress:
    status: str
    vertex_count: int
    arity: int
    individualized: tuple[int, ...]
    design_status: str
    child_aux_sizes: tuple[int, ...]
    max_child_aux_size: int | None
    aux_shrink_fraction: float
    aux_shrink_certified: bool
    split_or_johnson_result: CanonicalReductionResult | None
    accounting_children: tuple[RecurrenceAccountingNode, ...]
    local_log2_cost_bound: float
    canonical: bool
    cost_certified: bool
    reason: str


def _canonical_symmetric_pair_weights(vertices, pair_colors):
    vertices = tuple(vertices)
    index = {x: i for i, x in enumerate(vertices)}
    tokens = []
    for a, b in combinations(vertices, 2):
        tokens.append((tuple(sorted((pair_colors[a][b], pair_colors[b][a]))), index[a], index[b]))
    palette = sorted({token for token, _a, _b in tokens}, key=repr)
    labels = {token: i for i, token in enumerate(palette)}
    return tuple(((a, b), labels[token]) for token, a, b in tokens)


def _unresolved_measure_child(root_n: int, size: int, reason: str):
    """Record a proved child measure without pretending the child SI is terminal."""
    return RecurrenceAccountingNode(
        n=root_n,
        m=max(1, int(size)),
        operation_kind="unresolved_design_measure_child",
        canonical=True,
        cost_certified=False,
        local_log2_cost_bound=0.0,
        children=(),
        terminal_certified=False,
        reason=reason,
    )


def certify_design_twl_recurrence_progress(
    vertex_count: int,
    arity: int,
    colors,
    individualized,
    *,
    root_n: int,
    alpha: float = 0.9,
    max_tuple_states: int = 250000,
    max_rounds: int | None = None,
    max_work_units: int = 100000000,
    max_johnson_nodes: int = 500000,
) -> DesignTWLRecurrenceProgress:
    """Translate one exact k-WL Design outcome into recurrence progress evidence.

    Alpha-coloring and imprimitive Split-or-UPCC outcomes directly expose an
    auxiliary-domain partition whose cells are at most ``alpha*v``. These are
    mechanical ``aux_shrink`` measures for the global recurrence contract.

    A UPCC is not itself called progress. Its exact directed 2-skeleton is first
    symmetrized canonically and handed to the existing coherent/Johnson reducer.
    Only a verified point split or exact Johnson-ground reduction is promoted to
    auxiliary shrink. A stable non-Johnson coherent relation remains a typed
    ``requires_full_split_or_johnson`` child. This prevents theorem incompleteness
    from being hidden behind an optimistic recurrence flag.

    The returned accounting child nodes are deliberately *uncertified* measure
    placeholders. Global recurrence validation must replace each one with the
    actual exact downstream SI proof; otherwise the existing validator rejects it.
    """
    v = int(vertex_count)
    k = int(arity)
    if root_n < v or root_n < 1:
        raise ValueError("root_n must dominate the Design ground size")
    if not 0.5 <= alpha < 1.0:
        raise ValueError("alpha must lie in [1/2,1)")

    stable = stable_colored_subset_twl(
        v,
        k,
        tuple(colors),
        individualized=tuple(individualized),
        max_tuple_states=max_tuple_states,
        max_rounds=max_rounds,
        max_work_units=max_work_units,
    )
    outcome: ExactTWLDesignOutcome = classify_stable_twl_design(stable, alpha=alpha)
    if not outcome.exact:
        return DesignTWLRecurrenceProgress(
            outcome.status, v, k, tuple(individualized), outcome.status,
            (), None, alpha, False, None, (), 0.0, True, False, outcome.reason,
        )

    local_bound = log2(max(2, stable.work_units)) + 8.0 * log2(max(2, v)) + 24.0
    if outcome.status in {
        "certified_twl_alpha_coloring",
        "certified_twl_imprimitive_alpha_partition",
    }:
        sizes = tuple(sorted(len(cell) for cell in outcome.output_partition))
        largest = max(sizes, default=0)
        shrink = bool(sizes) and largest <= alpha * v + 1e-12 and largest < v
        if not shrink:
            raise AssertionError("certified Design split failed its recorded alpha bound")
        children = tuple(
            _unresolved_measure_child(
                root_n,
                size,
                "Design Split-or-UPCC proved this auxiliary measure; exact downstream SI/accounting is still required",
            )
            for size in sizes
        )
        return DesignTWLRecurrenceProgress(
            "certified_design_auxiliary_split_progress",
            v,
            k,
            tuple(individualized),
            outcome.status,
            sizes,
            largest,
            alpha,
            True,
            None,
            children,
            local_bound,
            True,
            True,
            "exact k-WL Split-or-UPCC output is an alpha-bounded canonical partition, certifying auxiliary-domain shrink on every structural child without claiming those children solved",
        )

    if outcome.status == "certified_twl_upcc":
        vertices = outcome.dominant_cell
        pair_weights = _canonical_symmetric_pair_weights(vertices, stable.pair_colors)
        reduction = reduce_canonical_pair_structure(
            len(vertices),
            pair_weights,
            max_class_fraction=alpha,
            max_johnson_nodes=max_johnson_nodes,
        )
        if reduction.progress_verified and reduction.reduced_domain_size is not None:
            reduced = int(reduction.reduced_domain_size)
            shrink = reduced <= alpha * len(vertices) + 1e-12 and reduced < len(vertices)
            if shrink:
                child = _unresolved_measure_child(
                    root_n,
                    reduced,
                    "coherent/Johnson reduction proved this smaller auxiliary measure; exact downstream SI/accounting is still required",
                )
                return DesignTWLRecurrenceProgress(
                    "certified_design_upcc_split_or_johnson_progress",
                    v,
                    k,
                    tuple(individualized),
                    outcome.status,
                    (reduced,),
                    reduced,
                    alpha,
                    True,
                    reduction,
                    (child,),
                    local_bound + 16.0 * log2(max(2, len(vertices))) + 32.0,
                    True,
                    True,
                    "the exact UPCC 2-skeleton is reduced by existing coherent/Johnson machinery to a strictly alpha-smaller auxiliary domain; the reduced child itself remains unsolved here",
                )
        return DesignTWLRecurrenceProgress(
            "requires_full_split_or_johnson",
            v,
            k,
            tuple(individualized),
            outcome.status,
            (),
            None,
            alpha,
            False,
            reduction,
            (),
            local_bound,
            True,
            True,
            "UPCC is mechanically certified, but the current coherent/Johnson reducer does not prove an alpha-smaller split or Johnson ground; full Split-or-Johnson remains the active child",
        )

    return DesignTWLRecurrenceProgress(
        "no_design_recurrence_progress",
        v,
        k,
        tuple(individualized),
        outcome.status,
        (),
        None,
        alpha,
        False,
        None,
        (),
        local_bound,
        True,
        True,
        "the exact stable k-WL outcome is not a Split-or-UPCC success that can currently be charged as recurrence progress",
    )
