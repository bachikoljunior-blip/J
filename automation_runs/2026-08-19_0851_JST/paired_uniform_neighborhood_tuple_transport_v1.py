from __future__ import annotations

from dataclasses import dataclass
from math import log2

from coset_stabilizer_primitives import RightCoset
from paired_uniform_neighborhood_design_branches_v1 import (
    PairedUniformNeighborhoodDesignBranches,
)
from signed_johnson_ground_profile_partition_si_v1 import _signed_partition_transporter


@dataclass(frozen=True)
class PairedUniformNeighborhoodTransportBranch:
    source_individualized: tuple[int, ...]
    target_individualized: tuple[int, ...]
    coset: RightCoset
    transporter_parity: bool
    orbit_states: int
    action_steps: int


@dataclass(frozen=True)
class PairedUniformNeighborhoodTupleTransport:
    status: str
    original_degree: int
    right_size: int
    individualization_length: int | None
    input_branch_count: int
    surviving_branch_count: int
    branches: tuple[PairedUniformNeighborhoodTransportBranch, ...]
    local_log2_cost_bound: float
    exact_empty: bool
    complete: bool
    exact: bool
    reason: str


def _tuple_partition(v: int, ordered_tuple: tuple[int, ...]):
    if len(set(ordered_tuple)) != len(ordered_tuple):
        raise ValueError("individualized tuple must be injective")
    if any(x < 0 or x >= v for x in ordered_tuple):
        raise ValueError("individualized point outside right ground")
    used = set(ordered_tuple)
    cells = tuple((x,) for x in ordered_tuple)
    rest = tuple(x for x in range(v) if x not in used)
    if rest:
        cells += (rest,)
    return cells


def transport_paired_uniform_neighborhood_design_branches(
    group,
    lifted_generators,
    plan: PairedUniformNeighborhoodDesignBranches,
    *,
    max_partition_states: int = 200000,
) -> PairedUniformNeighborhoodTupleTransport:
    """Lift every rev209 V2 tuple-pair branch through an exact ambient action.

    The caller supplies the original-domain group together with the paired action of
    each original generator on the right ground V2 (optionally carrying a complement
    parity bit, matching the existing signed-ground transporter interface). Each
    ordered individualization tuple is converted to an ordered singleton/remainder
    partition. The existing partition-orbit Schreier routine then returns the exact
    original-domain coset mapping that source tuple to the target tuple.

    Only proved-empty ambient transporters are discarded. Any resource cap or
    unrecognized status withholds the entire cover, so a successful result remains
    complete. The output is still a family of candidate cosets: exact full-string
    intersection and union reconstruction are separate children.
    """
    if max_partition_states < 1:
        raise ValueError("max_partition_states must be positive")
    n = int(group.degree)
    v = int(plan.right_size)

    if plan.exact_empty:
        return PairedUniformNeighborhoodTupleTransport(
            "exact_empty_paired_uniform_neighborhood_plan",
            n, v, plan.minimal_individualization_length,
            plan.branch_count, 0, (), plan.local_log2_branch_bound,
            True, True, True,
            "the upstream paired right-relation branch cover is already exact empty",
        )
    if (
        not plan.complete
        or not plan.exact
        or plan.status != "certified_paired_uniform_neighborhood_design_branch_cover"
    ):
        return PairedUniformNeighborhoodTupleTransport(
            "undetermined_incomplete_paired_uniform_neighborhood_plan",
            n, v, plan.minimal_individualization_length,
            plan.branch_count, 0, (), 0.0,
            False, False, False,
            "ambient tuple transport requires the complete exact rev209 Design branch cover",
        )

    kept = []
    total_steps = 0
    max_orbit_states = 0
    for branch in plan.branches:
        source_cells = _tuple_partition(v, branch.source_individualized)
        target_cells = _tuple_partition(v, branch.target_individualized)
        transport = _signed_partition_transporter(
            group,
            lifted_generators,
            source_cells,
            target_cells,
            max_states=max_partition_states,
        )
        total_steps += int(transport.action_steps)
        max_orbit_states = max(max_orbit_states, int(transport.orbit_states))
        if transport.status == "undetermined_signed_ground_partition_orbit_limit":
            return PairedUniformNeighborhoodTupleTransport(
                transport.status,
                n, v, plan.minimal_individualization_length,
                plan.branch_count, 0, (), 0.0,
                False, False, False,
                "at least one exact tuple-pair transporter orbit exceeded max_partition_states; no partial ambient cover is exposed",
            )
        if transport.status in {
            "no_signed_ground_partition_transporter",
            "partition_shape_mismatch",
        }:
            continue
        if transport.status != "signed_ground_partition_transporter_coset" or transport.transporter is None:
            return PairedUniformNeighborhoodTupleTransport(
                "undetermined_paired_uniform_neighborhood_tuple_transport",
                n, v, plan.minimal_individualization_length,
                plan.branch_count, 0, (), 0.0,
                False, False, False,
                "a rev209 branch returned an unrecognized ambient partition-transporter status",
            )
        kept.append(PairedUniformNeighborhoodTransportBranch(
            tuple(branch.source_individualized),
            tuple(branch.target_individualized),
            RightCoset(transport.stabilizer, transport.transporter),
            bool(transport.transporter_parity),
            int(transport.orbit_states),
            int(transport.action_steps),
        ))

    local_bound = (
        plan.local_log2_branch_bound
        + log2(max(1, total_steps))
        + 4.0 * log2(max(2, n + v + max_orbit_states))
        + 32.0
    )
    if not kept:
        return PairedUniformNeighborhoodTupleTransport(
            "exact_empty_paired_uniform_neighborhood_tuple_transport",
            n, v, plan.minimal_individualization_length,
            plan.branch_count, 0, (), local_bound,
            True, True, True,
            "every tuple pair in the complete exact rev209 cover has a proved-empty ambient transporter",
        )

    return PairedUniformNeighborhoodTupleTransport(
        "certified_complete_paired_uniform_neighborhood_tuple_transport",
        n, v, plan.minimal_individualization_length,
        plan.branch_count, len(kept), tuple(kept), local_bound,
        False, True, True,
        "every surviving rev209 tuple pair carries its exact original-domain ambient right coset; only proved-empty transporter branches were removed",
    )
