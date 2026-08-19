from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from paired_uniform_neighborhood_full_string_union_v1 import (
    PairedUniformNeighborhoodFullStringSI,
    solve_paired_uniform_neighborhood_full_string,
)
from paired_uniform_neighborhood_pipeline_v1 import (
    PairedUniformNeighborhoodPipeline,
    build_paired_uniform_neighborhood_candidate_cover,
)
from paired_uniform_neighborhood_provenance_v1 import (
    PairedUniformNeighborhoodProvenance,
    certify_paired_uniform_neighborhood_provenance,
)


@dataclass(frozen=True)
class BipartiteUniformNeighborhoodStringIso:
    status: str
    provenance: PairedUniformNeighborhoodProvenance | None
    pipeline: PairedUniformNeighborhoodPipeline | None
    full_string: PairedUniformNeighborhoodFullStringSI | None
    ambient_product_action_certified: bool
    exact_empty: bool
    exact: bool
    reason: str


def _validate_product_action(ambient_group, lifted_generators, n1: int, n2: int):
    """Prove each ambient generator is the paired left/right product action.

    Edge-position coordinates use ``a*n2+b``.  A supplied right action q is valid
    for ambient generator g only if there is a permutation p on the left part with
    g(a,b)=(p(a),q(b)) for every edge position.  Checking generators suffices for
    the generated ambient subgroup and simultaneously proves that the lifted V2
    generator list is the correct homomorphic right-part image used by rev210.
    """
    generators = tuple(ambient_group.original_generators)
    lifted = tuple(lifted_generators)
    if len(generators) != len(lifted):
        return False, "ambient and lifted generator lists have different lengths"
    if ambient_group.degree != n1 * n2:
        return False, "ambient group degree is not the complete bipartite edge-position degree"

    for g, lifted_entry in zip(generators, lifted):
        if not isinstance(lifted_entry, tuple) or len(lifted_entry) != 2:
            return False, "each lifted generator must be a (right_permutation, parity) pair"
        q, parity = lifted_entry
        q = tuple(q)
        if parity:
            return False, "uniform-neighborhood V2 provenance uses an ordinary right-part action, not signed complement parity"
        if len(q) != n2 or set(q) != set(range(n2)):
            return False, "lifted right action is not a permutation of V2"
        g = tuple(g)
        if len(g) != n1 * n2 or set(g) != set(range(n1 * n2)):
            return False, "ambient generator is not a permutation of the edge-position domain"

        left_image = []
        for a in range(n1):
            first = g[a * n2] // n2
            if not 0 <= first < n1:
                return False, "ambient generator left image escaped the declared left part"
            for b in range(n2):
                image = g[a * n2 + b]
                if image != first * n2 + q[b]:
                    return False, "ambient generator does not factor as one left permutation times the supplied V2 action"
            left_image.append(first)
        if set(left_image) != set(range(n1)):
            return False, "ambient generator does not induce a permutation of the left part"
    return True, "every ambient generator exactly factors through the supplied right-part action"


def _incidence_string(n1: int, n2: int, edges: Iterable[tuple[int, int]]):
    out = [0] * (n1 * n2)
    for a, b in edges:
        a = int(a)
        b = int(b)
        if not 0 <= a < n1 or not 0 <= b < n2:
            raise ValueError("bipartite edge endpoint outside the declared part")
        out[a * n2 + b] = 1
    return tuple(out)


