from __future__ import annotations

from dataclasses import dataclass

from paired_uniform_neighborhood_design_branches_v1 import (
    PairedUniformNeighborhoodDesignBranches,
    pair_uniform_neighborhood_design_branches,
)
from paired_uniform_neighborhood_provenance_v1 import PairedUniformNeighborhoodProvenance
from paired_uniform_neighborhood_tuple_transport_v1 import (
    PairedUniformNeighborhoodTupleTransport,
    transport_paired_uniform_neighborhood_design_branches,
)


@dataclass(frozen=True)
class PairedUniformNeighborhoodPipeline:
    status: str
    provenance_status: str
    design_plan: PairedUniformNeighborhoodDesignBranches | None
    tuple_transport: PairedUniformNeighborhoodTupleTransport | None
    relation_branch_count: int
    ambient_survivor_count: int
    exact_empty: bool
    complete_cover: bool
    exact: bool
    parent_provenance_required: bool
    reason: str


def build_paired_uniform_neighborhood_candidate_cover(
    ambient_group,
    lifted_generators,
    provenance: PairedUniformNeighborhoodProvenance,
    *,
    root_n: int | None = None,
    max_subsets: int = 200000,
    max_johnson_nodes: int = 500000,
    max_states: int = 200000,
    max_tuple_states: int = 250000,
    max_rounds: int | None = None,
    max_family_work_units: int = 500000000,
    max_branch_work_units: int = 100000000,
    max_branch_pairs: int = 200000,
    max_partition_states: int = 200000,
) -> PairedUniformNeighborhoodPipeline:
    """Compose rev212 provenance -> rev209 pairing -> rev210 ambient transport.

    This layer removes an unsafe manual wiring point: coordinates/colors are read
    only from an exact rev212 certificate, so a caller cannot accidentally pair an
    unrelated V2 relation while claiming rev204 provenance.  For the certified
    nonconstant containment-count case it materializes the complete exact k-WL
    witness-pair cover and lifts every surviving tuple pair through the supplied
    original-domain action on V2.

    The result is a complete *candidate* cover for every ambient isomorphism that
    preserves the certified bipartite state.  False-positive branches may remain and
    must be intersected with the parent state.  Because rev212 proves only
    bipartite->V2 equivariance, ``parent_provenance_required`` stays true: a larger
    parent reduction must still prove parent->bipartite equivariance before using
    this cover as complete for that parent's full string.
    """
    if root_n is None:
        root_n = int(ambient_group.degree)
    root_n = int(root_n)

    if provenance.exact_empty:
        return PairedUniformNeighborhoodPipeline(
            "exact_empty_paired_uniform_neighborhood_provenance",
            provenance.status,
            None,
            None,
            0,
            0,
            True,
            True,
            bool(provenance.exact),
            True,
            "the exact paired bipartite provenance stage already proves the source/target subproblems incompatible",
        )
    if not provenance.exact:
        return PairedUniformNeighborhoodPipeline(
            "undetermined_nonexact_paired_uniform_neighborhood_provenance",
            provenance.status,
            None,
            None,
            0,
            0,
            False,
            False,
            False,
            True,
            "the rev212 provenance stage is not exact, so no downstream candidate cover is exposed",
        )
    if provenance.paired_johnson_certified:
        return PairedUniformNeighborhoodPipeline(
            "paired_uniform_neighborhood_johnson_alternative",
            provenance.status,
            None,
            None,
            0,
            0,
            False,
            True,
            True,
            True,
            "rev212 certified the complete-uniform Johnson alternative; the containment-count Design branch is intentionally bypassed",
        )
    if provenance.status == "paired_degree_alpha_partition_preempts_uniform_neighborhood":
        return PairedUniformNeighborhoodPipeline(
            "paired_degree_partition_alternative",
            provenance.status,
            None,
            None,
            0,
            0,
            False,
            True,
            True,
            True,
            "the exact bipartite degree partition already gives structural progress on both sides, so no V2 Design candidate cover is needed",
        )
    if not provenance.derived_relation_certified:
        return PairedUniformNeighborhoodPipeline(
            "undetermined_uniform_neighborhood_relation_provenance_residual",
            provenance.status,
            None,
            None,
            0,
            0,
            False,
            False,
            False,
            True,
            "rev212 did not certify a nonconstant paired containment-count V2 relation; constant/design-bound or stage residual remains open",
        )
    if (
        provenance.test_arity is None
        or not provenance.source_coordinates
        or not provenance.target_coordinates
        or not provenance.source_colors
        or not provenance.target_colors
    ):
        raise AssertionError("certified derived V2 provenance is missing its exact relation payload")

    plan = pair_uniform_neighborhood_design_branches(
        provenance.right_size,
        provenance.test_arity,
        provenance.source_coordinates,
        provenance.source_colors,
        provenance.target_coordinates,
        provenance.target_colors,
        root_n=root_n,
        alpha=provenance.alpha,
        max_subsets=max_subsets,
        max_johnson_nodes=max_johnson_nodes,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_rounds=max_rounds,
        max_family_work_units=max_family_work_units,
        max_branch_work_units=max_branch_work_units,
        max_branch_pairs=max_branch_pairs,
    )
    if plan.exact_empty:
        return PairedUniformNeighborhoodPipeline(
            "exact_empty_paired_uniform_neighborhood_design_plan",
            provenance.status,
            plan,
            None,
            plan.branch_count,
            0,
            True,
            True,
            bool(plan.exact),
            True,
            "the exact rev212 relation payload reaches an exact-empty paired k-WL Design invariant before ambient transport",
        )
    if not plan.complete or not plan.exact:
        return PairedUniformNeighborhoodPipeline(
            "undetermined_paired_uniform_neighborhood_design_plan",
            provenance.status,
            plan,
            None,
            plan.branch_count,
            0,
            False,
            False,
            False,
            True,
            "the mechanically provenance-bound V2 relation did not produce a complete exact rev209 branch plan",
        )
    if plan.status != "certified_paired_uniform_neighborhood_design_branch_cover":
        return PairedUniformNeighborhoodPipeline(
            "paired_uniform_neighborhood_non_design_alternative",
            provenance.status,
            plan,
            None,
            plan.branch_count,
            0,
            False,
            True,
            True,
            True,
            "the exact V2 relation was classified by a cheaper rev205 alternative rather than the exact Design witness branch family",
        )

    transport = transport_paired_uniform_neighborhood_design_branches(
        ambient_group,
        lifted_generators,
        plan,
        max_partition_states=max_partition_states,
    )
    if transport.exact_empty:
        return PairedUniformNeighborhoodPipeline(
            "exact_empty_paired_uniform_neighborhood_ambient_cover",
            provenance.status,
            plan,
            transport,
            plan.branch_count,
            0,
            True,
            True,
            bool(transport.exact),
            True,
            "all branches in the exact provenance-bound V2 Design cover have proved-empty transporters in the supplied ambient action",
        )
    if not transport.complete or not transport.exact:
        return PairedUniformNeighborhoodPipeline(
            "undetermined_paired_uniform_neighborhood_ambient_cover",
            provenance.status,
            plan,
            transport,
            plan.branch_count,
            transport.surviving_branch_count,
            False,
            False,
            False,
            True,
            "the exact provenance-bound Design cover could not be completely lifted through the supplied ambient V2 action",
        )

    return PairedUniformNeighborhoodPipeline(
        "certified_paired_uniform_neighborhood_candidate_cover",
        provenance.status,
        plan,
        transport,
        plan.branch_count,
        transport.surviving_branch_count,
        False,
        True,
        True,
        True,
        "rev212's exact derived relation is mechanically wired through the complete rev209 invariant-compatible tuple cover and rev210 exact ambient transport; parent->bipartite provenance plus parent-state intersection remain explicit children",
    )
