from __future__ import annotations

from dataclasses import dataclass
from math import log2

from coset_stabilizer_primitives import RightCoset
from design_branch_tuple_transport_v1 import DesignTupleTransportPlan
from design_full_string_child_resource_proof_v1 import (
    DesignFullStringChildResourceProof,
    certify_design_full_string_child_resources,
)
from design_full_string_child_preflight_v1 import (
    DesignFullStringChildPreflight,
    design_full_string_child_preflight,
    record_design_full_string_child_execution,
)
from design_union_reconstruction_resource_v1 import (
    DesignUnionReconstructionResourceEnvelope,
    design_union_reconstruction_resource_envelope,
    record_design_union_reconstruction_execution,
)
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain
from proof_carrying_si_v1 import ProofCarryingCoset
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2


@dataclass(frozen=True)
class DesignTupleFullStringSI:
    status: str
    coset: RightCoset | None
    branch_results: tuple[ProofCarryingCoset, ...]
    branches_checked: int
    nonempty_branches: int
    exact: bool
    complete: bool
    explicit_union_log2_cost_bound: float
    reason: str
    child_resource_proof: DesignFullStringChildResourceProof | None = None
    child_preflight: DesignFullStringChildPreflight | None = None
    union_resource_envelope: DesignUnionReconstructionResourceEnvelope | None = None


def _maps_string(source, target, p) -> bool:
    return all(source[i] == target[p[i]] for i in range(len(source)))


def _stabilizes(values, p) -> bool:
    return all(values[i] == values[p[i]] for i in range(len(values)))


def solve_design_tuple_transport_full_string(
    ambient_group,
    transport_plan: DesignTupleTransportPlan,
    source_values,
    target_values,
    *,
    root_n: int,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 256,
    max_depth: int = 64,
    quasipoly_power: int = 5,
    quasipoly_constant: float = 64.0,
    max_design_full_string_child_work: int = 10**30,
    max_design_union_reconstruction_work: int = 10**30,
) -> DesignTupleFullStringSI:
    """Solve every exact Design-Lemma tuple branch on the original full string.

    A rev242 original-root ledger, when present on the transport plan, was admitted
    before the first correlated incidence-WL step. This phase refuses any root or
    child/union budget that exceeds that immutable reservation.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(ambient_group.degree)
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

    ledger = getattr(transport_plan, "original_root_ledger", None)
    if ledger is not None:
        if not ledger.admitted:
            return DesignTupleFullStringSI(
                ledger.status, None, (), 0, 0, False, False, 0.0,
                "full-string child cannot start from a rejected original-root ledger",
            )
        if int(root_n) != ledger.original_root_degree:
            return DesignTupleFullStringSI(
                "design_full_string_original_root_ledger_mismatch", None, (), 0, 0,
                False, False, 0.0,
                "the full-string child root differs from the root fixed before the first t-WL execution",
            )
        if (
            int(max_design_full_string_child_work) > ledger.child_si_work_upper_bound
            or int(max_design_union_reconstruction_work) > ledger.union_work_upper_bound
        ):
            return DesignTupleFullStringSI(
                "design_full_string_exceeds_original_root_ledger", None, (), 0, 0,
                False, False, 0.0,
                "the child-SI or union budget exceeds the amount reserved before the first t-WL execution",
            )

    if transport_plan.exact_empty:
        return DesignTupleFullStringSI(
            "exact_empty_design_tuple_transport", None, (), 0, 0,
            True, True, transport_plan.local_log2_cost_bound + 8.0,
            "the complete upstream tuple-transporter cover is already exactly empty",
        )
    if not transport_plan.complete or transport_plan.status != "certified_complete_design_tuple_transport_cover":
        return DesignTupleFullStringSI(
            "undetermined_incomplete_design_tuple_transport", None, (), 0, 0,
            False, False, 0.0,
            "full-string branch solving requires a complete exact tuple-transporter cover",
        )

    child_preflight = design_full_string_child_preflight(
        transport_plan.branches,
        original_root_degree=root_n,
        original_degree=n,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_work=max_design_full_string_child_work,
        target_values=target,
    )
    if not child_preflight.admitted:
        return DesignTupleFullStringSI(
            child_preflight.status, None, (), 0, 0, False, False, 0.0,
            child_preflight.reason, None, child_preflight,
        )

    solved = []
    nonempty = []
    for branch_index, branch in enumerate(transport_plan.branches):
        if branch.coset is None:
            raise AssertionError("a surviving tuple branch must carry a right coset")
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
            max_state_orbit_work=(
                child_preflight.state_orbit_work_upper_bounds[branch_index]
                if child_preflight.terminal_kinds[branch_index] == "state_orbit"
                else 0
            ),
        )
        solved.append(child)
        if not child.exact:
            partial_preflight = record_design_full_string_child_execution(
                child_preflight, solved, complete=False,
            )
            return DesignTupleFullStringSI(
                "undetermined_design_tuple_full_string_branch", None, tuple(solved),
                len(solved), len(nonempty), False, False, 0.0,
                "at least one branch in the complete tuple cover remains unresolved; exact union reconstruction is withheld",
                None, partial_preflight,
            )
        if child.coset is not None:
            nonempty.append(child.coset)

    child_preflight = record_design_full_string_child_execution(
        child_preflight, solved, complete=True,
    )
    child_resource = certify_design_full_string_child_resources(
        solved,
        expected_branch_count=transport_plan.surviving_branch_count,
        original_root_degree=root_n,
        quasipoly_power=quasipoly_power,
        quasipoly_constant=quasipoly_constant,
    )
    if not child_resource.certified:
        return DesignTupleFullStringSI(
            "undetermined_design_tuple_full_string_child_resources", None,
            tuple(solved), len(solved), len(nonempty), False, False, 0.0,
            child_resource.reason, child_resource, child_preflight,
        )

    layer_bound = (
        transport_plan.local_log2_cost_bound
        + log2(max(1, len(solved)))
        + max((c.local_log2_cost_bound for c in solved), default=0.0)
        + 6.0 * log2(max(2, n))
        + 32.0
    )
    if not nonempty:
        return DesignTupleFullStringSI(
            "exact_empty_design_tuple_full_string_union", None, tuple(solved),
            len(solved), 0, True, True, layer_bound,
            "every branch in the complete tuple-transporter cover has an exact empty full-string intersection",
            child_resource, child_preflight,
        )

    union_resource = design_union_reconstruction_resource_envelope(
        ambient_group,
        solved,
        max_work=max_design_union_reconstruction_work,
    )
    if not union_resource.admitted:
        return DesignTupleFullStringSI(
            union_resource.status, None, tuple(solved), len(solved), len(nonempty),
            False, False, layer_bound, union_resource.reason,
            child_resource, child_preflight, union_resource,
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
    union_resource = record_design_union_reconstruction_execution(
        union_resource,
        executed_generator_count=len(generators),
        complete=True,
    )
    return DesignTupleFullStringSI(
        "exact_design_tuple_full_string_union_coset",
        RightCoset(target_aut, r0),
        tuple(solved), len(solved), len(nonempty),
        True, True, layer_bound,
        "all tuple branches were exactly intersected with the original string and their complete union was reconstructed as one target-automorphism right coset",
        child_resource, child_preflight, union_resource,
    )
