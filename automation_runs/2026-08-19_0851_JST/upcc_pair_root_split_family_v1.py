from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from math import comb, log2

from colored_subset_exact_twl_design_v1 import (
    ExactTWLDesignOutcome,
    classify_stable_twl_design,
    stable_colored_subset_twl,
)


@dataclass(frozen=True)
class UPCCPairRootSplitFamily:
    status: str
    vertex_count: int
    arity: int
    alpha: float
    base_design_status: str
    root_pairs: tuple[tuple[int, int], ...]
    branch_design_statuses: tuple[str, ...]
    partitions: tuple[tuple[tuple[int, ...], ...], ...]
    child_aux_sizes: tuple[tuple[int, ...], ...]
    failed_root_pair: tuple[int, int] | None
    checked_root_pairs: int
    max_child_aux_size: int | None
    branch_count: int
    branch_log2_bound: float
    tuple_states_per_run: int
    preflight_work_upper_bound: int
    executed_work_units: int
    aux_shrink_certified: bool
    complete_root_cover: bool
    equivariant_family: bool
    exact: bool
    complete: bool
    reason: str


def _partition_sizes(
    partition: tuple[tuple[int, ...], ...],
    vertex_count: int,
) -> tuple[int, ...]:
    flat = tuple(x for cell in partition for x in cell)
    if len(flat) != vertex_count or len(set(flat)) != vertex_count:
        raise AssertionError("k-WL output partition is not a disjoint vertex cover")
    if tuple(sorted(flat)) != tuple(range(vertex_count)):
        raise AssertionError("k-WL output partition contains an out-of-range vertex")
    if any(not cell for cell in partition):
        raise AssertionError("k-WL output partition contains an empty cell")
    return tuple(sorted(len(cell) for cell in partition))


