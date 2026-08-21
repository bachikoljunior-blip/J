from __future__ import annotations

from dataclasses import dataclass, replace

from design_nested_primitive_johnson_resource_v1 import (
    NestedPrimitiveJohnsonResourceEnvelope,
    design_nested_primitive_johnson_resource_envelope,
)
from local_certificate_preimage_resource_v1 import _sat_add
from s1_structural_classifier_v1 import classify_s1_structure


ROBUST_ORBITAL_DEGREE = 128


@dataclass(frozen=True)
class PrimitiveJohnsonBranchReservation:
    branch_index: int
    classification_status: str
    canonical_classification: bool
    selected: bool
    resource_envelope: NestedPrimitiveJohnsonResourceEnvelope | None
    reserved_work_upper_bound: int
    root_lift_work_upper_bound: int
    parent_order_upper_bound: int
    image_order_upper_bound: int
    generator_upper_bound: int
    reason: str


@dataclass(frozen=True)
class DesignPrimitiveJohnsonCompleteCoverPreflight:
    status: str
    original_root_degree: int
    original_degree: int
    branch_count: int
    candidate_branch_indices: tuple[int, ...]
    branch_reservations: tuple[PrimitiveJohnsonBranchReservation, ...]
    selected_branch_count: int
    work_upper_bound: int
    root_lift_work_upper_bound: int
    max_work: int
    root_lift_certified: bool
    complete_selection: bool
    admitted: bool
    executed_branch_count: int
    charged_work_upper_bound: int
    execution_charge_complete: bool
    reason: str


def _candidate_indices(branch_count: int, requested) -> tuple[int, ...]:
    if requested is None:
        return tuple(range(branch_count))
    indices = tuple(int(index) for index in requested)
    if len(set(indices)) != len(indices):
        raise ValueError("primitive Johnson candidate branch indices must be unique")
    if any(index < 0 or index >= branch_count for index in indices):
        raise ValueError("primitive Johnson candidate branch index is outside the complete cover")
    return tuple(sorted(indices))


