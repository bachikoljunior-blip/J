"""Fail-closed production admission for the proof-carrying small-order SI terminal.

rev170 made the small-order terminal exact and locally cost-certified.  rev251
added an independent finite-group exact-result replay verifier.  This module
joins those two proof boundaries without modifying the shared solver: production
admission is granted only when the producer's proof metadata is internally
consistent, its recurrence leaf is certified, and a second independently
materialized group enumeration passes the rev251 complete replay/coset check.

The admission gate is deliberately stricter than the underlying solver.  It
preflights all degree/order/quadratic replay caps before invoking the producer,
so an over-cap request stays fail-closed and performs no group enumeration.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Any, Sequence

from certified_group_enumeration_v1 import enumerate_schreier_group_exact
from exact_result_replay_verifier_v1 import (
    CertificateBuildError,
    ReplayCaps,
    ReplayStatus,
    ReplayVerification,
    build_certificate,
    certificate_digest,
    verify_exact_result_replay,
)
from permutation_group_schreier import identity
from proof_carrying_small_order_si_v1 import (
    SmallOrderProofCarryingCoset,
    exact_small_order_group_string_isomorphism,
)
from quasipoly_recurrence_accounting_v3 import validate_quasipoly_recurrence_tree_v3


class ProductionAdmissionStatus(str, Enum):
    ADMITTED_EXACT = "admitted_exact"
    UNKNOWN_RESOURCE_CAP = "unknown_resource_cap"
    REJECTED_INPUT = "rejected_input"
    REJECTED_PRODUCER_PROOF = "rejected_producer_proof"
    REJECTED_REPLAY = "rejected_replay"


@dataclass(frozen=True)
class ProductionAdmissionCaps:
    """Finite production caps covering both producer and independent replay."""

    max_degree: int = 64
    max_group_order: int = 1_024
    max_group_compositions: int = 1_048_576
    max_action_point_checks: int = 2_000_000
    max_certificate_bytes: int = 4_000_000

    def validate(self) -> None:
        for name, value in vars(self).items():
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")

    def replay_caps(self) -> ReplayCaps:
        return ReplayCaps(
            max_degree=self.max_degree,
            max_group_size=self.max_group_order,
            max_group_compositions=self.max_group_compositions,
            max_action_point_checks=self.max_action_point_checks,
            max_certificate_bytes=self.max_certificate_bytes,
        )


@dataclass(frozen=True)
class ProductionPreflight:
    admitted: bool
    reason: str
    degree: int
    group_order: int
    root_n: int
    allowed_group_order: int
    required_group_compositions: int
    required_action_point_checks: int


@dataclass(frozen=True)
class SmallOrderProductionAdmission:
    status: ProductionAdmissionStatus
    reason: str
    preflight: ProductionPreflight
    producer_invoked: bool
    producer_status: str | None
    producer_group_elements_checked: int
    replay: ReplayVerification | None
    recurrence_status: str | None
    recurrence_certified: bool
    certificate_sha256: str | None
    claimed_match_count: int

    @property
    def admitted(self) -> bool:
        return self.status is ProductionAdmissionStatus.ADMITTED_EXACT


def _preflight_reject(
    reason: str,
    *,
    degree: int,
    group_order: int,
    root_n: int,
    allowed: int,
    compositions: int,
    checks: int,
) -> ProductionPreflight:
    return ProductionPreflight(
        False,
        reason,
        degree,
        group_order,
        root_n,
        allowed,
        compositions,
        checks,
    )


def preflight_small_order_production_admission(
    group,
    source_values: Sequence[Any],
    target_values: Sequence[Any],
    *,
    root_n: int | None = None,
    group_order_poly_power: int = 2,
    caps: ProductionAdmissionCaps = ProductionAdmissionCaps(),
) -> ProductionPreflight:
    """Reserve all order-dependent producer/replay work before solver execution."""

    try:
        caps.validate()
    except ValueError as exc:
        return _preflight_reject(
            f"invalid production caps: {exc}",
            degree=0,
            group_order=0,
            root_n=0,
            allowed=0,
            compositions=0,
            checks=0,
        )

    if type(group_order_poly_power) is not int or group_order_poly_power < 1:
        return _preflight_reject(
            "group_order_poly_power must be a positive integer",
            degree=getattr(group, "degree", 0),
            group_order=getattr(group, "order", 0),
            root_n=0 if root_n is None else root_n,
            allowed=0,
            compositions=0,
            checks=0,
        )
    if not hasattr(group, "degree") or not hasattr(group, "order"):
        return _preflight_reject(
            "group lacks certified degree/order metadata",
            degree=0,
            group_order=0,
            root_n=0 if root_n is None else root_n,
            allowed=0,
            compositions=0,
            checks=0,
        )

    degree = group.degree
    group_order = group.order
    if type(degree) is not int or degree < 1 or type(group_order) is not int or group_order < 1:
        return _preflight_reject(
            "group degree/order must be positive integers",
            degree=degree if type(degree) is int else 0,
            group_order=group_order if type(group_order) is int else 0,
            root_n=0 if root_n is None else root_n,
            allowed=0,
            compositions=0,
            checks=0,
        )
    try:
        source_len = len(source_values)
        target_len = len(target_values)
    except TypeError:
        return _preflight_reject(
            "source and target must be sized sequences",
            degree=degree,
            group_order=group_order,
            root_n=degree if root_n is None else root_n,
            allowed=0,
            compositions=0,
            checks=0,
        )
    if source_len != degree or target_len != degree:
        return _preflight_reject(
            "source/target lengths must equal the represented group degree",
            degree=degree,
            group_order=group_order,
            root_n=degree if root_n is None else root_n,
            allowed=0,
            compositions=0,
            checks=0,
        )

    if root_n is None:
        root_n = degree
    if type(root_n) is not int or root_n < degree:
        return _preflight_reject(
            "root_n must be an integer dominating the current degree",
            degree=degree,
            group_order=group_order,
            root_n=root_n if type(root_n) is int else 0,
            allowed=0,
            compositions=0,
            checks=0,
        )

    allowed = min(caps.max_group_order, root_n ** group_order_poly_power)
    compositions = group_order * group_order
    checks = 2 * group_order * degree
    if degree > caps.max_degree:
        return _preflight_reject(
            "degree exceeds the production replay cap",
            degree=degree,
            group_order=group_order,
            root_n=root_n,
            allowed=allowed,
            compositions=compositions,
            checks=checks,
        )
    if group_order > allowed:
        return _preflight_reject(
            "Schreier-certified group order exceeds the production small-order gate",
            degree=degree,
            group_order=group_order,
            root_n=root_n,
            allowed=allowed,
            compositions=compositions,
            checks=checks,
        )
    if compositions > caps.max_group_compositions:
        return _preflight_reject(
            "independent group-closure replay exceeds max_group_compositions",
            degree=degree,
            group_order=group_order,
            root_n=root_n,
            allowed=allowed,
            compositions=compositions,
            checks=checks,
        )
    if checks > caps.max_action_point_checks:
        return _preflight_reject(
            "independent action replay exceeds max_action_point_checks",
            degree=degree,
            group_order=group_order,
            root_n=root_n,
            allowed=allowed,
            compositions=compositions,
            checks=checks,
        )
    return ProductionPreflight(
        True,
        "all producer and quadratic exact-replay work fits the declared production caps",
        degree,
        group_order,
        root_n,
        allowed,
        compositions,
        checks,
    )


def _outcome(
    status: ProductionAdmissionStatus,
    reason: str,
    *,
    preflight: ProductionPreflight,
    producer_invoked: bool,
    producer: SmallOrderProofCarryingCoset | None = None,
    replay: ReplayVerification | None = None,
    recurrence_status: str | None = None,
    recurrence_certified: bool = False,
    digest: str | None = None,
    claimed_match_count: int = 0,
) -> SmallOrderProductionAdmission:
    return SmallOrderProductionAdmission(
        status=status,
        reason=reason,
        preflight=preflight,
        producer_invoked=producer_invoked,
        producer_status=None if producer is None else producer.status,
        producer_group_elements_checked=(
            0 if producer is None else producer.group_elements_checked
        ),
        replay=replay,
        recurrence_status=recurrence_status,
        recurrence_certified=recurrence_certified,
        certificate_sha256=digest,
        claimed_match_count=claimed_match_count,
    )


def verify_small_order_production_result(
    group,
    source_values: Sequence[Any],
    target_values: Sequence[Any],
    producer: SmallOrderProofCarryingCoset,
    *,
    root_n: int | None = None,
    group_order_poly_power: int = 2,
    caps: ProductionAdmissionCaps = ProductionAdmissionCaps(),
    preflight: ProductionPreflight | None = None,
) -> SmallOrderProductionAdmission:
    """Independently verify one already-produced small-order terminal result."""

    if preflight is None:
        preflight = preflight_small_order_production_admission(
            group,
            source_values,
            target_values,
            root_n=root_n,
            group_order_poly_power=group_order_poly_power,
            caps=caps,
        )
    if not preflight.admitted:
        return _outcome(
            ProductionAdmissionStatus.UNKNOWN_RESOURCE_CAP,
            preflight.reason,
            preflight=preflight,
            producer_invoked=True,
            producer=producer if isinstance(producer, SmallOrderProofCarryingCoset) else None,
        )
    if not isinstance(producer, SmallOrderProofCarryingCoset):
        return _outcome(
            ProductionAdmissionStatus.REJECTED_PRODUCER_PROOF,
            "producer result is not a SmallOrderProofCarryingCoset",
            preflight=preflight,
            producer_invoked=True,
        )

    degree = preflight.degree
    group_order = preflight.group_order
    root = preflight.root_n
    if not (
        producer.canonical
        and producer.exact
        and producer.local_cost_certified
        and producer.terminal_certified
        and producer.operation_kind == "small_order_group_si_terminal"
        and producer.children == ()
        and producer.root_n == root
        and producer.domain_size == degree
        and producer.certified_group_order == group_order
        and producer.permutation_candidates_checked == producer.group_elements_checked
        and isfinite(producer.local_log2_cost_bound)
        and producer.local_log2_cost_bound >= 0.0
    ):
        return _outcome(
            ProductionAdmissionStatus.REJECTED_PRODUCER_PROOF,
            "producer proof metadata is inconsistent with an exact small-order terminal",
            preflight=preflight,
            producer_invoked=True,
            producer=producer,
        )

    accounting = producer.accounting
    if not (
        accounting.n == root
        and accounting.m == max(1, degree)
        and accounting.operation_kind == "small_order_group_si_terminal"
        and accounting.canonical
        and accounting.cost_certified
        and accounting.terminal_certified
        and accounting.children == ()
        and accounting.local_log2_cost_bound == producer.local_log2_cost_bound
    ):
        return _outcome(
            ProductionAdmissionStatus.REJECTED_PRODUCER_PROOF,
            "producer accounting leaf does not match its terminal proof metadata",
            preflight=preflight,
            producer_invoked=True,
            producer=producer,
        )

    recurrence = validate_quasipoly_recurrence_tree_v3(accounting)
    if not recurrence.certified:
        return _outcome(
            ProductionAdmissionStatus.REJECTED_PRODUCER_PROOF,
            f"recurrence accounting rejected the terminal: {recurrence.reason}",
            preflight=preflight,
            producer_invoked=True,
            producer=producer,
            recurrence_status=recurrence.status,
            recurrence_certified=False,
        )

    if producer.status == "exact_empty_small_order_group":
        if producer.coset is not None or producer.group_elements_checked != group_order:
            return _outcome(
                ProductionAdmissionStatus.REJECTED_PRODUCER_PROOF,
                "exact-empty producer has a coset or an impossible scan count",
                preflight=preflight,
                producer_invoked=True,
                producer=producer,
                recurrence_status=recurrence.status,
                recurrence_certified=True,
            )
    elif producer.status == "exact_small_order_group_coset":
        if producer.coset is None or producer.group_elements_checked != 2 * group_order:
            return _outcome(
                ProductionAdmissionStatus.REJECTED_PRODUCER_PROOF,
                "nonempty producer lacks its coset or second-pass audit count",
                preflight=preflight,
                producer_invoked=True,
                producer=producer,
                recurrence_status=recurrence.status,
                recurrence_certified=True,
            )
        if producer.coset.subgroup.degree != degree:
            return _outcome(
                ProductionAdmissionStatus.REJECTED_PRODUCER_PROOF,
                "producer coset degree differs from the represented group",
                preflight=preflight,
                producer_invoked=True,
                producer=producer,
                recurrence_status=recurrence.status,
                recurrence_certified=True,
            )
    else:
        return _outcome(
            ProductionAdmissionStatus.REJECTED_PRODUCER_PROOF,
            "producer exact status is not a recognized small-order terminal status",
            preflight=preflight,
            producer_invoked=True,
            producer=producer,
            recurrence_status=recurrence.status,
            recurrence_certified=True,
        )

    try:
        elements = enumerate_schreier_group_exact(group, max_elements=preflight.allowed_group_order)
    except (AssertionError, ValueError) as exc:
        return _outcome(
            ProductionAdmissionStatus.REJECTED_PRODUCER_PROOF,
            f"independent Schreier enumeration failed: {exc}",
            preflight=preflight,
            producer_invoked=True,
            producer=producer,
            recurrence_status=recurrence.status,
            recurrence_certified=True,
        )
    if elements is None or len(elements) != group_order:
        return _outcome(
            ProductionAdmissionStatus.REJECTED_PRODUCER_PROOF,
            "independent enumeration did not recover the certified represented group",
            preflight=preflight,
            producer_invoked=True,
            producer=producer,
            recurrence_status=recurrence.status,
            recurrence_certified=True,
        )

    if producer.coset is None:
        claimed_matches = ()
    else:
        element_set = set(elements)
        if producer.coset.representative not in element_set:
            return _outcome(
                ProductionAdmissionStatus.REJECTED_PRODUCER_PROOF,
                "producer coset representative is outside the represented group",
                preflight=preflight,
                producer_invoked=True,
                producer=producer,
                recurrence_status=recurrence.status,
                recurrence_certified=True,
            )
        claimed_matches = tuple(p for p in elements if producer.coset.contains(p))
        if len(claimed_matches) != producer.coset.subgroup.order:
            return _outcome(
                ProductionAdmissionStatus.REJECTED_PRODUCER_PROOF,
                "producer right coset is not wholly contained in the represented group",
                preflight=preflight,
                producer_invoked=True,
                producer=producer,
                recurrence_status=recurrence.status,
                recurrence_certified=True,
                claimed_match_count=len(claimed_matches),
            )

    try:
        certificate = build_certificate(
            source=source_values,
            target=target_values,
            candidate_group=elements,
            claimed_matches=claimed_matches,
            universe_label=(
                f"rev252-small-order-production:root={root}:degree={degree}:order={group_order}"
            ),
            solver_status="exact",
        )
    except (CertificateBuildError, TypeError, ValueError) as exc:
        return _outcome(
            ProductionAdmissionStatus.REJECTED_INPUT,
            f"replay certificate could not snapshot the production input: {exc}",
            preflight=preflight,
            producer_invoked=True,
            producer=producer,
            recurrence_status=recurrence.status,
            recurrence_certified=True,
            claimed_match_count=len(claimed_matches),
        )

    digest = certificate_digest(certificate)
    replay = verify_exact_result_replay(
        certificate,
        caps=caps.replay_caps(),
        expected_sha256=digest,
    )
    if replay.status is ReplayStatus.UNKNOWN_RESOURCE_CAP:
        return _outcome(
            ProductionAdmissionStatus.UNKNOWN_RESOURCE_CAP,
            f"independent replay exceeded a declared cap: {replay.reason}",
            preflight=preflight,
            producer_invoked=True,
            producer=producer,
            replay=replay,
            recurrence_status=recurrence.status,
            recurrence_certified=True,
            digest=digest,
            claimed_match_count=len(claimed_matches),
        )
    if replay.status is not ReplayStatus.VERIFIED_EXACT:
        return _outcome(
            ProductionAdmissionStatus.REJECTED_REPLAY,
            f"independent exact-result replay rejected the producer: {replay.reason}",
            preflight=preflight,
            producer_invoked=True,
            producer=producer,
            replay=replay,
            recurrence_status=recurrence.status,
            recurrence_certified=True,
            digest=digest,
            claimed_match_count=len(claimed_matches),
        )
    if producer.coset is not None and replay.target_stabilizer_size != producer.coset.subgroup.order:
        return _outcome(
            ProductionAdmissionStatus.REJECTED_REPLAY,
            "replayed target stabilizer order differs from the producer coset subgroup order",
            preflight=preflight,
            producer_invoked=True,
            producer=producer,
            replay=replay,
            recurrence_status=recurrence.status,
            recurrence_certified=True,
            digest=digest,
            claimed_match_count=len(claimed_matches),
        )

    return _outcome(
        ProductionAdmissionStatus.ADMITTED_EXACT,
        "small-order producer proof, recurrence leaf, independent group enumeration, and complete replay all agree",
        preflight=preflight,
        producer_invoked=True,
        producer=producer,
        replay=replay,
        recurrence_status=recurrence.status,
        recurrence_certified=True,
        digest=digest,
        claimed_match_count=len(claimed_matches),
    )


def run_proof_carrying_small_order_production_admission(
    group,
    source_values: Sequence[Any],
    target_values: Sequence[Any],
    *,
    root_n: int | None = None,
    group_order_poly_power: int = 2,
    caps: ProductionAdmissionCaps = ProductionAdmissionCaps(),
) -> SmallOrderProductionAdmission:
    """Production entry point: snapshot, preflight, execute once, then replay."""

    preflight = preflight_small_order_production_admission(
        group,
        source_values,
        target_values,
        root_n=root_n,
        group_order_poly_power=group_order_poly_power,
        caps=caps,
    )
    if not preflight.admitted:
        return _outcome(
            ProductionAdmissionStatus.UNKNOWN_RESOURCE_CAP,
            preflight.reason,
            preflight=preflight,
            producer_invoked=False,
        )

    # Snapshot before invoking the producer so later caller mutation cannot change
    # either the producer execution or the independent replay evidence.
    try:
        source = tuple(deepcopy(tuple(source_values)))
        target = tuple(deepcopy(tuple(target_values)))
        build_certificate(
            source=source,
            target=target,
            candidate_group=(identity(preflight.degree),),
            claimed_matches=(),
            universe_label="rev252-input-snapshot-probe",
            solver_status="exact",
        )
    except (CertificateBuildError, TypeError, ValueError, RecursionError) as exc:
        return _outcome(
            ProductionAdmissionStatus.REJECTED_INPUT,
            f"production input cannot be snapshotted deterministically: {exc}",
            preflight=preflight,
            producer_invoked=False,
        )

    producer = exact_small_order_group_string_isomorphism(
        group,
        source,
        target,
        root_n=preflight.root_n,
        group_order_poly_power=group_order_poly_power,
        max_group_order=caps.max_group_order,
    )
    return verify_small_order_production_result(
        group,
        source,
        target,
        producer,
        root_n=preflight.root_n,
        group_order_poly_power=group_order_poly_power,
        caps=caps,
        preflight=preflight,
    )
