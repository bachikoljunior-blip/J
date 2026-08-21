from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from math import comb, log2

from colored_subset_exact_twl_design_v1 import (
    classify_stable_twl_design,
    stable_colored_subset_twl,
)


_ACCEPTED_SPLITS = {
    "certified_twl_alpha_coloring",
    "certified_twl_imprimitive_alpha_partition",
}


@dataclass(frozen=True)
class UPCCPairRootSplitFamily:
    status: str
    vertex_count: int
    arity: int
    design_status: str
    root_pairs: tuple[tuple[int, int], ...]
    branch_statuses: tuple[str, ...]
    partitions: tuple[tuple[tuple[int, ...], ...], ...]
    child_aux_sizes: tuple[tuple[int, ...], ...]
    max_child_aux_size: int | None
    branch_count: int
    tuple_states_per_run: int
    reserved_work_units: int
    used_work_units: int
    branch_log2_bound: float
    aux_shrink_fraction: float
    aux_shrink_certified: bool
    exact: bool
    complete: bool
    reason: str


def _closed(
    status: str,
    v: int,
    k: int,
    *,
    design_status: str = "not_started",
    branch_count: int = 0,
    tuple_states: int = 0,
    reserved_work: int = 0,
    used_work: int = 0,
    alpha: float,
    exact: bool = False,
    reason: str,
) -> UPCCPairRootSplitFamily:
    return UPCCPairRootSplitFamily(
        status, v, k, design_status, (), (), (), (), None, branch_count,
        tuple_states, reserved_work, used_work, 0.0, alpha, False, exact,
        False, reason,
    )


def _sat_mul(a: int, b: int, limit: int) -> int:
    if a == 0 or b == 0:
        return 0
    if a > limit // b:
        return limit
    return min(limit, a * b)