def design_primitive_johnson_complete_cover_preflight(
    branches,
    *,
    original_root_degree: int,
    original_degree: int,
    candidate_branch_indices=None,
    polylog_power: int = 2,
    max_explicit_degree: int = 8,
    max_recognition_nodes: int = 500000,
    max_partition_states: int = 4096,
    max_work: int,
) -> DesignPrimitiveJohnsonCompleteCoverPreflight:
    """Reserve every caller-selected primitive-Johnson branch before execution.

    This is the collision-free adapter between the rev243 resource envelope and
    the rev246 executable primitive-Johnson operator.  A shared Design caller can
    hand this routine exactly the branch indices left unresolved by its cheaper
    terminals.  The adapter classifies every such branch *before any rev246
    execution*, admits only exact ``primitive_non_giant`` classifications, and
    sums the full recognition/profile/partition/original-root-lift reservation
    for the entire selected subcover under one caller cap.

    Non-selected branches are deliberately outside this adapter and must already
    be reserved by the caller's other terminal preflights.  If even one selected
    branch is not canonically primitive-non-giant, lacks an admitted rev243
    envelope, or causes the aggregate cap to overflow, no selected branch is
    admitted for execution.
    """
    frozen = tuple(branches)
    root = int(original_root_degree)
    n = int(original_degree)
    power = int(polylog_power)
    explicit_degree = int(max_explicit_degree)
    recognition_nodes = int(max_recognition_nodes)
    partition_states = int(max_partition_states)
    cap = int(max_work)
    if min(root, n, power, explicit_degree, recognition_nodes, partition_states, cap) <= 0:
        raise ValueError("invalid primitive Johnson complete-cover preflight parameters")

    indices = _candidate_indices(len(frozen), candidate_branch_indices)
    if root < n:
        return DesignPrimitiveJohnsonCompleteCoverPreflight(
            "design_primitive_johnson_complete_cover_original_root_lift_unavailable",
            root,
            n,
            len(frozen),
            indices,
            (),
            0,
            0,
            0,
            cap,
            False,
            False,
            False,
            0,
            0,
            False,
            "the full-string child degree exceeds the original root",
        )

    if not indices:
        return DesignPrimitiveJohnsonCompleteCoverPreflight(
            "certified_empty_design_primitive_johnson_complete_cover_preflight",
            root,
            n,
            len(frozen),
            (),
            (),
            0,
            0,
            0,
            cap,
            True,
            True,
            True,
            0,
            0,
            False,
            "the caller selected no unresolved primitive-Johnson branches; the adapter is an exact no-op",
        )

    reservations = []
    total = 0
    root_lift_total = 0
    stop = cap + 1
    complete_selection = True
    all_resource_admitted = True

    for branch_index in indices:
        branch = frozen[branch_index]
        coset = getattr(branch, "coset", None)
        if coset is None:
            raise ValueError("a selected Design branch must carry a right coset")
        group = coset.subgroup
        if int(group.degree) != n:
            raise ValueError("selected Design branch group degree does not match the full-string degree")

        classification = classify_s1_structure(
            group,
            root_n=root,
            polylog_power=power,
            max_explicit_degree=explicit_degree,
        )
        classification_status = str(classification.status)
        canonical = bool(classification.canonical)
        if classification_status != "primitive_non_giant" or not canonical:
            complete_selection = False
            reservations.append(
                PrimitiveJohnsonBranchReservation(
                    branch_index,
                    classification_status,
                    canonical,
                    False,
                    None,
                    0,
                    0,
                    int(group.order),
                    int(group.order),
                    max(1, len(tuple(group.original_generators))),
                    "the exact structural classifier did not select the primitive non-giant path",
                )
            )
            continue

        order = int(group.order)
        generators = max(1, len(tuple(group.original_generators)))
        envelope = design_nested_primitive_johnson_resource_envelope(
            original_root_degree=root,
            original_degree=n,
            image_degree=n,
            parent_order_upper_bound=order,
            image_order_upper_bound=order,
            generator_upper_bound=generators,
            max_recognition_nodes=recognition_nodes,
            max_robust_orbital_degree=ROBUST_ORBITAL_DEGREE,
            partition_state_poly_power=2,
            max_partition_states=partition_states,
            max_work=cap,
        )
        work = int(envelope.work_upper_bound)
        root_lift_work = int(envelope.original_root_lift_work_upper_bound)
        total = _sat_add(total, work, stop)
        root_lift_total = _sat_add(root_lift_total, root_lift_work, stop)
        if not envelope.resource_admitted:
            all_resource_admitted = False
        reservations.append(
            PrimitiveJohnsonBranchReservation(
                branch_index,
                classification_status,
                canonical,
                bool(envelope.resource_admitted),
                envelope,
                work,
                root_lift_work,
                order,
                order,
                generators,
                envelope.reason,
            )
        )

    root_lift_certified = all(
        reservation.resource_envelope is not None
        and bool(reservation.resource_envelope.root_lift_certified)
        for reservation in reservations
        if reservation.classification_status == "primitive_non_giant"
    )
    selected = sum(1 for reservation in reservations if reservation.selected)
    admitted = bool(
        complete_selection
        and all_resource_admitted
        and root_lift_certified
        and selected == len(indices)
        and total <= cap
    )

    if not complete_selection:
        status = "design_primitive_johnson_complete_cover_path_unavailable"
        reason = (
            "at least one caller-selected branch is not canonically primitive-non-giant; "
            "no primitive-Johnson branch in the selected subcover may start"
        )
    elif not all_resource_admitted or not root_lift_certified:
        status = "design_primitive_johnson_complete_cover_resource_unavailable"
        reason = (
            "at least one selected primitive-non-giant branch lacks the complete rev243 "
            "recognition/profile/partition/original-root-lift reservation"
        )
    elif total > cap:
        status = "design_primitive_johnson_complete_cover_work_cap_exceeded"
        reason = (
            "the sum of every selected primitive-Johnson branch reservation exceeds "
            "the caller cap before the first rev246 execution"
        )
    else:
        status = "certified_design_primitive_johnson_complete_cover_preflight"
        reason = (
            "every caller-selected branch is canonically primitive-non-giant and the "
            "complete rev243 resource plus original-root-lift charge for the selected "
            "subcover fits the finite caller cap before execution"
        )

    return DesignPrimitiveJohnsonCompleteCoverPreflight(
        status,
        root,
        n,
        len(frozen),
        indices,
        tuple(reservations),
        selected,
        total,
        root_lift_total,
        cap,
        root_lift_certified,
        complete_selection,
        admitted,
        0,
        0,
        False,
        reason,
    )


