from __future__ import annotations

from dataclasses import dataclass
from math import log2

from ambient_design_tuple_transport_v1 import AmbientDesignTupleCover
from design_twl_recurrence_progress_v1 import (
    DesignTWLRecurrenceProgress,
    certify_design_twl_recurrence_progress,
)
from quasipoly_recurrence_accounting_v1 import AccountingChild, RecurrenceAccountingNode
from relation_twin_design_wiring_v1 import _relation_palette


@dataclass(frozen=True)
class BipartiteDesignBranchProgress:
    source_tuple: tuple[int, ...]
    target_tuple: tuple[int, ...]
    status: str
    exact_structural_empty: bool
    source_progress: DesignTWLRecurrenceProgress | None
    target_progress: DesignTWLRecurrenceProgress | None
    child_aux_sizes: tuple[int, ...]
    aux_shrink_certified: bool
    reason: str


@dataclass(frozen=True)
class BipartiteDesignRecurrenceGate:
    status: str
    right_size: int
    structural_branches: int
    branches_discharged: int
    invariant_empty_branches: int
    progress_branches: int
    unresolved_branches: int
    max_child_aux_size: int | None
    alpha: float
    records: tuple[BipartiteDesignBranchProgress, ...]
    accounting_root: RecurrenceAccountingNode | None
    complete_structural_progress: bool
    local_cost_certified: bool
    local_log2_cost_bound: float
    exact: bool
    reason: str


def _placeholder(root_n: int, size: int, reason: str) -> RecurrenceAccountingNode:
    return RecurrenceAccountingNode(
        n=int(root_n),
        m=max(1, int(size)),
        operation_kind="unresolved_h6_exact_child",
        canonical=True,
        cost_certified=False,
        local_log2_cost_bound=0.0,
        children=(),
        terminal_certified=False,
        reason=reason,
    )


def _invariant_signature(outcome):
    return (
        outcome.status,
        tuple(sorted(len(cell) for cell in outcome.point_cells)),
        tuple(sorted(len(cell) for cell in outcome.output_partition)),
        len(outcome.dominant_cell),
        int(outcome.two_skeleton_rank),
        tuple(sorted(len(cell) for cell in outcome.constituent_components)),
        outcome.stable_signature,
    )


