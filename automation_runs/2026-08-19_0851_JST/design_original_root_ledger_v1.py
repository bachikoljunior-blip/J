from __future__ import annotations

from dataclasses import dataclass
from math import comb

from local_certificate_preimage_resource_v1 import _sat_add, _sat_mul


@dataclass(frozen=True)
class DesignOriginalRootLedger:
    status: str
    original_root_degree: int
    vertex_count: int
    arity: int
    auxiliary_vertices: int
    branch_pair_cap: int
    wl_work_upper_bound: int
    materialization_work_upper_bound: int
    tuple_transport_work_upper_bound: int
    child_si_work_upper_bound: int
    union_work_upper_bound: int
    work_upper_bound: int
    max_work: int
    root_lift_certified: bool
    admitted: bool
    reason: str


def design_original_root_ledger(
    original_root_degree: int,
    vertex_count: int,
    arity: int,
    *,
    max_states: int,
    max_wl_vertices: int,
    max_wl_rounds: int,
    max_branch_pairs: int,
    max_partition_states: int,
    max_design_full_string_child_work: int,
    max_design_union_reconstruction_work: int,
    max_work: int,
) -> DesignOriginalRootLedger:
    """Reserve the whole Design continuation before the first incidence-WL step.

    This is intentionally a caller-cap ledger rather than a post-hoc accounting
    object.  It reserves both correlated witness searches, worst-case branch
    materialization, every tuple-transporter orbit, the complete full-string child
    budget, and final union reconstruction under one original-root cap.  Saturation
    uses only ``max_work + 1`` so a rejected ledger fails before any t-WL execution.
    """
    root = int(original_root_degree)
    v = int(vertex_count)
    t = int(arity)
    states = int(max_states)
    wl_vertices_cap = int(max_wl_vertices)
    wl_rounds = int(max_wl_rounds)
    branch_cap = int(max_branch_pairs)
    partition_states = int(max_partition_states)
    child_cap = int(max_design_full_string_child_work)
    union_cap = int(max_design_union_reconstruction_work)
    cap = int(max_work)
    if min(root, v, t, states, wl_vertices_cap, wl_rounds, branch_cap,
           partition_states, child_cap, union_cap, cap) <= 0:
        raise ValueError("invalid Design original-root ledger parameters")

    auxiliary = v + comb(v, t)
    root_lift = v <= root and auxiliary <= wl_vertices_cap
    stop = cap + 1

    # One exact incidence 2-WL state has O(m^3) pair-through-vertex refinement
    # work per round plus O(m^2) initialization.  Charge source and target.
    m2 = _sat_mul(auxiliary, auxiliary, stop)
    m3 = _sat_mul(m2, auxiliary, stop)
    per_state = _sat_add(m2, _sat_mul(wl_rounds, m3, stop), stop)
    wl_work = _sat_mul(2 * states, per_state, stop)

    # Any accepted witness level has ell < t; use t as a conservative tuple-copy
    # width before the exact witness cardinalities are known.
    materialization_per_branch = 2 * t + 1
    materialization = _sat_add(
        _sat_mul(2 * states, t + 1, stop),
        _sat_mul(branch_cap, materialization_per_branch, stop),
        stop,
    )

    # _signed_partition_transporter explores at most max_partition_states states
    # per branch; charge root-sized permutation scans per state.
    tuple_per_state = _sat_mul(16 * root, root, stop)
    tuple_transport = _sat_mul(
        branch_cap,
        _sat_mul(partition_states, tuple_per_state, stop),
        stop,
    )

    total = 0
    for part in (wl_work, materialization, tuple_transport, child_cap, union_cap):
        total = _sat_add(total, part, stop)
    admitted = root_lift and total <= cap
    if not root_lift:
        status = "design_original_root_ledger_lift_unavailable"
        reason = "the Design ground or explicit incidence graph exceeds the original-root/implementation lift gate before t-WL"
    elif total > cap:
        status = "design_original_root_ledger_work_cap_exceeded"
        reason = "the correlated t-WL, branch materialization, tuple transport, child SI, and union reservations exceed the single finite original-root budget before the first t-WL execution"
    else:
        status = "certified_design_original_root_ledger"
        reason = "one finite original-root ledger reserves correlated t-WL, branch materialization, tuple transport, child SI, and union reconstruction before the first t-WL execution"
    return DesignOriginalRootLedger(
        status, root, v, t, auxiliary, branch_cap, wl_work, materialization,
        tuple_transport, child_cap, union_cap, total, cap, root_lift, admitted, reason,
    )


__all__ = ["DesignOriginalRootLedger", "design_original_root_ledger"]