def certify_upcc_pair_root_split_family(
    vertex_count: int,
    arity: int,
    colors,
    *,
    root_n: int,
    alpha: float = 0.9,
    max_pair_branches: int = 250_000,
    max_tuple_states: int = 250_000,
    max_rounds: int | None = None,
    per_run_work_cap: int = 100_000_000,
    max_total_work_units: int = 1_000_000_000,
) -> UPCCPairRootSplitFamily:
    """Certify the complete ordered two-root split family of a full-ground UPCC.

    Every injective ordered pair is retained.  Each pair is passed as two ordered
    constants to exact correlated-replacement k-WL, and only an alpha-bounded
    canonical point coloring or an alpha-bounded imprimitive partition counts as
    split progress.  The complete branch count and worst-case work are reserved
    before the base UPCC check or the first pair run, so resource rejection has no
    partially executed prefix.

    This is a bounded exact terminal for the cases it accepts.  It is not the
    corrected general Split-or-Johnson theorem: a branch that remains UPCC or
    exposes a Johnson alternative is reported unresolved rather than promoted.
    """
    v = int(vertex_count)
    k = int(arity)
    r = int(root_n)
    palette = tuple(colors)
    if v < 2 or not 1 <= k <= v:
        raise ValueError("pair-root certification requires 2<=vertex_count and valid arity")
    if r < v:
        raise ValueError("root_n must dominate the UPCC ground size")
    if not 0.5 <= alpha < 1.0:
        raise ValueError("alpha must lie in [1/2,1)")
    if min(max_pair_branches, max_tuple_states, per_run_work_cap, max_total_work_units) < 1:
        raise ValueError("resource caps must be positive")
    if max_rounds is not None and int(max_rounds) < 1:
        raise ValueError("max_rounds must be positive when supplied")
    if len(palette) != comb(v, k):
        raise ValueError("colors must contain one entry for every k-subset")

    pair_count = v * (v - 1)
    tuple_states = v ** k
    run_count = pair_count + 1  # base UPCC certificate plus every ordered pair
    reserve_limit = max_total_work_units + 1
    reserved_work = _sat_mul(run_count, per_run_work_cap, reserve_limit)
    if pair_count > max_pair_branches:
        return _closed(
            "undetermined_upcc_pair_root_branch_cap", v, k,
            branch_count=pair_count, tuple_states=tuple_states,
            reserved_work=reserved_work, alpha=alpha,
            reason="the complete ordered injective root-pair cover exceeds max_pair_branches; no k-WL run started",
        )
    if tuple_states > max_tuple_states:
        return _closed(
            "undetermined_upcc_pair_root_tuple_state_cap", v, k,
            branch_count=pair_count, tuple_states=tuple_states,
            reserved_work=reserved_work, alpha=alpha,
            reason="one exact k-WL run exceeds max_tuple_states; no k-WL run started",
        )
    if reserved_work > max_total_work_units:
        return _closed(
            "undetermined_upcc_pair_root_total_work_cap", v, k,
            branch_count=pair_count, tuple_states=tuple_states,
            reserved_work=reserved_work, alpha=alpha,
            reason="the base run and complete ordered pair cover cannot all be reserved; no k-WL run started",
        )

    base = stable_colored_subset_twl(
        v, k, palette, individualized=(), max_tuple_states=max_tuple_states,
        max_rounds=max_rounds, max_work_units=per_run_work_cap,
    )
    used_work = base.work_units
    base_outcome = classify_stable_twl_design(base, alpha=alpha)
    if not base_outcome.exact:
        return _closed(
            base_outcome.status, v, k, design_status=base_outcome.status,
            branch_count=pair_count, tuple_states=tuple_states,
            reserved_work=reserved_work, used_work=used_work, alpha=alpha,
            reason=base_outcome.reason,
        )
    if base_outcome.status != "certified_twl_upcc" or tuple(base_outcome.dominant_cell) != tuple(range(v)):
        return _closed(
            "not_full_ground_upcc_pair_root_leaf", v, k,
            design_status=base_outcome.status, branch_count=pair_count,
            tuple_states=tuple_states, reserved_work=reserved_work,
            used_work=used_work, alpha=alpha, exact=True,
            reason="the exact base outcome is not a full-ground homogeneous UPCC, so this pair-root terminal does not apply",
        )

    root_pairs = tuple(permutations(range(v), 2))
    statuses = []
    partitions = []
    sizes = []
    for pair in root_pairs:
        stable = stable_colored_subset_twl(
            v, k, palette, individualized=pair,
            max_tuple_states=max_tuple_states, max_rounds=max_rounds,
            max_work_units=per_run_work_cap,
        )
        used_work += stable.work_units
        outcome = classify_stable_twl_design(stable, alpha=alpha)
        if not outcome.exact:
            return UPCCPairRootSplitFamily(
                outcome.status, v, k, base_outcome.status,
                root_pairs[: len(statuses)], tuple(statuses), tuple(partitions),
                tuple(sizes), max((max(row) for row in sizes), default=None),
                pair_count, tuple_states, reserved_work, used_work,
                2.0 * log2(max(2, r)), alpha, False, False, False,
                "an ordered pair k-WL branch failed before the complete cover was executed: " + outcome.reason,
            )
        statuses.append(outcome.status)
        partition = outcome.output_partition if outcome.status in _ACCEPTED_SPLITS else ()
        partitions.append(partition)
        sizes.append(tuple(len(cell) for cell in partition))

    if used_work > reserved_work:
        raise AssertionError("pair-root execution exceeded its complete preflight reservation")
    largest = max((max(row) for row in sizes if row), default=None)
    all_split = all(status in _ACCEPTED_SPLITS for status in statuses)
    if not all_split:
        return UPCCPairRootSplitFamily(
            "upcc_pair_root_not_alpha_shrinking", v, k, base_outcome.status,
            root_pairs, tuple(statuses), tuple(partitions), tuple(sizes), largest,
            pair_count, tuple_states, reserved_work, used_work,
            2.0 * log2(max(2, r)), alpha, False, True, True,
            "every ordered root pair was executed exactly, but at least one branch remained outside alpha-coloring/imprimitive split; keep the corrected general Split-or-Johnson child unresolved",
        )

    return UPCCPairRootSplitFamily(
        "certified_complete_upcc_pair_root_split_family", v, k,
        base_outcome.status, root_pairs, tuple(statuses), tuple(partitions),
        tuple(sizes), largest, pair_count, tuple_states, reserved_work,
        used_work, 2.0 * log2(max(2, r)), alpha, True, True, True,
        "all ordered injective root pairs were retained and every exact marked k-WL branch produced an alpha-bounded canonical coloring or imprimitive partition",
    )