def certify_upcc_pair_root_split_family(
    vertex_count: int,
    arity: int,
    colors,
    *,
    root_n: int,
    alpha: float = 0.9,
    max_root_pairs: int = 200000,
    max_tuple_states: int = 250000,
    max_rounds: int | None = None,
    max_work_units: int = 100000000,
    max_total_work_units: int = 5000000000,
) -> UPCCPairRootSplitFamily:
    """Certify a complete ordered two-root split family for a full-ground UPCC.

    rev197 reads every one-root subconstituent partition directly from the stable
    unindividualized 2-skeleton.  Some exact full-ground UPCCs still have a large
    one-root cell.  This routine handles a strictly stronger finite subcase by
    retaining *every ordered injective pair* of roots, rerunning the exact
    correlated-replacement k-WL refinement relative to those two ordered marks,
    and requiring every resulting branch to expose an alpha-bounded canonical
    point partition.

    The full ordered-pair family is equivariant as a set: a relation isomorphism
    sends ``(a,b)`` to ``(g(a),g(b))`` while preserving the two mark positions.
    No root pair is selected by its numeric labels.  The branch multiplicity is
    exactly ``v*(v-1) <= root_n**2``.

    This is structural auxiliary-shrink evidence only.  It does not pair source
    and target branches, solve their downstream String Isomorphism children,
    construct a Johnson embedding, or prove the general corrected
    Split-or-Johnson recursion.  Every resource or completeness failure is
    returned fail closed.
    """
    v = int(vertex_count)
    k = int(arity)
    r = int(root_n)
    palette = tuple(colors)

    if v < 2:
        raise ValueError("two-root UPCC splitting requires vertex_count>=2")
    if not 1 <= k <= v:
        raise ValueError("arity must lie in [1, vertex_count]")
    if len(palette) != comb(v, k):
        raise ValueError("colors must contain one entry for every k-subset")
    if r < v:
        raise ValueError("root_n must dominate the UPCC ground size")
    if not 0.5 <= alpha < 1.0:
        raise ValueError("alpha must lie in [1/2,1)")
    if max_root_pairs < 1:
        raise ValueError("max_root_pairs must be positive")
    if max_tuple_states < 1 or max_work_units < 1 or max_total_work_units < 1:
        raise ValueError("resource caps must be positive")
    if max_rounds is not None and int(max_rounds) < 1:
        raise ValueError("max_rounds must be positive when supplied")

    branch_count = v * (v - 1)
    branch_log2_bound = log2(max(1, branch_count))
    if branch_log2_bound > 2.0 * log2(max(2, r)) + 1e-12:
        raise AssertionError("ordered-pair branch bound exceeds root_n^2")

    tuple_states = v**k
    round_cap = tuple_states if max_rounds is None else int(max_rounds)
    per_run_algorithm_bound = tuple_states * (1 + round_cap * v * k)
    # The underlying exact routine can stop at max_work_units before another
    # round, but it always pays the initial tuple-state construction.
    per_run_executed_bound = max(
        tuple_states,
        min(per_run_algorithm_bound, int(max_work_units)),
    )
    run_count = branch_count + 1
    bookkeeping_bound = run_count * (v * v + v + k + 1)
    preflight_bound = run_count * per_run_executed_bound + bookkeeping_bound

    def result(
        status: str,
        *,
        base_status: str = "",
        root_pairs: tuple[tuple[int, int], ...] = (),
        branch_statuses: tuple[str, ...] = (),
        partitions: tuple[tuple[tuple[int, ...], ...], ...] = (),
        sizes: tuple[tuple[int, ...], ...] = (),
        failed_pair: tuple[int, int] | None = None,
        executed_work: int = 0,
        aux_shrink: bool = False,
        complete_root_cover: bool = False,
        equivariant_family: bool = False,
        exact: bool = False,
        complete: bool = False,
        reason: str,
    ) -> UPCCPairRootSplitFamily:
        largest = max((max(row) for row in sizes if row), default=None)
        return UPCCPairRootSplitFamily(
            status=status,
            vertex_count=v,
            arity=k,
            alpha=float(alpha),
            base_design_status=base_status,
            root_pairs=root_pairs,
            branch_design_statuses=branch_statuses,
            partitions=partitions,
            child_aux_sizes=sizes,
            failed_root_pair=failed_pair,
            checked_root_pairs=len(root_pairs),
            max_child_aux_size=largest,
            branch_count=branch_count,
            branch_log2_bound=branch_log2_bound,
            tuple_states_per_run=tuple_states,
            preflight_work_upper_bound=preflight_bound,
            executed_work_units=executed_work,
            aux_shrink_certified=aux_shrink,
            complete_root_cover=complete_root_cover,
            equivariant_family=equivariant_family,
            exact=exact,
            complete=complete,
            reason=reason,
        )

    if tuple_states > max_tuple_states:
        return result(
            "upcc_pair_root_tuple_state_cap_closed",
            reason="one exact k-WL run exceeds max_tuple_states before any root branch is materialized",
        )
    if branch_count > max_root_pairs:
        return result(
            "upcc_pair_root_branch_cap_closed",
            reason="the complete ordered two-root cover exceeds max_root_pairs",
        )
    if preflight_bound > max_total_work_units:
        return result(
            "upcc_pair_root_total_work_preflight_closed",
            reason=(
                "the input-independent bound for the base run plus every ordered "
                "two-root k-WL branch exceeds max_total_work_units"
            ),
        )

    base_stable = stable_colored_subset_twl(
        v,
        k,
        palette,
        individualized=(),
        max_tuple_states=max_tuple_states,
        max_rounds=max_rounds,
        max_work_units=max_work_units,
    )
    executed_work = int(base_stable.work_units)
    base: ExactTWLDesignOutcome = classify_stable_twl_design(base_stable, alpha=alpha)
    if not base.exact:
        return result(
            base.status,
            base_status=base.status,
            executed_work=executed_work,
            reason=base.reason,
        )
    if base.status != "certified_twl_upcc":
        return result(
            "not_upcc_pair_root_split_leaf",
            base_status=base.status,
            executed_work=executed_work,
            exact=True,
            reason=(
                "the exact unindividualized Design outcome is not the unresolved "
                "UPCC child handled by the two-root family"
            ),
        )
    if tuple(base.dominant_cell) != tuple(range(v)):
        return result(
            "undetermined_upcc_pair_root_not_ful_ground",
            base_status=base.status,
            executed_work=executed_work,
            exact=True,
            reason=(
                "the certified UPCC occupies only a dominant fiber; use the "
                "surrounding Design partition recursion before pair-root splitting"
            ),
        )

    planned_pairs = tuple(permutations(range(v), 2))
    if len(planned_pairs) != branch_count:
        raise AssertionError("ordered pair enumeration is incomplete")

    checked_pairs: list[tuple[int, int]] = []
    statuses: list[str] = []
    partitions: list[tuple[tuple[int, ...], ...]] = []
    child_sizes: list[tuple[int, ...]] = []
    progress_statuses = {
        "certified_twl_alpha_coloring",
        "certified_twl_imprimitive_alpha_partition",
    }

    for pair in planned_pairs:
        stable = stable_colored_subset_twl(
            v,
            k,
            palette,
            individualized=pair,
            max_tuple_states=max_tuple_states,
            max_rounds=max_rounds,
            max_work_units=max_work_units,
        )
        executed_work += int(stable.work_units)
        outcome: ExactTWLDesignOutcome = classify_stable_twl_design(stable, alpha=alpha)
        checked_pairs.append(pair)
        statuses.append(outcome.status)

        if not outcome.exact:
            return result(
                outcome.status,
                base_status=base.status,
                root_pairs=tuple(checked_pairs),
                branch_statuses=tuple(statuses),
                partitions=tuple(partitions),
                sizes=tuple(child_sizes),
                failed_pair=pair,
                executed_work=executed_work,
                reason=(
                    "an ordered two-root exact k-WL branch hit a resource or "
                    "verification boundary; the family is withheld"
                ),
            )
        if outcome.status not in progress_statuses or not outcome.output_partition:
            return result(
                "upcc_pair_root_branch_not_alpha_shrinking",
                base_status=base.status,
                root_pairs=tuple(checked_pairs),
                branch_statuses=tuple(statuses),
                partitions=tuple(partitions),
                sizes=tuple(child_sizes),
                failed_pair=pair,
                executed_work=executed_work,
                exact=True,
                reason=(
                    "at least one exact ordered two-root branch remains a clique, "
                    "UPCC, or otherwise nonshrinking Design state"
                ),
            )

        partition = tuple(tuple(cell) for cell in outcome.output_partition)
        sizes = _partition_sizes(partition, v)
        largest = max(sizes)
        shrink = largest < v and largest <= alpha * v + 1e-12
        if not shrink:
            raise AssertionError(
                "a certified alpha-partition branch violates its recorded shrink bound"
            )
        partitions.append(partition)
        child_sizes.append(sizes)

    if tuple(checked_pairs) != planned_pairs:
        raise AssertionError("successful pair-root family omitted an ordered root pair")
    if executed_work > preflight_bound:
        raise AssertionError("executed k-WL work exceeded the admitted static bound")

    return result(
        "certified_complete_upcc_pair_root_split_family",
        base_status=base.status,
        root_pairs=tuple(checked_pairs),
        branch_statuses=tuple(statuses),
        partitions=tuple(partitions),
        sizes=tuple(child_sizes),
        executed_work=executed_work,
        aux_shrink=True,
        complete_root_cover=True,
        equivariant_family=True,
        exact=True,
        complete=True,
        reason=(
            "every ordered injective root pair is retained, and every exact "
            "two-root correlated k-WL outcome exposes an alpha-bounded canonical "
            "partition; this closes a strict structural subcase beyond the "
            "one-root UPCC split family without claiming downstream exact SI"
        ),
    )
