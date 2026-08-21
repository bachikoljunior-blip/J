from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil, log2


@dataclass(frozen=True)
class DesignBranchMaterializationResourceEnvelope:
    status: str
    original_root_degree: int
    vertex_count: int
    individualization_length: int
    source_witness_count: int
    target_witness_count: int
    branch_count: int
    witness_snapshot_work_upper_bound: int
    work_per_branch_upper_bound: int
    work_upper_bound: int
    max_work: int
    root_lift_certified: bool
    admitted: bool
    materialized_branch_count: int
    charged_work_upper_bound: int
    complete: bool
    reason: str


def design_branch_materialization_resource_envelope(
    original_root_degree: int,
    vertex_count: int,
    individualization_length: int,
    source_witness_count: int,
    target_witness_count: int,
    max_work: int,
) -> DesignBranchMaterializationResourceEnvelope:
    """Reserve the complete Cartesian witness cover before touching a tuple.

    The theorem-side bound uses arbitrary-precision integers.  It charges a
    canonical snapshot of every source/target witness tuple and construction of
    every ordered pair, including conservative copies of both length-``ell``
    tuples.  Runtime ``max_branch_pairs`` is deliberately not an input.
    """
    root, v, ell, source, target, cap = map(int, (
        original_root_degree, vertex_count, individualization_length,
        source_witness_count, target_witness_count, max_work,
    ))
    if min(root, v, cap) <= 0 or min(ell, source, target) < 0:
        raise ValueError("invalid Design branch materialization parameters")
    arity_cap = max(1, ceil(log2(max(2, root))))
    root_lift = v <= root and ell <= arity_cap
    branches = source * target
    snapshot = (source + target) * (ell + 1)
    per_branch = 2 * ell + 1
    total = snapshot + branches * per_branch
    admitted = root_lift and total <= cap
    if not root_lift:
        status = "design_branch_materialization_original_root_lift_unavailable"
        reason = "the Design ground or individualization length exceeds the original-root lift gate"
    elif total > cap:
        status = "design_branch_materialization_work_cap_exceeded"
        reason = "the complete Cartesian witness cover exceeds the finite budget before any branch tuple is materialized"
    else:
        status = "certified_design_branch_materialization_work_bound"
        reason = "all witness snapshots and Cartesian branch objects fit the finite original-root budget"
    return DesignBranchMaterializationResourceEnvelope(
        status, root, v, ell, source, target, branches, snapshot, per_branch,
        total, cap, root_lift, admitted, 0, 0, False, reason,
    )


def record_design_branch_materialization(
    envelope: DesignBranchMaterializationResourceEnvelope,
    *,
    materialized_branch_count: int,
    complete: bool,
) -> DesignBranchMaterializationResourceEnvelope:
    if not envelope.admitted:
        raise ValueError("cannot record materialization for a rejected envelope")
    count = int(materialized_branch_count)
    if count < 0 or count > envelope.branch_count:
        raise ValueError("materialized branch count exceeds the reserved Cartesian cover")
    if complete and count != envelope.branch_count:
        raise ValueError("a complete materialization must contain the entire Cartesian cover")
    charged = envelope.witness_snapshot_work_upper_bound + count * envelope.work_per_branch_upper_bound
    if charged > envelope.work_upper_bound:
        raise ValueError("materialization charge exceeds the reserved work")
    return replace(
        envelope,
        materialized_branch_count=count,
        charged_work_upper_bound=charged,
        complete=bool(complete),
    )


__all__ = [
    "DesignBranchMaterializationResourceEnvelope",
    "design_branch_materialization_resource_envelope",
    "record_design_branch_materialization",
]
