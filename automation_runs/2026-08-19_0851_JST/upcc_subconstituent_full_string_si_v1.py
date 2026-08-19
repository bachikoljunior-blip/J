from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import permutations
from math import factorial, log2

from design_branch_tuple_transport_v1 import DesignTupleBranch, DesignTupleTransportPlan
from design_tuple_full_string_union_si_v1 import DesignTupleFullStringSI, solve_design_tuple_transport_full_string
from signed_johnson_ground_profile_partition_si_v1 import _signed_partition_transporter
from upcc_subconstituent_split_family_v1 import (
    UPCCSubconstituentSplitFamily,
    certify_upcc_subconstituent_split_family,
)
from coset_stabilizer_primitives import RightCoset


@dataclass(frozen=True)
class UPCCSubconstituentFullStringSI:
    status: str
    source_family: UPCCSubconstituentSplitFamily
    target_family: UPCCSubconstituentSplitFamily
    transport_plan: DesignTupleTransportPlan | None
    full_string_result: DesignTupleFullStringSI | None
    partition_pair_count: int
    exact: bool
    complete: bool
    local_log2_cost_bound: float
    reason: str


def _matching_cell_permutation_count(source_cells, target_cells):
    if len(source_cells) != len(target_cells):
        return 0
    if len(source_cells[0]) != 1 or len(target_cells[0]) != 1:
        return 0
    ss = [len(cell) for cell in source_cells[1:]]
    ts = [len(cell) for cell in target_cells[1:]]
    if Counter(ss) != Counter(ts):
        return 0
    counts = Counter(ts)
    out = 1
    for multiplicity in counts.values():
        out *= factorial(multiplicity)
    return out


def _matching_target_orders(source_cells, target_cells):
    source_sizes = tuple(len(cell) for cell in source_cells[1:])
    indices = tuple(range(1, len(target_cells)))
    for perm in permutations(indices):
        if tuple(len(target_cells[i]) for i in perm) == source_sizes:
            yield (target_cells[0],) + tuple(target_cells[i] for i in perm)


