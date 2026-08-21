from __future__ import annotations

from dataclasses import dataclass
from math import log2

from colored_subset_design_branch_plan_v1 import DesignBranchPlan
from coset_stabilizer_primitives import RightCoset
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

    Each ordered witness tuple is represented as an ordered partition consisting
    of its singleton positions followed by the unindividualized remainder. The
    existing signed-ground partition Schreier routine therefore returns the exact
    original-domain right coset mapping one source tuple to one target tuple,
    including the Johnson complement bit when present.

    Because `branch_plan` is a complete source/target witness cover, discarding
    only branches with a proved-empty ambient transporter preserves completeness.
    Any orbit/resource-limit result aborts fail-closed rather than exposing a
    partial cover. The returned object is still a *family* of candidate cosets;
    full string recursion and exact coset-union reconstruction are later children.
    """
    if max_partition_states < 1:
        raise ValueError("max_partition_states must be positive")
    n = int(group.degree)
    v = int(branch_plan.vertex_count)

    if branch_plan.exact_empty:
        return DesignTupleTransportPlan(
            "exact_empty_design_branch_plan",
            n, v, branch_plan.individualization_length,
            branch_plan.branch_count, 0, (),
            branch_plan.local_log2_cost_bound + 8.0,
            True, True,
            "the upstream exact Design-Lemma branch plan is already empty",
        )
    if not branch_plan.complete or branch_plan.status != "certified_complete_design_branch_plan":
        return DesignTupleTransportPlan(
            "undetermined_incomplete_design_branch_plan",
            n, v, branch_plan.individualization_length,
            branch_plan.branch_count, 0, (),
            0.0, False, False,
            "tuple transport requires an exact complete upstream Design-Lemma branch cover",
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
            branch_plan.branch_count, total_orbit_states, total_steps,
        )

    return DesignTupleTransportPlan(
        "certified_complete_design_tuple_transport_cover",
        n, v, branch_plan.individualization_length,
        branch_plan.branch_count, len(kept), tuple(kept), local_bound,
        False, True,
        "every surviving tuple-pair branch carries its exact original-domain ambient right coset; only proved-empty transporter branches were removed",
        branch_plan.branch_count, total_orbit_states, total_steps,
    )
