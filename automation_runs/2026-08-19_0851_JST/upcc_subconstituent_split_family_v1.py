from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import log2

from colored_subset_exact_twl_design_v1 import (
    ExactTWLDesignOutcome,
    classify_stable_twl_design,
    stable_colored_subset_twl,
)


@dataclass(frozen=True)
class UPCCSubconstituentSplitFamily:
    status: str
    vertex_count: int
    arity: int
    design_status: str
    roots: tuple[int, ...]
    partitions: tuple[tuple[tuple[int, ...], ...], ...]
    child_aux_sizes: tuple[tuple[int, ...], ...]
    max_child_aux_size: int | None
    branch_count: int
    branch_log2_bound: float
    aux_shrink_fraction: float
    aux_shrink_certified: bool
    exact: bool
    complete: bool
    reason: str


def _root_subconstituent_partition(pair_colors, root: int):
    """Canonical partition relative to one individualized UPCC point.

    The root is a singleton. Every other point is grouped by the exact ordered
    pair of stable 2-skeleton colors seen from/to the root. No graph-theoretic
    theorem is assumed here: the partition is read directly from the mechanically
    stable pair-color matrix.
    """
    v = len(pair_colors)
    buckets = defaultdict(list)
    for x in range(v):
        if x == root:
            continue
        token = (pair_colors[root][x], pair_colors[x][root])
        buckets[token].append(x)
    cells = [(root,)]
    for token in sorted(buckets, key=repr):
        cells.append(tuple(buckets[token]))
    return tuple(cells)


def certify_upcc_subconstituent_split_family(
    vertex_count: int,
    arity: int,
    colors,
    *,
    root_n: int,
    alpha: float = 0.9,
    max_tuple_states: int = 250000,
    max_rounds: int | None = None,
    max_work_units: int = 100000000,
) -> UPCCSubconstituentSplitFamily:
    """Turn a full-ground exact UPCC into a complete one-point split family.

    The rev193 exact correlated-replacement k-WL verifier first proves the UPCC
    outcome and exact coherent 2-skeleton. For every possible root point we then
    expose its complete subconstituent partition: root singleton plus the stable
    directed pair-color neighborhoods. The family contains *all* roots, so it is
    equivariant as a set under every color-preserving isomorphism; no arbitrary
    representative root is selected.

    This routine promotes the family to recurrence progress only if every rooted
    partition has all cells at most ``alpha * v``. The branch count is exactly v,
    hence its logarithmic multiplicity charge is at most log2(root_n) when
    ``v <= root_n``. If the UPCC is not full-ground homogeneous or any rooted
    subconstituent remains too large, the result fails closed. Downstream exact
    source/target root pairing and ambient string-isomorphism recursion remain a
    separate child problem.
    """
    v = int(vertex_count)
    k = int(arity)
    r = int(root_n)
    if r < v or v < 1:
        raise ValueError("root_n must dominate the positive UPCC ground size")
    if not 0.5 <= alpha < 1.0:
        raise ValueError("alpha must lie in [1/2,1)")

    stable = stable_colored_subset_twl(
        v,
        k,
        tuple(colors),
        individualized=(),
        max_tuple_states=max_tuple_states,
        max_rounds=max_rounds,
        max_work_units=max_work_units,
    )
    outcome: ExactTWLDesignOutcome = classify_stable_twl_design(stable, alpha=alpha)
    base_bound = (
        log2(max(2, stable.work_units + 1))
        + 6.0 * log2(max(2, v))
        + 24.0
    )
    if not outcome.exact:
        return UPCCSubconstituentSplitFamily(
            outcome.status, v, k, outcome.status, (), (), (), None, 0,
            0.0, alpha, False, False, False, outcome.reason,
        )
    if outcome.status != "certified_twl_upcc":
        return UPCCSubconstituentSplitFamily(
            "not_upcc_subconstituent_leaf", v, k, outcome.status, (), (), (), None,
            0, base_bound, alpha, False, True, False,
            "the exact k-WL Design outcome is not the unresolved UPCC child handled by this routine",
        )

    full_ground = tuple(outcome.dominant_cell) == tuple(range(v))
    if not full_ground:
        return UPCCSubconstituentSplitFamily(
            "undetermined_upcc_not_full_ground_homogeneous", v, k, outcome.status,
            (), (), (), None, 0, base_bound, alpha, False, True, False,
            "the certified UPCC does not occupy the entire auxiliary ground; use the surrounding Design partition recursion instead",
        )

    roots = tuple(range(v))
    partitions = tuple(_root_subconstituent_partition(stable.pair_colors, root) for root in roots)
    sizes = tuple(tuple(len(cell) for cell in partition) for partition in partitions)
    largest = max((max(row) for row in sizes), default=0)
    all_shrink = bool(partitions) and all(
        max(row) < v and max(row) <= alpha * v + 1e-12
        for row in sizes
    )
    branch_bound = log2(max(1, v))
    if not all_shrink:
        return UPCCSubconstituentSplitFamily(
            "upcc_subconstituent_not_alpha_shrinking", v, k, outcome.status,
            roots, partitions, sizes, largest, v, branch_bound,
            alpha, False, True, True,
            "all root subconstituent partitions were constructed exactly, but at least one contains a cell larger than the required alpha fraction",
        )

    return UPCCSubconstituentSplitFamily(
        "certified_complete_upcc_subconstituent_split_family",
        v,
        k,
        outcome.status,
        roots,
        partitions,
        sizes,
        largest,
        v,
        branch_bound,
        alpha,
        True,
        True,
        True,
        "every possible root is retained and every exact stable 2-skeleton subconstituent cell is alpha-smaller; this gives a complete equivariant one-point auxiliary-shrink branch family",
    )