def upcc_subconstituent_full_string_isomorphism(
    group,
    lifted_generators,
    vertex_count: int,
    arity: int,
    source_relation,
    target_relation,
    source_values,
    target_values,
    *,
    root_n: int,
    alpha: float = 0.9,
    max_tuple_states: int = 250000,
    max_twl_rounds: int | None = None,
    max_twl_work_units: int = 100000000,
    max_partition_pair_branches: int = 200000,
    max_partition_states: int = 200000,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 256,
    max_depth: int = 64,
) -> UPCCSubconstituentFullStringSI:
    """Solve the alpha-shrinking UPCC subconstituent branch family exactly.

    Source and target independently expose the complete all-root subconstituent
    families from the exact stable k-WL 2-skeleton. For every root pair, all
    bijections between non-root cells having the same cardinalities are retained.
    This deliberately overcovers when stable color IDs alone would already align,
    but it guarantees that every true color-preserving isomorphism is represented
    without assuming cross-instance numeric color-ID comparability.

    Each ordered partition pair is intersected exactly with the supplied signed
    ambient action by the existing Schreier partition transporter. Only proved-empty
    branches are discarded. The resulting complete coset family is then intersected
    with the original full string and reconstructed by the existing exact branch-
    union SI routine. Resource caps fail closed before a partial cover is exposed.

    This is an exact small/explicit UPCC child. It does not by itself certify the
    global Split-or-Johnson recurrence or a theorem-scale bound for cell-permutation
    branching; those remain separate accounting obligations.
    """
    if max_partition_pair_branches < 1 or max_partition_states < 1:
        raise ValueError("partition branch/state caps must be positive")
    n = int(group.degree)
    source = tuple(source_values)
    target = tuple(target_values)
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate the ambient degree")

    sf = certify_upcc_subconstituent_split_family(
        vertex_count,
        arity,
        source_relation,
        root_n=root_n,
        alpha=alpha,
        max_tuple_states=max_tuple_states,
        max_rounds=max_twl_rounds,
        max_work_units=max_twl_work_units,
    )
    tf = certify_upcc_subconstituent_split_family(
        vertex_count,
        arity,
        target_relation,
        root_n=root_n,
        alpha=alpha,
        max_tuple_states=max_tuple_states,
        max_rounds=max_twl_rounds,
        max_work_units=max_twl_work_units,
    )
    base_bound = sf.branch_log2_bound + tf.branch_log2_bound + 16.0
    required = "certified_complete_upcc_subconstituent_split_family"
    if sf.status != required or tf.status != required:
        return UPCCSubconstituentFullStringSI(
            "undetermined_upcc_subconstituent_family",
            sf,
            tf,
            None,
            None,
            0,
            False,
            False,
            0.0,
            "exact full-string UPCC recursion requires complete alpha-shrinking source and target subconstituent families",
        )

    pair_count = 0
    for scells in sf.partitions:
        for tcells in tf.partitions:
            pair_count += _matching_cell_permutation_count(scells, tcells)
            if pair_count > max_partition_pair_branches:
                return UPCCSubconstituentFullStringSI(
                    "undetermined_upcc_partition_pair_limit",
                    sf,
                    tf,
                    None,
                    None,
                    pair_count,
                    False,
                    False,
                    0.0,
                    "the complete root/subconstituent partition cover exceeds the explicit materialization cap",
                )

    if pair_count == 0:
        return UPCCSubconstituentFullStringSI(
            "exact_empty_upcc_partition_shape_invariant",
            sf,
            tf,
            DesignTupleTransportPlan(
                "exact_empty_upcc_partition_shape_invariant",
                n,
                int(vertex_count),
                1,
                0,
                0,
                (),
                base_bound,
                True,
                True,
                "no source/target root partitions have matching non-root cell-size multisets",
            ),
            None,
            0,
            True,
            True,
            base_bound,
            "subconstituent partition-size invariants prove the UPCC branch family empty",
        )

    kept = []
    action_steps = 0
    max_orbit_states = 0
    materialized = 0
    for sroot, scells in zip(sf.roots, sf.partitions):
        for troot, tcells in zip(tf.roots, tf.partitions):
            for ordered_target in _matching_target_orders(scells, tcells):
                materialized += 1
                transport = _signed_partition_transporter(
                    group,
                    lifted_generators,
                    scells,
                    ordered_target,
                    max_states=max_partition_states,
                )
                action_steps += int(transport.action_steps)
                max_orbit_states = max(max_orbit_states, int(transport.orbit_states))
                if transport.status == "undetermined_signed_ground_partition_orbit_limit":
                    return UPCCSubconstituentFullStringSI(
                        transport.status, sf, tf, None, None, materialized,
                        False, False, 0.0,
                        "an exact partition branch exceeded the orbit-state cap; the complete cover is withheld",
                    )
                if transport.status == "no_signed_ground_partition_transporter":
                    continue
                if transport.status != "signed_ground_partition_transporter_coset" or transport.transporter is None:
                    return UPCCSubconstituentFullStringSI(
                        "undetermined_upcc_partition_transport", sf, tf, None, None,
                        materialized, False, False, 0.0,
                        "a complete UPCC partition branch returned an unrecognized transporter status",
                    )
                kept.append(
                    DesignTupleBranch(
                        (int(sroot),),
                        (int(troot),),
                        transport.status,
                        RightCoset(transport.stabilizer, transport.transporter),
                        int(transport.orbit_states),
                        int(transport.action_steps),
                        "exact ambient transporter for one complete UPCC root/subconstituent partition pairing",
                    )
                )

    local_bound = (
        base_bound
        + log2(max(1, pair_count))
        + log2(max(1, action_steps))
        + 4.0 * log2(max(2, n + int(vertex_count) + max_orbit_states))
        + 32.0
    )
    if not kept:
        plan = DesignTupleTransportPlan(
            "exact_empty_design_tuple_transport_cover",
            n,
            int(vertex_count),
            1,
            pair_count,
            0,
            (),
            local_bound,
            True,
            True,
            "every partition pair in the complete UPCC subconstituent cover has exact empty ambient transporter",
        )
        return UPCCSubconstituentFullStringSI(
            "exact_empty_upcc_subconstituent_transport",
            sf,
            tf,
            plan,
            None,
            pair_count,
            True,
            True,
            local_bound,
            plan.reason,
        )

    plan = DesignTupleTransportPlan(
        "certified_complete_design_tuple_transport_cover",
        n,
        int(vertex_count),
        1,
        pair_count,
        len(kept),
        tuple(kept),
        local_bound,
        False,
        True,
        "all root pairs and all size-compatible subconstituent-cell bijections were covered; only proved-empty exact ambient transporters were removed",
    )
    full = solve_design_tuple_transport_full_string(
        group,
        plan,
        source,
        target,
        root_n=root_n,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_depth=max_depth,
    )
    if not full.exact:
        return UPCCSubconstituentFullStringSI(
            "undetermined_upcc_subconstituent_full_string",
            sf,
            tf,
            plan,
            full,
            pair_count,
            False,
            False,
            0.0,
            full.reason,
        )
    return UPCCSubconstituentFullStringSI(
        "exact_empty_upcc_subconstituent_full_string" if full.coset is None else "exact_upcc_subconstituent_full_string_coset",
        sf,
        tf,
        plan,
        full,
        pair_count,
        True,
        True,
        full.explicit_union_log2_cost_bound,
        "complete UPCC subconstituent partition cover, exact ambient transport, and exact full-string union reconstruction completed",
    )