def solve_bipartite_incidence_via_uniform_neighborhood(
    ambient_group,
    lifted_generators,
    left_size: int,
    right_size: int,
    source_edges: Iterable[tuple[int, int]],
    target_edges: Iterable[tuple[int, int]],
    *,
    root_n: int | None = None,
    bipartite_alpha: float = 2 / 3,
    design_alpha: float = 0.9,
    max_subsets: int = 200000,
    max_johnson_nodes: int = 500000,
    max_states: int = 200000,
    max_tuple_states: int = 250000,
    max_rounds: int | None = None,
    max_family_work_units: int = 500000000,
    max_branch_work_units: int = 100000000,
    max_branch_pairs: int = 200000,
    max_partition_states: int = 200000,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 256,
    max_depth: int = 64,
) -> BipartiteUniformNeighborhoodStringIso:
    """End-to-end exact SI for the rev204 nonconstant bipartite incidence branch.

    Unlike rev211's general parent-state interface, this routine's full string *is*
    exactly the complete bipartite incidence bit string from which rev212 derives
    the V2 relation.  It therefore discharges the missing provenance implication
    mechanically rather than accepting a caller boolean.

    Exactness additionally requires the ambient group itself to be proved a subgroup
    of the left/right product action, with each original generator paired to its V2
    right action.  After that check the routine composes rev212 -> rev213 and uses
    rev211 to intersect every complete candidate branch with the actual incidence
    bit string.  The complete-uniform Johnson, degree-partition, constant-relation,
    and other theorem alternatives remain typed residuals unless a separate exact
    solver for those alternatives is supplied.
    """
    n1 = int(left_size)
    n2 = int(right_size)
    if n1 < 1 or n2 < 2:
        raise ValueError("bipartite incidence SI requires positive left_size and right_size>=2")
    source_edges = tuple(source_edges)
    target_edges = tuple(target_edges)
    if root_n is None:
        root_n = int(ambient_group.degree)
    root_n = int(root_n)
    if root_n < ambient_group.degree:
        raise ValueError("root_n must dominate the ambient edge-position degree")

    action_ok, action_reason = _validate_product_action(
        ambient_group, lifted_generators, n1, n2
    )
    if not action_ok:
        return BipartiteUniformNeighborhoodStringIso(
            "undetermined_bipartite_ambient_product_action",
            None, None, None, False, False, False, action_reason,
        )

    source_values = _incidence_string(n1, n2, source_edges)
    target_values = _incidence_string(n1, n2, target_edges)
    provenance = certify_paired_uniform_neighborhood_provenance(
        n1,
        n2,
        source_edges,
        target_edges,
        alpha=bipartite_alpha,
    )
    if provenance.exact_empty:
        return BipartiteUniformNeighborhoodStringIso(
            "exact_empty_bipartite_uniform_neighborhood_provenance",
            provenance, None, None, True, True, True,
            "a canonical exact bipartite invariant already proves the two incidence strings incompatible",
        )
    if not provenance.derived_relation_certified:
        return BipartiteUniformNeighborhoodStringIso(
            "bipartite_uniform_neighborhood_structural_alternative",
            provenance, None, None, True, False, bool(provenance.exact),
            "the exact paired bipartite state entered a degree-partition, Johnson, constant-design, or other non-containment-count alternative that this focused SI does not falsely collapse into the Design branch",
        )

    pipeline = build_paired_uniform_neighborhood_candidate_cover(
        ambient_group,
        lifted_generators,
        provenance,
        root_n=root_n,
        design_alpha=design_alpha,
        max_subsets=max_subsets,
        max_johnson_nodes=max_johnson_nodes,
        max_states=max_states,
        max_tuple_states=max_tuple_states,
        max_rounds=max_rounds,
        max_family_work_units=max_family_work_units,
        max_branch_work_units=max_branch_work_units,
        max_branch_pairs=max_branch_pairs,
        max_partition_states=max_partition_states,
    )
    if pipeline.exact_empty:
        return BipartiteUniformNeighborhoodStringIso(
            "exact_empty_bipartite_uniform_neighborhood_candidate_cover",
            provenance, pipeline, None, True, True, bool(pipeline.exact),
            pipeline.reason,
        )
    if (
        not pipeline.exact
        or not pipeline.complete_cover
        or pipeline.tuple_transport is None
        or pipeline.status != "certified_paired_uniform_neighborhood_candidate_cover"
    ):
        return BipartiteUniformNeighborhoodStringIso(
            "undetermined_bipartite_uniform_neighborhood_candidate_cover",
            provenance, pipeline, None, True, False, False,
            "the exact bipartite provenance branch did not yield a complete ambient tuple candidate cover",
        )

    full = solve_paired_uniform_neighborhood_full_string(
        ambient_group,
        pipeline.tuple_transport,
        source_values,
        target_values,
        root_n=root_n,
        # Safe here by construction: source_values/target_values are exactly the
        # bipartite incidence strings consumed by the provenance certificate.
        relation_provenance_certified=True,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_depth=max_depth,
    )
    if not full.exact:
        return BipartiteUniformNeighborhoodStringIso(
            "undetermined_bipartite_uniform_neighborhood_full_string",
            provenance, pipeline, full, True, False, False, full.reason,
        )
    return BipartiteUniformNeighborhoodStringIso(
        "exact_bipartite_uniform_neighborhood_string_isomorphism",
        provenance, pipeline, full, True, full.coset is None, True,
        "the complete bipartite incidence string, exact rev212 V2 provenance, complete rev213 ambient candidate cover, and rev211 full-string branch union are mechanically connected end to end",
    )
