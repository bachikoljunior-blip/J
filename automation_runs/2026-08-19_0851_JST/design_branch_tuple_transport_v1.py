from __future__ import annotations

from dataclasses import dataclass
from math import log2

from colored_subset_design_branch_plan_v1 import DesignBranchPlan
from coset_stabilizer_primitives import RightCoset
from design_original_root_ledger_v1 import DesignOriginalRootLedger
from signed_johnson_ground_profile_partition_si_v1 import _signed_partition_transporter


@dataclass(frozen=True)
class DesignTupleBranch:
    source_tuple: tuple[int, ...]
    target_tuple: tuple[int, ...]
    status: str
    coset: RightCoset | None
    orbit_states: int
    action_steps: int
    reason: str


@dataclass(frozen=True)
class DesignTupleTransportPlan:
    status: str
    original_degree: int
    ground_size: int
    individualization_length: int | None
    input_branch_count: int
    surviving_branch_count: int
    branches: tuple[DesignTupleBranch, ...]
    local_log2_cost_bound: float
    exact_empty: bool
    complete: bool
    reason: str
    executed_branch_count: int = 0
    total_orbit_states: int = 0
    total_action_steps: int = 0
    original_root_ledger: DesignOriginalRootLedger | None = None


def _tuple_partition(v: int, ordered_tuple: tuple[int, ...]):
    used = set(ordered_tuple)
    rest = tuple(x for x in range(v) if x not in used)
    cells = tuple((x,) for x in ordered_tuple)
    if rest:
        cells += (rest,)
    return cells


def transport_complete_design_tuple_branches(
    group,
    lifted_generators,
    branch_plan: DesignBranchPlan,
    *,
    max_partition_states: int = 200000,
) -> DesignTupleTransportPlan:
    """Intersect every Design-Lemma tuple branch with an exact ambient action.

    If the upstream branch plan carries a rev242 original-root ledger, this phase
    may not enlarge the reserved tuple-orbit cap. The ledger is propagated to the
    full-string child so later phases remain bound to the same pre-WL reservation.
    """
    if max_partition_states < 1:
        raise ValueError("max_partition_states must be positive")
    n = int(group.degree)
    v = int(branch_plan.vertex_count)
    ledger = branch_plan.original_root_ledger
    if ledger is not None:
        if not ledger.admitted:
            return DesignTupleTransportPlan(
                ledger.status, n, v, branch_plan.individualization_length,
                branch_plan.branch_count, 0, (), 0.0, False, False,
                "tuple transport cannot start from a rejected original-root ledger",
                original_root_ledger=ledger,
            )
        if int(max_partition_states) > ledger.partition_state_cap:
            return DesignTupleTransportPlan(
                "design_tuple_transport_exceeds_original_root_ledger", n, v,
                branch_plan.individualization_length, branch_plan.branch_count, 0,
                (), 0.0, False, False,
                "tuple transport requested a state cap larger than the amount reserved before the first t-WL execution",
                original_root_ledger=ledger,
            )

    if branch_plan.exact_empty:
        return DesignTupleTransportPlan(
            "exact_empty_design_branch_plan",
            n, v, branch_plan.individualization_length,
            branch_plan.branch_count, 0, (),
            branch_plan.local_log2_cost_bound + 8.0,
            True, True,
            "the upstream exact Design-Lemma branch plan is already empty",
            original_root_ledger=ledger,
        )
    if not branch_plan.complete or branch_plan.status != "certified_complete_design_branch_plan":
        return DesignTupleTransportPlan(
            "undetermined_incomplete_design_branch_plan",
            n, v, branch_plan.individualization_length,
            branch_plan.branch_count, 0, (),
            0.0, False, False,
            "tuple transport requires an exact complete upstream Design-Lemma branch cover",
            original_root_ledger=ledger,
        )

    kept = []
    total_steps = 0
    total_orbit_states = 0
    max_orbit_states = 0
    for source_tuple, target_tuple in branch_plan.branches:
        source_cells = _tuple_partition(v, tuple(source_tuple))
        target_cells = _tuple_partition(v, tuple(target_tuple))
        transport = _signed_partition_transporter(
            group,
            lifted_generators,
            source_cells,
            target_cells,
            max_states=max_partition_states,
        )
        total_steps += int(transport.action_steps)
        total_orbit_states += int(transport.orbit_states)
        max_orbit_states = max(max_orbit_states, int(transport.orbit_states))
        if transport.status == "undetermined_signed_ground_partition_orbit_limit":
            return DesignTupleTransportPlan(
                transport.status,
                n, v, branch_plan.individualization_length,
                branch_plan.branch_count, 0, (),
                0.0, False, False,
                "at least one tuple-pair transporter orbit exceeded the explicit state cap; the complete cover is withheld",
                original_root_ledger=ledger,
            )
        if transport.status == "no_signed_ground_partition_transporter":
            continue
        if transport.status != "signed_ground_partition_transporter_coset" or transport.transporter is None:
            return DesignTupleTransportPlan(
                "undetermined_design_tuple_transport",
                n, v, branch_plan.individualization_length,
                branch_plan.branch_count, 0, (),
                0.0, False, False,
                "an upstream-complete tuple branch returned an unrecognized transporter status",
                original_root_ledger=ledger,
            )
        kept.append(
            DesignTupleBranch(
                tuple(source_tuple),
                tuple(target_tuple),
                transport.status,
                RightCoset(transport.stabilizer, transport.transporter),
                int(transport.orbit_states),
                int(transport.action_steps),
                transport.reason,
            )
        )

    local_bound = (
        branch_plan.local_log2_cost_bound
        + log2(max(1, total_steps))
        + 4.0 * log2(max(2, n + v + max_orbit_states))
        + 32.0
    )
    if not kept:
        return DesignTupleTransportPlan(
            "exact_empty_design_tuple_transport_cover",
            n, v, branch_plan.individualization_length,
            branch_plan.branch_count, 0, (), local_bound,
            True, True,
            "every tuple pair in the complete canonical Design-Lemma witness cover has an exact empty ambient transporter",
            branch_plan.branch_count, total_orbit_states, total_steps, ledger,
        )

    return DesignTupleTransportPlan(
        "certified_complete_design_tuple_transport_cover",
        n, v, branch_plan.individualization_length,
        branch_plan.branch_count, len(kept), tuple(kept), local_bound,
        False, True,
        "every surviving tuple-pair branch carries its exact original-domain ambient right coset; only proved-empty transporter branches were removed",
        branch_plan.branch_count, total_orbit_states, total_steps, ledger,
    )
