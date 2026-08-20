from __future__ import annotations

from dataclasses import dataclass
from math import log2
from typing import Hashable, Iterable

from bipartite_split_or_johnson_gate_v1 import certify_bipartite_split_or_johnson_gate
from quasipoly_structural_recurrence_accounting_v2 import (
    PHASE_UPCC,
    StructuralAccountingChild,
    StructuralRecurrenceAccountingNode,
)


@dataclass(frozen=True)
class BipartiteTwinSplitProgress:
    status: str
    left_size: int
    right_size: int
    alpha: float
    accounting_shrink_fraction: float
    theorem_input_gate: bool
    twin_cells: tuple[tuple[int, ...], ...]
    twin_cell_sizes: tuple[int, ...]
    largest_twin_cell: int
    canonical_partition: bool
    exact_partition: bool
    accounting_shrink_gate: bool
    progress_certified: bool
    local_log2_cost_bound: float
    reason: str


def certify_bipartite_twin_split_progress(
    left_size: int,
    right_size: int,
    edges: Iterable[tuple[int, int]],
    *,
    alpha: float = 0.75,
    accounting_shrink_fraction: float = 0.9,
    left_colors: Iterable[Hashable] | None = None,
    right_colors: Iterable[Hashable] | None = None,
    normalize_by_complement: bool = True,
) -> BipartiteTwinSplitProgress:
    """Turn the exact rev199 twin-defect gate into a certified shrink subcase.

    For a colored bipartite graph, equality of left color and exact right
    neighborhood is an isomorphism-invariant equivalence relation. Therefore the
    left twin classes form an equivariant partition. When rev199's theorem input
    gate fires, its symmetry-defect certificate already bounds the largest twin
    class by ``alpha * |V1|``. If that bound is also within the recurrence
    checker's configured shrink fraction, each twin cell is a mechanically
    certified constant-factor auxiliary child.

    This closes only the stronger "visible twin split" subcase. It does not claim
    the corrected general Split-or-Johnson theorem conclusion: instances whose
    theorem progress depends on a deeper bipartite recursion or a Johnson output
    remain unresolved and must fail closed here.
    """
    if not 0.0 < accounting_shrink_fraction < 1.0:
        raise ValueError("accounting_shrink_fraction must lie in (0,1)")

    gate = certify_bipartite_split_or_johnson_gate(
        left_size,
        right_size,
        edges,
        alpha=alpha,
        left_colors=left_colors,
        right_colors=right_colors,
        normalize_by_complement=normalize_by_complement,
    )
    cells = tuple(gate.left_twin_classes)
    sizes = tuple(sorted(len(cell) for cell in cells))
    largest = max(sizes, default=0)

    # Conservative polynomial local-work charge. The exact gate scans explicit
    # vertices/edges and neighborhood data; charging the cube of the represented
    # instance size dominates those operations without treating Python timing as
    # mathematical evidence.
    represented = max(2, gate.left_size + gate.right_size + gate.edge_count + 1)
    local_log2_cost_bound = 3.0 * log2(represented)

    canonical = True
    exact = bool(gate.exact)
    shrink_gate = (
        bool(gate.theorem_input_gate)
        and len(cells) >= 2
        and largest <= accounting_shrink_fraction * gate.left_size + 1e-12
    )
    progress = canonical and exact and shrink_gate

    if not gate.theorem_input_gate:
        status = "bipartite_twin_split_theorem_gate_not_met"
        reason = (
            "rev199 theorem input gate is not certified; no recurrence progress "
            "is claimed"
        )
    elif len(cells) < 2:
        status = "bipartite_twin_split_degenerate_partition"
        reason = "the exact twin relation did not produce a nontrivial partition"
    elif not shrink_gate:
        status = "bipartite_twin_split_not_accounting_compatible"
        reason = (
            "the theorem gate fires, but the largest exact twin cell is not within "
            "the configured recurrence shrink fraction"
        )
    else:
        status = "certified_bipartite_twin_aux_shrink"
        reason = (
            "left color+neighborhood twin classes are an exact equivariant partition; "
            "every child is within the configured constant-factor auxiliary shrink. "
            "This is a strict subcase of the corrected Split-or-Johnson recursion, "
            "not a proof of the general theorem conclusion"
        )

    return BipartiteTwinSplitProgress(
        status=status,
        left_size=gate.left_size,
        right_size=gate.right_size,
        alpha=float(alpha),
        accounting_shrink_fraction=float(accounting_shrink_fraction),
        theorem_input_gate=bool(gate.theorem_input_gate),
        twin_cells=cells,
        twin_cell_sizes=sizes,
        largest_twin_cell=largest,
        canonical_partition=canonical,
        exact_partition=exact,
        accounting_shrink_gate=shrink_gate,
        progress_certified=progress,
        local_log2_cost_bound=local_log2_cost_bound,
        reason=reason,
    )


def make_twin_split_accounting_node(
    certificate: BipartiteTwinSplitProgress,
    children: Iterable[StructuralRecurrenceAccountingNode],
    *,
    ambient_n: int,
    structural_phase: int = PHASE_UPCC,
) -> StructuralRecurrenceAccountingNode:
    """Attach independently supplied recursive children to a certified twin split.

    The helper does not manufacture terminals or downstream theorem evidence. The
    caller must provide one child for each exact twin cell, with the multiset of
    child ``m`` measures equal to the multiset of twin-cell sizes. This preserves
    rev196's requirement that every later recursive edge carry its own evidence.
    """
    if not certificate.progress_certified:
        raise ValueError("certificate does not prove an accounting-compatible split")
    if ambient_n < certificate.left_size:
        raise ValueError("ambient_n must be at least the large-part size")

    child_nodes = tuple(children)
    child_measures = tuple(sorted(int(child.m) for child in child_nodes))
    if child_measures != certificate.twin_cell_sizes:
        raise ValueError("child auxiliary measures must match exact twin-cell sizes")
    if any(child.n > ambient_n for child in child_nodes):
        raise ValueError("child primary measure may not exceed ambient_n")

    return StructuralRecurrenceAccountingNode(
        n=int(ambient_n),
        m=int(certificate.left_size),
        structural_phase=int(structural_phase),
        operation_kind="aux_shrink",
        canonical=certificate.canonical_partition,
        cost_certified=True,
        progress_certified=certificate.progress_certified,
        local_log2_cost_bound=float(certificate.local_log2_cost_bound),
        children=tuple(StructuralAccountingChild(child, multiplicity=1) for child in child_nodes),
        terminal_certified=False,
        reason=certificate.reason,
    )
