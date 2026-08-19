from __future__ import annotations

from dataclasses import dataclass
from math import log2

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


def _ordered_cell_size_profile(cells):
    return tuple(len(cell) for cell in cells)


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
    """Solve the alpha-shrinking UPCC subconstituent root family exactly.

    The rev193 exact k-WL implementation assigns every refinement color by sorting
    exact refinement signatures. Consequently its stable pair-color IDs are
    canonical, not encounter-order labels: under a true color-preserving relation
    isomorphism, the source and target root subconstituent cells occur in the same
    token order. The rev197 family uses precisely those ordered
    ``(color(root,x), color(x,root))`` tokens.

    We therefore retain every source/target root pair whose *ordered* cell-size
    profile agrees and intersect that canonical partition pairing with the supplied
    signed ambient action. Every true relation isomorphism maps some source root to
    some target root with the same ordered profile, so no arbitrary representative
    is selected. The candidate count is at most v^2, giving at most
    ``2*log2(v)`` branch-multiplicity charge instead of factorial cell matching.

    Only proved-empty transporters are discarded. The surviving complete coset
    family is intersected with the original full string and reconstructed by the
    existing exact branch-union SI routine. This exactness boundary assumes, as in
    the surrounding H5/H6 pipeline, that the supplied UPCC relations are the
    deterministic equivariant relations derived from the corresponding strings.
    Resource caps fail closed.

    This closes an explicit UPCC child but does not by itself certify the complete
    corrected Split-or-Johnson recurrence for every coherent configuration.
    """
    if max_partition_pair_branches < 1 or max_partition_states < 1:
        raise ValueError("partition branch/state caps must be positive")
    n = int(group.degree)
    v = int(vertex_count)
    source = tuple(source_values)
    target = tuple(target_values)
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate the ambient degree")

    sf = certify_upcc_subconstituent_split_family(
        v,
        arity,
        source_relation,
        root_n=root_n,
        alpha=alpha,
        max_tuple_states=max_tuple_states,
        max_rounds=max_twl_rounds,
        max_work_units=max_twl_work_units,
    )
    tf = certify_upcc_subconstituent_split_family(
        v,
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
            sf, tf, None, None, 0, False, False, 0.0,
            "exact full-string UPCC recursion requires complete alpha-shrinking source and target subconstituent families",
        )

    pairs = []
    for sroot, scells in zip(sf.roots, sf.partitions):
        sprofile = _ordered_cell_size_profile(scells)
        for troot, tcells in zip(tf.roots, tf.partitions):
            if sprofile == _ordered_cell_size_profile(tcells):
                pairs.append((sroot, scells, troot, tcells))
                if len(pairs) > max_partition_pair_branches:
                    return UPCCSubconstituentFullStringSI(
                        "undetermined_upcc_partition_pair_limit",
                        sf, tf, None, None, len(pairs), False, False, 0.0,
                        "the complete root-pair cover exceeds the explicit materialization cap",
                    )

    pair_count = len(pairs)
    if pair_count > v * v:
        raise AssertionError("UPCC root-pair cover unexpectedly exceeds v^2")
    if pair_count == 0:
        plan = DesignTupleTransportPlan(
            "exact_empty_upcc_partition_shape_invariant",
            n, v, 1, 0, 0, (), base_bound,
            True, True,
            "no source/target roots have the same canonical ordered subconstituent cell-size profile",
        )
        return UPCCSubconstituentFullStringSI(
            "exact_empty_upcc_partition_shape_invariant",
            sf, tf, plan, None, 0, True, True, base_bound,
            "canonical ordered subconstituent partition invariants prove the relation-constrained branch family empty",
        )

    kept = []
    action_steps = 0
    max_orbit_states = 0
    for materialized, (sroot, scells, troot, tcells) in enumerate(pairs, start=1):
        transport = _signed_partition_transporter(
            group,
            lifted_generators,
            scells,
            tcells,
            max_states=max_partition_states,
        )
        action_steps += int(transport.action_steps)
        max_orbit_states = max(max_orbit_states, int(transport.orbit_states))
        if transport.status == "undetermined_signed_ground_partition_orbit_limit":
            return UPCCSubconstituentFullStringSI(
                transport.status, sf, tf, None, None, materialized,
                False, False, 0.0,
                "an exact canonical root-partition branch exceeded the orbit-state cap; the complete cover is withheld",
            )
        if transport.status == "no_signed_ground_partition_transporter":
            continue
        if transport.status != "signed_ground_partition_transporter_coset" or transport.transporter is None:
            return UPCCSubconstituentFullStringSI(
                "undetermined_upcc_partition_transport", sf, tf, None, None,
                materialized, False, False, 0.0,
                "a complete UPCC root-partition branch returned an unrecognized transporter status",
            )
        kept.append(
            DesignTupleBranch(
                (int(sroot),),
                (int(troot),),
                transport.status,
                RightCoset(transport.stabilizer, transport.transporter),
                int(transport.orbit_states),
                int(transport.action_steps),
                "exact ambient transporter for one canonical UPCC root/subconstituent partition pair",
            )
        )

    local_bound = (
        base_bound
        + 2.0 * log2(max(2, v))
        + log2(max(1, action_steps))
        + 4.0 * log2(max(2, n + v + max_orbit_states))
        + 32.0
    )
    if not kept:
        plan = DesignTupleTransportPlan(
            "exact_empty_design_tuple_transport_cover",
            n, v, 1, pair_count, 0, (), local_bound,
            True, True,
            "every canonical root-partition pair in the complete UPCC cover has exact empty ambient transporter",
        )
        return UPCCSubconstituentFullStringSI(
            "exact_empty_upcc_subconstituent_transport",
            sf, tf, plan, None, pair_count, True, True, local_bound, plan.reason,
        )

    plan = DesignTupleTransportPlan(
        "certified_complete_design_tuple_transport_cover",
        n, v, 1, pair_count, len(kept), tuple(kept), local_bound,
        False, True,
        "all canonical source/target root partition pairs were covered and only proved-empty exact ambient transporters were removed",
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
            sf, tf, plan, full, pair_count, False, False, 0.0, full.reason,
        )
    return UPCCSubconstituentFullStringSI(
        "exact_empty_upcc_subconstituent_full_string" if full.coset is None else "exact_upcc_subconstituent_full_string_coset",
        sf, tf, plan, full, pair_count, True, True,
        full.explicit_union_log2_cost_bound,
        "complete canonical UPCC root-partition cover, exact ambient transport, and exact full-string union reconstruction completed",
    )