def certify_complete_design_cover_recurrence_progress(
    cover: AmbientDesignTupleCover,
    *,
    root_n: int,
    alpha: float = 0.75,
    max_tuple_states: int = 250000,
    max_twl_rounds: int | None = None,
    max_twl_work_units: int = 500000000,
    max_johnson_nodes: int = 500000,
) -> BipartiteDesignRecurrenceGate:
    """Certify strict auxiliary progress across the complete rev205 Design cover.

    This is a recurrence *gate*, not a child solver.  It consumes the exact rev205
    structural cover and checks every materialized branch.  Canonical k-WL outcome
    invariants that differ source/target discharge a branch as exact structural
    empty.  Every remaining branch must independently expose an alpha-smaller
    auxiliary measure through the already-validated rev195 Design recurrence
    adapter.  UPCC labels alone are never accepted: rev195 must either reduce the
    exact 2-skeleton to an alpha-smaller split/Johnson ground or return the typed
    ``requires_full_split_or_johnson`` unresolved status.

    When all branches are discharged, an ``aux_shrink`` accounting root is emitted.
    Its children are deliberately uncertified placeholders carrying only the proved
    smaller measures.  Global recurrence validation therefore still fails until the
    exact downstream SI proofs are wired into those children.  This separates the
    strict-progress theorem obligation from the next exact-child integration step.
    """
    if root_n < 1 or root_n < cover.wiring.relation_twin.source.relation.right_size:
        raise ValueError("root_n must dominate the current right auxiliary size")
    if not 0.5 <= alpha < 1.0:
        raise ValueError("alpha must lie in [1/2,1)")
    right_size = int(cover.wiring.relation_twin.source.relation.right_size)

    if cover.exact_empty:
        terminal = RecurrenceAccountingNode(
            n=int(root_n),
            m=max(1, right_size),
            operation_kind="h6_structural_exact_empty_terminal",
            canonical=True,
            cost_certified=True,
            local_log2_cost_bound=16.0 * log2(max(2, right_size)) + 32.0,
            children=(),
            terminal_certified=True,
            reason="rev205 complete structural cover is exact empty",
        )
        return BipartiteDesignRecurrenceGate(
            "certified_empty_design_cover_recurrence_terminal",
            right_size, cover.original_branch_count, 0, cover.original_branch_count,
            0, 0, None, float(alpha), (), terminal, True, True,
            terminal.local_log2_cost_bound, True,
            "the complete ambient Design cover is already exact empty, so no recursive child remains",
        )

    if not cover.exact or not cover.ambient_pairing_complete:
        return BipartiteDesignRecurrenceGate(
            "undetermined_incomplete_ambient_design_cover",
            right_size, cover.original_branch_count, 0, 0, 0,
            cover.original_branch_count, None, float(alpha), (), None,
            False, False, 0.0, False,
            "strict recurrence progress requires an exact complete rev205 ambient structural cover",
        )

    wiring = cover.wiring
    if wiring.status == "certified_unary_relation_half_bounded_coloring":
        source_sizes = tuple(sorted(len(cell) for cell in wiring.source_unary_partition))
        target_sizes = tuple(sorted(len(cell) for cell in wiring.target_unary_partition))
        if source_sizes != target_sizes:
            raise AssertionError("certified paired unary partitions have different shapes")
        largest = max(source_sizes, default=0)
        shrink = bool(source_sizes) and largest <= alpha * right_size + 1e-12 and largest < right_size
        if not shrink:
            return BipartiteDesignRecurrenceGate(
                "undetermined_unary_partition_without_alpha_shrink",
                right_size, 1, 0, 0, 0, 1, largest or None, float(alpha), (), None,
                False, True, 8.0 * log2(max(2, right_size)) + 24.0, True,
                "the exact unary canonical coloring did not meet the configured alpha-shrink recurrence gate",
            )
        children = tuple(
            AccountingChild(_placeholder(root_n, size, "unary relation color cell requires exact downstream parent SI"))
            for size in source_sizes
        )
        local = 8.0 * log2(max(2, right_size)) + 32.0
        root = RecurrenceAccountingNode(
            n=int(root_n), m=right_size, operation_kind="aux_shrink",
            canonical=True, cost_certified=True, local_log2_cost_bound=local,
            children=children, terminal_certified=False,
            reason="exact unary relation coloring gives alpha-bounded right-ground cells",
        )
        return BipartiteDesignRecurrenceGate(
            "certified_complete_unary_aux_shrink_plan",
            right_size, 1, 1, 0, 1, 0, largest, float(alpha), (), root,
            True, True, local, True,
            "every unary structural child has a mechanically certified alpha-smaller auxiliary measure; downstream exact SI proofs remain placeholders",
        )

    if wiring.status != "certified_relation_design_branch_plan" or wiring.branch_plan is None:
        return BipartiteDesignRecurrenceGate(
            "design_recurrence_gate_not_applicable",
            right_size, cover.original_branch_count, 0, 0, 0,
            cover.original_branch_count, None, float(alpha), (), None,
            False, True, 0.0, True,
            "the complete ambient cover is not the no-large-twin exact Design branch handled by this recurrence gate",
        )

    plan = wiring.branch_plan
    if not plan.complete or plan.status != "certified_complete_design_branch_plan":
        return BipartiteDesignRecurrenceGate(
            "undetermined_incomplete_design_branch_plan",
            right_size, int(plan.branch_count), 0, 0, 0, int(plan.branch_count),
            None, float(alpha), (), None, False, False,
            float(plan.local_log2_cost_bound), False,
            "the exact-k-WL Design family is not complete enough for branchwise recurrence certification",
        )

    source_outcomes = {tuple(o.individualized): o for o in plan.source_family.witness_outcomes}
    target_outcomes = {tuple(o.individualized): o for o in plan.target_family.witness_outcomes}
    source_palette = _relation_palette(wiring.relation_twin.source.relation)
    target_palette = _relation_palette(wiring.relation_twin.target.relation)
    arity = int(wiring.relation_arity)

    source_progress_cache = {}
    target_progress_cache = {}
    records = []
    accounting_children = []
    progress_count = 0
    empty_count = 0
    unresolved = 0
    max_child = 0
    extra_local = 0.0

    # rev205 may delete structurally unreachable tuple pairs.  Its surviving list
    # remains complete relative to the actual right image, so only those pairs need
    # recursive progress.  Exact source/target canonical invariant mismatch can
    # discard a survivor before downstream SI because no relation isomorphism maps
    # one individualized state to the other.
    for branch in cover.branches:
        xs = tuple(branch.source_tuple)
        yt = tuple(branch.target_tuple)
        so = source_outcomes.get(xs)
        to = target_outcomes.get(yt)
        if so is None or to is None:
            raise AssertionError("ambient branch tuple is absent from its complete exact-k-WL witness family")

        if _invariant_signature(so) != _invariant_signature(to):
            empty_count += 1
            records.append(BipartiteDesignBranchProgress(
                xs, yt, "exact_empty_design_outcome_invariant", True,
                None, None, (), False,
                "canonical individualized k-WL Design outcome invariants differ, excluding this ambient tuple branch exactly",
            ))
            continue

        if xs not in source_progress_cache:
            source_progress_cache[xs] = certify_design_twl_recurrence_progress(
                right_size, arity, source_palette, xs,
                root_n=root_n, alpha=alpha,
                max_tuple_states=max_tuple_states,
                max_rounds=max_twl_rounds,
                max_work_units=max_twl_work_units,
                max_johnson_nodes=max_johnson_nodes,
            )
            extra_local += source_progress_cache[xs].local_log2_cost_bound
        if yt not in target_progress_cache:
            target_progress_cache[yt] = certify_design_twl_recurrence_progress(
                right_size, arity, target_palette, yt,
                root_n=root_n, alpha=alpha,
                max_tuple_states=max_tuple_states,
                max_rounds=max_twl_rounds,
                max_work_units=max_twl_work_units,
                max_johnson_nodes=max_johnson_nodes,
            )
            extra_local += target_progress_cache[yt].local_log2_cost_bound
        sp = source_progress_cache[xs]
        tp = target_progress_cache[yt]

        if (
            sp.aux_shrink_certified
            and tp.aux_shrink_certified
            and sp.child_aux_sizes == tp.child_aux_sizes
            and sp.child_aux_sizes
        ):
            sizes = tuple(int(x) for x in sp.child_aux_sizes)
            largest = max(sizes)
            if largest > alpha * right_size + 1e-12 or largest >= right_size:
                raise AssertionError("rev195 certified a child that violates the requested alpha shrink")
            progress_count += 1
            max_child = max(max_child, largest)
            for size in sizes:
                accounting_children.append(AccountingChild(
                    _placeholder(
                        root_n,
                        size,
                        "exact downstream parent SI is required for one alpha-smaller Design structural child",
                    )
                ))
            records.append(BipartiteDesignBranchProgress(
                xs, yt, "certified_design_branch_aux_shrink", False,
                sp, tp, sizes, True,
                "source and target individualized Design states have matching canonical invariants and matching mechanically certified alpha-smaller recurrence measures",
            ))
        else:
            unresolved += 1
            records.append(BipartiteDesignBranchProgress(
                xs, yt, "unresolved_design_branch_recurrence_progress", False,
                sp, tp, (), False,
                "this structurally reachable tuple branch is exact/canonical but rev195 does not yet prove matching alpha-smaller source/target measures; a full Split-or-Johnson child remains",
            ))

    discharged = empty_count + progress_count
    local = float(plan.local_log2_cost_bound) + extra_local + log2(max(1, len(cover.branches))) + 32.0
    if unresolved:
        return BipartiteDesignRecurrenceGate(
            "requires_full_split_or_johnson_on_surviving_design_branch",
            right_size, len(cover.branches), discharged, empty_count, progress_count,
            unresolved, max_child or None, float(alpha), tuple(records), None,
            False, True, local, True,
            "at least one ambient-reachable branch in the complete Design cover lacks a certified alpha-smaller recurrence measure; no global progress claim is made",
        )

    if not cover.branches:
        raise AssertionError("nonempty complete Design cover contains no surviving branches")
    if not accounting_children and progress_count == 0:
        # Every surviving branch was eliminated by canonical individualized-state
        # invariants.  Relative to the actual ambient right action this is an exact
        # structural empty instance even though rev205 itself did not compare these
        # stronger post-individualization invariants.
        terminal = RecurrenceAccountingNode(
            n=int(root_n), m=right_size,
            operation_kind="h6_design_outcome_invariant_empty_terminal",
            canonical=True, cost_certified=True, local_log2_cost_bound=local,
            children=(), terminal_certified=True,
            reason="every ambient tuple branch is excluded by exact canonical individualized Design invariants",
        )
        return BipartiteDesignRecurrenceGate(
            "certified_design_outcome_invariant_empty",
            right_size, len(cover.branches), discharged, empty_count, 0, 0,
            None, float(alpha), tuple(records), terminal,
            True, True, local, True,
            "all ambient-reachable Design tuple branches are exact-empty by stronger canonical outcome invariants",
        )

    root = RecurrenceAccountingNode(
        n=int(root_n), m=right_size, operation_kind="aux_shrink",
        canonical=True, cost_certified=True, local_log2_cost_bound=local,
        children=tuple(accounting_children), terminal_certified=False,
        reason="every ambient-reachable nonempty Design structural branch has matching alpha-smaller auxiliary measures; exact downstream SI/accounting must replace the child placeholders",
    )
    return BipartiteDesignRecurrenceGate(
        "certified_complete_design_aux_shrink_plan",
        right_size, len(cover.branches), discharged, empty_count, progress_count, 0,
        max_child or None, float(alpha), tuple(records), root,
        True, True, local, True,
        "the complete rev205 ambient Design cover is discharged branch-by-branch by exact canonical emptiness or strict alpha-smaller recurrence progress; downstream exact SI proofs are still deliberately unresolved placeholders",
    )
