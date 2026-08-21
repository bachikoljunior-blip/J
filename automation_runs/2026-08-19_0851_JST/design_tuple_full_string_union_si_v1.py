from __future__ import annotations

from dataclasses import dataclass, replace
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
from design_primitive_johnson_complete_cover_preflight_v1 import (
    record_design_primitive_johnson_complete_cover_execution,
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

    The complete child cover is reserved before execution.  When rev254 marks a
    subset of branches as primitive-Johnson, each corresponding U2 call consumes
    its exact rev246 reservation and the caller records the ordered execution
    charges back into the same complete-cover ledger before union reconstruction.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    n = int(ambient_group.degree)
    if len(source) != n or len(target) != n:
        raise ValueError("string/group degree mismatch")
    if root_n < n:
        raise ValueError("root_n must dominate current degree")

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

    primitive_preflight = child_preflight.primitive_johnson_preflight
    primitive_reservations = {}
    if primitive_preflight is not None:
        primitive_reservations = {
            reservation.branch_index: reservation
            for reservation in primitive_preflight.branch_reservations
        }
    primitive_results = []

    solved = []
    nonempty = []
    for branch_index, branch in enumerate(transport_plan.branches):
        if branch.coset is None:
            raise AssertionError("a surviving tuple branch must carry a right coset")
        if not ambient_group.contains(branch.coset.representative):
            raise AssertionError("tuple-branch representative escaped the ambient group")
        terminal_kind = child_preflight.terminal_kinds[branch_index]
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
                if terminal_kind == "state_orbit"
                else 0
            ),
            max_imprimitive_quotient_kernel_work=(
                child_preflight.imprimitive_work_upper_bounds[branch_index]
                if terminal_kind == "imprimitive_quotient_kernel"
                else 0
            ),
            primitive_johnson_reservation=(
                primitive_reservations.get(branch_index)
                if terminal_kind == "primitive_johnson"
                else None
            ),
        )
        solved.append(child)

        if terminal_kind == "primitive_johnson":
            primitive_results.append(child)
            if primitive_preflight is None:
                raise AssertionError("primitive-Johnson child lacks the complete-cover preflight")
            if bool(getattr(child, "production_attempt_admitted", False)):
                primitive_preflight = record_design_primitive_johnson_complete_cover_execution(
                    primitive_preflight,
                    primitive_results,
                    complete=False,
                )
                child_preflight = replace(
                    child_preflight,
                    primitive_johnson_preflight=primitive_preflight,
                )

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

    if primitive_preflight is not None and primitive_preflight.selected_branch_count:
        if len(primitive_results) != primitive_preflight.selected_branch_count:
            return DesignTupleFullStringSI(
                "undetermined_design_primitive_johnson_execution_ledger", None,
                tuple(solved), len(solved), len(nonempty), False, False, 0.0,
                "the executed primitive-Johnson branches do not match the caller-selected complete subcover",
                None, child_preflight,
            )
        if not all(bool(getattr(result, "production_attempt_admitted", False)) for result in primitive_results):
            return DesignTupleFullStringSI(
                "undetermined_design_primitive_johnson_execution_ledger", None,
                tuple(solved), len(solved), len(nonempty), False, False, 0.0,
                "at least one selected primitive-Johnson branch did not carry a production-admitted rev246 execution charge",
                None, child_preflight,
            )
        primitive_preflight = record_design_primitive_johnson_complete_cover_execution(
            primitive_preflight,
            primitive_results,
            complete=True,
        )
        if not primitive_preflight.execution_charge_complete:
            return DesignTupleFullStringSI(
                "undetermined_design_primitive_johnson_execution_ledger", None,
                tuple(solved), len(solved), len(nonempty), False, False, 0.0,
                "the rev254 primitive-Johnson complete-cover execution ledger is incomplete",
                None, child_preflight,
            )
        child_preflight = replace(
            child_preflight,
            primitive_johnson_preflight=primitive_preflight,
        )

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