def _execution_fits_reservation(result, reservation: PrimitiveJohnsonBranchReservation) -> int:
    if not reservation.selected or reservation.resource_envelope is None:
        raise ValueError("cannot execute an unselected primitive-Johnson reservation")
    if not bool(getattr(result, "production_attempt_admitted", False)):
        raise ValueError("rev246 result is not a production-admitted primitive-Johnson attempt")
    if str(getattr(result, "classification_status", "")) != "primitive_non_giant":
        raise ValueError("rev246 result lost the primitive-non-giant structural certificate")
    actual = getattr(result, "resource_envelope", None)
    if actual is None or not bool(getattr(actual, "resource_admitted", False)):
        raise ValueError("rev246 result does not carry an admitted resource envelope")
    reserved = reservation.resource_envelope

    exact_fields = ("original_root_degree", "original_degree", "image_degree")
    for field in exact_fields:
        if int(getattr(actual, field)) != int(getattr(reserved, field)):
            raise ValueError(f"rev246 execution changed reserved {field}")
    upper_fields = (
        "parent_order_upper_bound",
        "image_order_upper_bound",
        "generator_upper_bound",
        "partition_state_upper_bound",
        "partition_action_upper_bound",
        "original_root_lift_work_upper_bound",
        "work_upper_bound",
    )
    for field in upper_fields:
        if int(getattr(actual, field)) > int(getattr(reserved, field)):
            raise ValueError(f"rev246 execution exceeded reserved {field}")

    reserved_parameters = set(tuple(pair) for pair in reserved.johnson_parameter_candidates)
    actual_parameters = set(tuple(pair) for pair in actual.johnson_parameter_candidates)
    if not actual_parameters.issubset(reserved_parameters):
        raise ValueError("rev246 execution escaped the reserved Johnson parameter family")
    charged = int(getattr(result, "charged_work_upper_bound", 0))
    if charged <= 0 or charged > int(reservation.reserved_work_upper_bound):
        raise ValueError("rev246 execution charge exceeds the complete-cover reservation")
    return charged


def record_design_primitive_johnson_complete_cover_execution(
    preflight: DesignPrimitiveJohnsonCompleteCoverPreflight,
    branch_results,
    *,
    complete: bool,
) -> DesignPrimitiveJohnsonCompleteCoverPreflight:
    """Bind ordered rev246 executions back to the pre-execution cover ledger."""
    if not preflight.admitted:
        raise ValueError("cannot record primitive-Johnson execution for a rejected preflight")
    frozen = tuple(branch_results)
    if len(frozen) > preflight.selected_branch_count:
        raise ValueError("executed primitive-Johnson branch count exceeds the selected cover")
    if complete and len(frozen) != preflight.selected_branch_count:
        raise ValueError("complete primitive-Johnson execution omitted a selected branch")

    charged = 0
    stop = preflight.max_work + 1
    for result, reservation in zip(frozen, preflight.branch_reservations):
        charged = _sat_add(charged, _execution_fits_reservation(result, reservation), stop)
    reserved_prefix = sum(
        int(reservation.reserved_work_upper_bound)
        for reservation in preflight.branch_reservations[: len(frozen)]
    )
    if charged > reserved_prefix or charged > preflight.work_upper_bound:
        raise ValueError("aggregate rev246 execution charge exceeded the reserved cover ledger")

    execution_complete = bool(complete and len(frozen) == preflight.selected_branch_count)
    return replace(
        preflight,
        executed_branch_count=len(frozen),
        charged_work_upper_bound=charged,
        execution_charge_complete=execution_complete,
    )


__all__ = [
    "PrimitiveJohnsonBranchReservation",
    "DesignPrimitiveJohnsonCompleteCoverPreflight",
    "design_primitive_johnson_complete_cover_preflight",
    "record_design_primitive_johnson_complete_cover_execution",
]
