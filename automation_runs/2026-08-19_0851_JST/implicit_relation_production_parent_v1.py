from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional


RESOURCE_STATUS = "certified_implicit_relation_image_work_bound"
IMAGE_NONEMPTY_STATUS = "exact_implicit_relation_image_value_coset"
PREIMAGE_NONEMPTY_STATUS = "exact_original_domain_relation_preimage_coset"
PREIMAGE_EMPTY_STATUS = "exact_empty_original_domain_relation_preimage"
PARENT_NONEMPTY_STATUS = "exact_implicit_relation_parent_coset"
PARENT_EMPTY_STATUSES = frozenset(
    {
        "exact_empty_parent_domain_size_mismatch",
        "exact_empty_parent_relation_signature_mismatch",
        "exact_empty_parent_feature_inventory_mismatch",
    }
)
PREFLIGHT_INCONCLUSIVE_STATUS = "inconclusive_no_structural_exact_empty_obstruction"
NORMALIZED_NONEMPTY_STATUS = "exact_parent_outcome_nonempty"
NORMALIZED_EMPTY_STATUS = "exact_parent_outcome_empty"
_REQUIRED_PHASES = (
    "induced_action",
    "domain_schreier",
    "image_schreier",
    "value_coset_intersection",
    "paired_preimage",
    "verification",
)
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ImplicitRelationProductionParentResult:
    status: str
    exact: bool
    complete: bool
    outcome_kind: str
    original_root_degree: int
    domain_degree: int
    auxiliary_degree: int
    reserved_work_upper_bound: int
    parent_coset: Optional[object]
    normalized_outcome: Optional[object]
    executed_steps: tuple[str, ...]
    reason: str


def _nonnegative_int(value: object) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _positive_int(value: object) -> Optional[int]:
    parsed = _nonnegative_int(value)
    return parsed if parsed is not None and parsed > 0 else None


def _closed(
    status: str,
    *,
    root: int = 0,
    domain: int = 0,
    auxiliary: int = 0,
    work: int = 0,
    steps: tuple[str, ...] = (),
    reason: str,
) -> ImplicitRelationProductionParentResult:
    return ImplicitRelationProductionParentResult(
        status=status,
        exact=False,
        complete=False,
        outcome_kind="undetermined",
        original_root_degree=root,
        domain_degree=domain,
        auxiliary_degree=auxiliary,
        reserved_work_upper_bound=work,
        parent_coset=None,
        normalized_outcome=None,
        executed_steps=steps,
        reason=reason,
    )


def _resource_contract(envelope: object) -> tuple[bool, int, int, int, int, str]:
    status = getattr(envelope, "status", None)
    admitted = getattr(envelope, "admitted", None)
    complete = getattr(envelope, "complete", None)
    root_lift = getattr(envelope, "root_lift_certified", None)
    order_compatible = getattr(envelope, "order_bounds_compatible", None)
    image_gate = getattr(envelope, "image_gate_certified", None)
    root = _positive_int(getattr(envelope, "original_root_degree", None))
    domain = _positive_int(getattr(envelope, "domain_degree", None))
    auxiliary = _positive_int(getattr(envelope, "auxiliary_degree", None))
    work = _nonnegative_int(getattr(envelope, "work_upper_bound", None))
    max_work = _positive_int(getattr(envelope, "max_work", None))

    if (
        status != RESOURCE_STATUS
        or admitted is not True
        or complete is not False
        or root_lift is not True
        or order_compatible is not True
        or image_gate is not True
        or root is None
        or domain is None
        or auxiliary is None
        or work is None
        or max_work is None
        or work > max_work
    ):
        return False, root or 0, domain or 0, auxiliary or 0, work or 0, (
            "rev265 resource evidence is not an admitted complete-attempt envelope"
        )

    try:
        phases = tuple(getattr(envelope, "phase_work_upper_bounds"))
    except (AttributeError, TypeError):
        return False, root, domain, auxiliary, work, (
            "rev265 resource evidence omitted its immutable phase reservation split"
        )
    if len(phases) != len(_REQUIRED_PHASES):
        return False, root, domain, auxiliary, work, (
            "rev265 resource evidence has the wrong phase reservation arity"
        )
    names: list[str] = []
    reserved_total = 0
    for entry in phases:
        if not isinstance(entry, tuple) or len(entry) != 2:
            return False, root, domain, auxiliary, work, (
                "rev265 phase reservation entry is malformed"
            )
        name, bound = entry
        parsed = _nonnegative_int(bound)
        if not isinstance(name, str) or parsed is None:
            return False, root, domain, auxiliary, work, (
                "rev265 phase reservation entry has an invalid name or bound"
            )
        names.append(name)
        reserved_total += parsed
    if tuple(names) != _REQUIRED_PHASES or reserved_total != work:
        return False, root, domain, auxiliary, work, (
            "rev265 phase reservations do not exactly reconstruct the admitted work bound"
        )
    return True, root, domain, auxiliary, work, ""


