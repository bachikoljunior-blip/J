from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from coset_stabilizer_primitives import RightCoset
from implicit_relation_image_action_v1 import (
    ImplicitRelationImageAction,
    prepare_implicit_relation_image_action,
)
from permutation_group_schreier import identity
from proof_carrying_si_v1 import ProofCarryingCoset
from u2_candidate_coset_string_iso_v2 import candidate_coset_string_isomorphism_u2
from bounded_arity_relation_image_solver import BoundedArityRelationImage


@dataclass(frozen=True)
class ImplicitRelationImageCosetIntersection:
    status: str
    exact: bool
    complete: bool
    auxiliary_degree: int
    action: ImplicitRelationImageAction
    proof: Optional[ProofCarryingCoset]
    coset: Optional[RightCoset]
    reason: str


def exact_implicit_relation_image_coset_intersection(
    source: BoundedArityRelationImage,
    target: BoundedArityRelationImage,
    domain_generators: Iterable[Iterable[int]],
    *,
    max_auxiliary_degree: int = 100_000,
    max_generators: int = 10_000,
    max_action_point_checks: int = 10_000_000,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    group_order_poly_power: int = 2,
    max_group_order: int = 256,
    max_depth: int = 64,
    max_state_orbit_work: int = 0,
    max_imprimitive_quotient_kernel_work: int = 0,
) -> ImplicitRelationImageCosetIntersection:
    """Intersect rev257's implicit image group with the complete value coset.

    The faithful auxiliary action is built from the supplied domain generators.
    Its exact image group is then treated as the ambient subgroup of one identity
    right coset and passed to the repository's proof-carrying U2 string
    isomorphism solver.  Therefore an ``exact`` result is the complete
    source-to-target value-preserving transporter *inside that implicit image
    group*, not an enumeration-derived approximation.

    This layer intentionally does not lift the resulting auxiliary coset back to
    the original domain and does not claim an original-root quasipolynomial work
    envelope.  Those remain later rev257/rev258 children.
    """

    action = prepare_implicit_relation_image_action(
        source,
        target,
        domain_generators,
        max_auxiliary_degree=max_auxiliary_degree,
        max_generators=max_generators,
        max_action_point_checks=max_action_point_checks,
    )

    if action.status.startswith("exact_empty_"):
        return ImplicitRelationImageCosetIntersection(
            action.status,
            True,
            True,
            action.auxiliary_degree,
            action,
            None,
            None,
            action.reason,
        )

    if action.status != "exact_implicit_relation_image_paired_action":
        return ImplicitRelationImageCosetIntersection(
            "undetermined_implicit_relation_image_action",
            False,
            False,
            action.auxiliary_degree,
            action,
            None,
            None,
            action.reason,
        )

    if action.image_group is None:
        raise AssertionError("exact implicit action is missing its image group")

    candidate = RightCoset(
        action.image_group,
        identity(action.auxiliary_degree),
    )
    proof = candidate_coset_string_isomorphism_u2(
        candidate,
        action.source_features,
        action.target_features,
        root_n=action.auxiliary_degree,
        polylog_power=polylog_power,
        max_explicit_degree=max_explicit_degree,
        group_order_poly_power=group_order_poly_power,
        max_group_order=max_group_order,
        max_depth=max_depth,
        max_state_orbit_work=max_state_orbit_work,
        max_imprimitive_quotient_kernel_work=max_imprimitive_quotient_kernel_work,
    )

    if not proof.exact:
        return ImplicitRelationImageCosetIntersection(
            "undetermined_implicit_image_value_coset_intersection",
            False,
            False,
            action.auxiliary_degree,
            action,
            proof,
            None,
            proof.reason,
        )

    if proof.coset is None:
        return ImplicitRelationImageCosetIntersection(
            "exact_empty_implicit_image_value_coset",
            True,
            True,
            action.auxiliary_degree,
            action,
            proof,
            None,
            "proof-carrying U2 certified that no implicit image-group element transports the source auxiliary value string to the target",
        )

    return ImplicitRelationImageCosetIntersection(
        "exact_implicit_image_value_coset_intersection",
        True,
        True,
        action.auxiliary_degree,
        action,
        proof,
        proof.coset,
        "proof-carrying U2 returned the complete source-to-target value-preserving right coset inside rev257's exact implicit auxiliary image group",
    )
