from __future__ import annotations

from dataclasses import dataclass
from math import log2

from coset_stabilizer_primitives import RightCoset
from paired_uniform_neighborhood_tuple_transport_v1 import (
    PairedUniformNeighborhoodTupleTransport,
)
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


@dataclass(frozen=True)
class PairedUniformNeighborhoodFullStringSI:
    status: str
    coset: RightCoset | None
    branch_results: tuple[ProofCarryingCoset, ...]
    branches_checked: int
    nonempty_branches: int
    relation_provenance_certified: bool
    exact: bool
    complete: bool
    explicit_union_log2_cost_bound: float
    reason: str


def _maps_string(source, target, p) -> bool:
    return all(source[i] == target[p[i]] for i in range(len(source)))


def _stabilizes(values, p) -> bool:
    return all(values[i] == values[p[i]] for i in range(len(values)))


def solve_paired_uniform_neighborhood_full_string(
    ambient_group,
    transport_plan: PairedUniformNeighborhoodTupleTransport,
    source_values,
    target_values,
    *,
    root_n: int,
    relation_provenance_certified: bool = False,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 256,
    max_depth: int = 64,
) -> PairedUniformNeighborhoodFullStringSI:
    """Intersect every rev210 ambient branch with the original full string.

    The tuple-transport cover is only a complete cover for isomorphisms preserving
    the supplied V2 relation. To promote its exact union to the *full* ambient
    string-isomorphism set, callers must separately certify that the V2 relation was
    derived equivariantly from the original source/target state. This explicit
    ``relation_provenance_certified`` gate prevents a convenient auxiliary relation
    from silently deleting legitimate full-string isomorphisms.

    Once that gate and the complete rev210 transport cover hold, every surviving
    right coset is intersected exactly with the original strings through the
    proof-carrying U2 candidate solver. If all branches are exact, their union is
    reconstructed as one target-automorphism right coset by adjoining inter-branch
    representative differences. Any unresolved branch withholds the entire union.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(ambient_group.degree)
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    if not relation_provenance_certified:
        return PairedUniformNeighborhoodFullStringSI(
            "undetermined_uniform_neighborhood_relation_provenance",
            None, (), 0, 0, False, False, False, 0.0,
            "exact full-string completeness requires a separate equivariance/provenance certificate tying the V2 relation to the original state",
        )
    if transport_plan.exact_empty:
        return PairedUniformNeighborhoodFullStringSI(
            "exact_empty_paired_uniform_neighborhood_transport",
            None, (), 0, 0, True, True, True,
            transport_plan.local_log2_cost_bound + 8.0,
            "the complete relation-preserving ambient tuple-transporter cover is already exactly empty",
        )
    if (
        not transport_plan.complete
        or not transport_plan.exact
        or transport_plan.status != "certified_complete_paired_uniform_neighborhood_tuple_transport"
    ):
        return PairedUniformNeighborhoodFullStringSI(
            "undetermined_incomplete_paired_uniform_neighborhood_transport",
            None, (), 0, 0, True, False, False, 0.0,
            "full-string branch solving requires the complete exact rev210 ambient tuple-transporter cover",
        )

    solved = []
    nonempty = []
    for branch in transport_plan.branches:
        if not ambient_group.contains(branch.coset.representative):
            raise AssertionError("tuple-branch representative escaped the ambient group")
        child = candidate_coset_string_isomorphism_u2(
            branch.coset,
            source,
            target,
            root_n=root_n,
            polylog_power=polylog_power,
            max_explicit_degree=max_explicit_degree,
            group_order_poly_power=group_order_poly_power,
            max_group_order=max_group_order,
            max_depth=max_depth,
        )
        solved.append(child)
        if not child.exact:
            return PairedUniformNeighborhoodFullStringSI(
                "undetermined_paired_uniform_neighborhood_full_string_branch",
                None, tuple(solved), len(solved), len(nonempty), True,
                False, False, 0.0,
                "at least one branch in the complete relation-preserving tuple cover remains unresolved; exact union reconstruction is withheld",
            )
        if child.coset is not None:
            nonempty.append(child.coset)

    layer_bound = (
        transport_plan.local_log2_cost_bound
        + log2(max(1, len(solved)))
        + max((result.local_log2_cost_bound for result in solved), default=0.0)
        + 6.0 * log2(max(2, n))
        + 32.0
    )
    if not nonempty:
        return PairedUniformNeighborhoodFullStringSI(
            "exact_empty_paired_uniform_neighborhood_full_string_union",
            None, tuple(solved), len(solved), 0, True,
            True, True, layer_bound,
            "every branch in the complete relation-preserving tuple cover has an exact empty full-string intersection",
        )

    r0 = nonempty[0].representative
    if not ambient_group.contains(r0) or not _maps_string(source, target, r0):
        raise AssertionError("exact child representative is not an ambient full-string isomorphism")

    generators = []
    for result_coset in nonempty:
        ri = result_coset.representative
        if not ambient_group.contains(ri) or not _maps_string(source, target, ri):
            raise AssertionError("exact child representative is not an ambient full-string isomorphism")
        for g in result_coset.subgroup.original_generators:
            if not ambient_group.contains(g) or not _stabilizes(target, g):
                raise AssertionError("exact child subgroup contains a non-target-automorphism")
            generators.append(g)
        delta = compose(inverse(r0), ri)
        if not ambient_group.contains(delta) or not _stabilizes(target, delta):
            raise AssertionError("inter-branch representative difference is not a target automorphism")
        generators.append(delta)

    target_aut = schreier_stabilizer_chain(generators or (identity(n),))
    return PairedUniformNeighborhoodFullStringSI(
        "exact_paired_uniform_neighborhood_full_string_union_coset",
        RightCoset(target_aut, r0),
        tuple(solved), len(solved), len(nonempty), True,
        True, True, layer_bound,
        "all relation-preserving tuple branches were exactly intersected with the original string and, under the explicit equivariant-provenance gate, their complete union was reconstructed as the full ambient target-automorphism right coset",
    )