def _same_degrees(value: object, domain: int, auxiliary: int) -> bool:
    return (
        _positive_int(getattr(value, "domain_degree", None)) == domain
        and _positive_int(getattr(value, "auxiliary_degree", None)) == auxiliary
    )


def _exact_complete(value: object) -> bool:
    return getattr(value, "exact", None) is True and getattr(value, "complete", None) is True


def _call(step: str, callback: Callable[..., object], *args: object) -> tuple[bool, object]:
    try:
        return True, callback(*args)
    except Exception as exc:  # fail closed at the orchestration boundary
        return False, f"{step} raised {type(exc).__name__}"


def _normalized_contract(
    outcome: object,
    *,
    kind: str,
    domain: int,
    auxiliary: int,
    source_digest: str,
    target_digest: str,
) -> bool:
    if not _exact_complete(outcome):
        return False
    if _positive_int(getattr(outcome, "domain_degree", None)) != domain:
        return False
    normalized_auxiliary = _nonnegative_int(getattr(outcome, "auxiliary_degree", None))
    if normalized_auxiliary is None:
        return False
    if kind == "nonempty" and normalized_auxiliary != auxiliary:
        return False
    if kind == "exact_empty" and normalized_auxiliary not in (0, auxiliary):
        return False
    if getattr(outcome, "outcome_kind", None) != kind:
        return False
    expected_status = (
        NORMALIZED_NONEMPTY_STATUS if kind == "nonempty" else NORMALIZED_EMPTY_STATUS
    )
    expected_revision = 261 if kind == "nonempty" else 263
    return (
        getattr(outcome, "status", None) == expected_status
        and getattr(outcome, "source_evidence_revision", None) == expected_revision
        and getattr(outcome, "source_relation_digest", None) == source_digest
        and getattr(outcome, "target_relation_digest", None) == target_digest
    )


def _accepted_empty_preflight(
    evidence: object,
    *,
    domain: int,
    auxiliary: int,
) -> bool:
    status = getattr(evidence, "status", None)
    if status not in PARENT_EMPTY_STATUSES or not _exact_complete(evidence):
        return False
    if _positive_int(getattr(evidence, "domain_degree", None)) != domain:
        return False
    evidence_auxiliary = _nonnegative_int(getattr(evidence, "auxiliary_degree", None))
    if status in {
        "exact_empty_parent_domain_size_mismatch",
        "exact_empty_parent_relation_signature_mismatch",
    }:
        return evidence_auxiliary == 0
    return evidence_auxiliary == auxiliary


def _accepted_inconclusive_preflight(
    evidence: object,
    *,
    domain: int,
    auxiliary: int,
) -> bool:
    return (
        getattr(evidence, "status", None) == PREFLIGHT_INCONCLUSIVE_STATUS
        and getattr(evidence, "exact", None) is False
        and getattr(evidence, "complete", None) is False
        and _positive_int(getattr(evidence, "domain_degree", None)) == domain
        and _positive_int(getattr(evidence, "auxiliary_degree", None)) == auxiliary
    )


def exact_implicit_relation_production_parent(
    resource_envelope: object,
    *,
    expected_source_relation_digest: str,
    expected_target_relation_digest: str,
    exact_empty_parent_preflight: Callable[[], object],
    image_solver: Callable[[], object],
    preimage_solver: Callable[[object], object],
    nonempty_parent_verifier: Callable[[object], object],
    parent_outcome_normalizer: Callable[[object], object],
) -> ImplicitRelationProductionParentResult:
    """Compose exact implicit-relation descendants behind one fail-closed parent.

    Sibling implementations remain independently owned, so this module accepts
    them as callables instead of importing branch-only modules.  The caller
    closes over the concrete rev263/rev262/rev267/rev261/rev266 descendants and
    this function enforces ordering, exact-result contracts, relation identity,
    and the rev265 original-root reservation before promotion.

    Structurally certified empty route:
      rev265 admission -> rev263 preflight -> rev266 normalized outcome.

    Nonempty route:
      rev265 admission -> rev263 inconclusive preflight -> rev262 image coset ->
      rev267 original preimage -> rev261 semantic parent verifier ->
      rev266 normalized outcome.

    A rev262 exact-empty image is propagated through rev267, but is deliberately
    left undetermined at the parent boundary: current rev263/rev266 contracts do
    not accept image/preimage emptiness as semantic parent-empty evidence.  That
    missing bridge remains a separate leaf rather than being silently assumed.
    """
    if not isinstance(expected_source_relation_digest, str) or _SHA256_RE.fullmatch(
        expected_source_relation_digest
    ) is None:
        raise ValueError("expected_source_relation_digest must be sha256:<64 lowercase hex>")
    if not isinstance(expected_target_relation_digest, str) or _SHA256_RE.fullmatch(
        expected_target_relation_digest
    ) is None:
        raise ValueError("expected_target_relation_digest must be sha256:<64 lowercase hex>")
    for callback, name in (
        (exact_empty_parent_preflight, "exact_empty_parent_preflight"),
        (image_solver, "image_solver"),
        (preimage_solver, "preimage_solver"),
        (nonempty_parent_verifier, "nonempty_parent_verifier"),
        (parent_outcome_normalizer, "parent_outcome_normalizer"),
    ):
        if not callable(callback):
            raise TypeError(f"{name} must be callable")

    admitted, root, domain, auxiliary, work, reason = _resource_contract(resource_envelope)
    if not admitted:
        return _closed(
            "fail_closed_unadmitted_original_root_resource_envelope",
            root=root,
            domain=domain,
            auxiliary=auxiliary,
            work=work,
            reason=reason,
        )

    steps: list[str] = []
    ok, preflight = _call(
        "rev263 exact-empty parent preflight", exact_empty_parent_preflight
    )
    steps.append("structural_exact_empty_preflight")
    if not ok:
        return _closed(
            "fail_closed_exact_empty_parent_preflight_exception",
            root=root,
            domain=domain,
            auxiliary=auxiliary,
            work=work,
            steps=tuple(steps),
            reason=str(preflight),
        )

    if getattr(preflight, "status", None) in PARENT_EMPTY_STATUSES:
        if not _accepted_empty_preflight(preflight, domain=domain, auxiliary=auxiliary):
            return _closed(
                "fail_closed_exact_empty_parent_preflight_contract",
                root=root,
                domain=domain,
                auxiliary=auxiliary,
                work=work,
                steps=tuple(steps),
                reason="rev263 structural exact-empty evidence does not match the admitted parent degrees",
            )
        ok, normalized = _call(
            "rev266 parent outcome normalizer", parent_outcome_normalizer, preflight
        )
        steps.append("parent_outcome_normalization")
        if not ok:
            return _closed(
                "fail_closed_parent_outcome_normalizer_exception",
                root=root,
                domain=domain,
                auxiliary=auxiliary,
                work=work,
                steps=tuple(steps),
                reason=str(normalized),
            )
        if not _normalized_contract(
            normalized,
            kind="exact_empty",
            domain=domain,
            auxiliary=auxiliary,
            source_digest=expected_source_relation_digest,
            target_digest=expected_target_relation_digest,
        ):
            return _closed(
                "fail_closed_normalized_exact_empty_contract",
                root=root,
                domain=domain,
                auxiliary=auxiliary,
                work=work,
                steps=tuple(steps),
                reason="rev266 normalized outcome does not bind the requested rev263 exact-empty parent context",
            )
        return ImplicitRelationProductionParentResult(
            status="exact_implicit_relation_production_parent_empty",
            exact=True,
            complete=True,
            outcome_kind="exact_empty",
            original_root_degree=root,
            domain_degree=domain,
            auxiliary_degree=auxiliary,
            reserved_work_upper_bound=work,
            parent_coset=None,
            normalized_outcome=normalized,
            executed_steps=tuple(steps),
            reason="rev265 admission and the rev263->rev266 structural exact-empty route agree on one complete parent-empty outcome",
        )

    if not _accepted_inconclusive_preflight(
        preflight, domain=domain, auxiliary=auxiliary
    ):
        return _closed(
            "fail_closed_exact_empty_parent_preflight_contract",
            root=root,
            domain=domain,
            auxiliary=auxiliary,
            work=work,
            steps=tuple(steps),
            reason="rev263 returned neither accepted exact-empty evidence nor its exact inconclusive continuation contract",
        )

    ok, image_result = _call("rev262 image solver", image_solver)
    steps.append("value_coset_intersection")
    if not ok:
        return _closed(
            "fail_closed_image_solver_exception",
            root=root,
            domain=domain,
            auxiliary=auxiliary,
            work=work,
            steps=tuple(steps),
            reason=str(image_result),
        )
    if not _exact_complete(image_result):
        return _closed(
            "fail_closed_image_result_not_exact_complete",
            root=root,
            domain=domain,
            auxiliary=auxiliary,
            work=work,
            steps=tuple(steps),
            reason="rev262 image result is not exact and complete",
        )
    if _positive_int(getattr(image_result, "auxiliary_degree", None)) != auxiliary:
        return _closed(
            "fail_closed_image_result_degree_mismatch",
            root=root,
            domain=domain,
            auxiliary=auxiliary,
            work=work,
            steps=tuple(steps),
            reason="rev262 image result is bound to a different auxiliary degree",
        )

    image_status = getattr(image_result, "status", None)
    image_coset = getattr(image_result, "coset", None)
    if isinstance(image_status, str) and image_status.startswith("exact_empty_"):
        if image_coset is not None:
            return _closed(
                "fail_closed_exact_empty_image_carried_coset",
                root=root,
                domain=domain,
                auxiliary=auxiliary,
                work=work,
                steps=tuple(steps),
                reason="an exact-empty image result must not carry a right coset",
            )
        ok, empty_preimage = _call(
            "rev267 original-domain exact-empty preimage", preimage_solver, image_result
        )
        steps.append("paired_preimage")
        if not ok:
            return _closed(
                "fail_closed_preimage_solver_exception",
                root=root,
                domain=domain,
                auxiliary=auxiliary,
                work=work,
                steps=tuple(steps),
                reason=str(empty_preimage),
            )
        if (
            not _exact_complete(empty_preimage)
            or not _same_degrees(empty_preimage, domain, auxiliary)
            or getattr(empty_preimage, "status", None) != PREIMAGE_EMPTY_STATUS
            or getattr(empty_preimage, "coset", None) is not None
        ):
            return _closed(
                "fail_closed_original_domain_exact_empty_preimage_contract",
                root=root,
                domain=domain,
                auxiliary=auxiliary,
                work=work,
                steps=tuple(steps),
                reason="rev267 did not preserve rev262 exact emptiness as a complete original-domain preimage result",
            )
        return _closed(
            "undetermined_exact_empty_image_parent_semantic_bridge",
            root=root,
            domain=domain,
            auxiliary=auxiliary,
            work=work,
            steps=tuple(steps),
            reason=(
                "rev262 and rev267 certify image/original-domain emptiness, but current "
                "rev263/rev266 parent semantics do not certify that obstruction as an "
                "exact parent-empty outcome"
            ),
        )

    if image_status != IMAGE_NONEMPTY_STATUS or image_coset is None:
        return _closed(
            "fail_closed_image_result_contract",
            root=root,
            domain=domain,
            auxiliary=auxiliary,
            work=work,
            steps=tuple(steps),
            reason="rev262 returned neither its accepted nonempty image coset nor an exact-empty result",
        )

    ok, preimage = _call("rev267 original-domain preimage", preimage_solver, image_result)
    steps.append("paired_preimage")
    if not ok:
        return _closed(
            "fail_closed_preimage_solver_exception",
            root=root,
            domain=domain,
            auxiliary=auxiliary,
            work=work,
            steps=tuple(steps),
            reason=str(preimage),
        )
    if (
        not _exact_complete(preimage)
        or not _same_degrees(preimage, domain, auxiliary)
        or getattr(preimage, "status", None) != PREIMAGE_NONEMPTY_STATUS
        or getattr(preimage, "coset", None) is None
    ):
        return _closed(
            "fail_closed_original_domain_preimage_contract",
            root=root,
            domain=domain,
            auxiliary=auxiliary,
            work=work,
            steps=tuple(steps),
            reason="rev267 did not return the accepted complete original-domain preimage coset",
        )

    ok, promotion = _call("rev261 nonempty parent verifier", nonempty_parent_verifier, preimage)
    steps.append("nonempty_parent_verification")
    if not ok:
        return _closed(
            "fail_closed_nonempty_parent_verifier_exception",
            root=root,
            domain=domain,
            auxiliary=auxiliary,
            work=work,
            steps=tuple(steps),
            reason=str(promotion),
        )
    if (
        not _exact_complete(promotion)
        or not _same_degrees(promotion, domain, auxiliary)
        or getattr(promotion, "status", None) != PARENT_NONEMPTY_STATUS
        or getattr(promotion, "coset", None) is None
    ):
        return _closed(
            "fail_closed_nonempty_parent_evidence_contract",
            root=root,
            domain=domain,
            auxiliary=auxiliary,
            work=work,
            steps=tuple(steps),
            reason="rev261 did not return the accepted complete parent right coset",
        )

    ok, normalized = _call(
        "rev266 parent outcome normalizer", parent_outcome_normalizer, promotion
    )
    steps.append("parent_outcome_normalization")
    if not ok:
        return _closed(
            "fail_closed_parent_outcome_normalizer_exception",
            root=root,
            domain=domain,
            auxiliary=auxiliary,
            work=work,
            steps=tuple(steps),
            reason=str(normalized),
        )
    if not _normalized_contract(
        normalized,
        kind="nonempty",
        domain=domain,
        auxiliary=auxiliary,
        source_digest=expected_source_relation_digest,
        target_digest=expected_target_relation_digest,
    ):
        return _closed(
            "fail_closed_normalized_nonempty_contract",
            root=root,
            domain=domain,
            auxiliary=auxiliary,
            work=work,
            steps=tuple(steps),
            reason="rev266 normalized outcome does not bind the requested nonempty parent context",
        )

    return ImplicitRelationProductionParentResult(
        status="exact_implicit_relation_production_parent_coset",
        exact=True,
        complete=True,
        outcome_kind="nonempty",
        original_root_degree=root,
        domain_degree=domain,
        auxiliary_degree=auxiliary,
        reserved_work_upper_bound=work,
        parent_coset=getattr(promotion, "coset"),
        normalized_outcome=normalized,
        executed_steps=tuple(steps),
        reason="rev265 admission and the rev263->rev262->rev267->rev261->rev266 route agree on one complete exact parent right coset",
    )


__all__ = [
    "ImplicitRelationProductionParentResult",
    "exact_implicit_relation_production_parent",
]
