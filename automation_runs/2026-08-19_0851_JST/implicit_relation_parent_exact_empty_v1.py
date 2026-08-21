from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from bounded_arity_relation_image_solver import BoundedArityRelationImage
from implicit_relation_image_action_v1 import ImplicitRelationImageAction


@dataclass(frozen=True)
class ImplicitRelationParentExactEmpty:
    status: str
    exact: bool
    complete: bool
    domain_degree: int
    auxiliary_degree: int
    reserved_feature_checks: int
    source_inventory_classes: int
    target_inventory_classes: int
    mismatched_inventory_classes: int
    domain_order: int
    image_order: int
    kernel_order: int
    reason: str


def _result(
    status: str,
    *,
    exact: bool,
    complete: bool,
    degree: int,
    auxiliary_degree: int,
    checks: int,
    source_classes: int = 0,
    target_classes: int = 0,
    mismatched_classes: int = 0,
    domain_order: int = 0,
    image_order: int = 0,
    kernel_order: int = 0,
    reason: str,
) -> ImplicitRelationParentExactEmpty:
    return ImplicitRelationParentExactEmpty(
        status,
        exact,
        complete,
        degree,
        auxiliary_degree,
        checks,
        source_classes,
        target_classes,
        mismatched_classes,
        domain_order,
        image_order,
        kernel_order,
        reason,
    )


def _relation_signature(
    image: BoundedArityRelationImage,
) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((relation.name, relation.arity) for relation in image.relations))


def _expected_auxiliary_degree(
    degree: int,
    signature: tuple[tuple[str, int], ...],
) -> int:
    return degree + sum(
        degree if arity == 1 else degree * degree
        for _name, arity in signature
    )


def _canonical_feature_string(
    image: BoundedArityRelationImage,
) -> tuple[object, ...]:
    """Independently replay the faithful named unary/binary incidence string."""
    degree = len(image.domain)
    index = {value: point for point, value in enumerate(image.domain)}
    features: list[object] = [("point", False)] * degree
    for relation in sorted(image.relations, key=lambda item: item.name):
        indexed = {
            tuple(index[value] for value in relation_tuple)
            for relation_tuple in relation.tuples
        }
        if relation.arity == 1:
            features.extend(
                (relation.name, (point,) in indexed)
                for point in range(degree)
            )
        else:
            features.extend(
                (relation.name, (left, right) in indexed)
                for left in range(degree)
                for right in range(degree)
            )
    return tuple(features)


def verify_exact_empty_relation_parent(
    source: BoundedArityRelationImage,
    target: BoundedArityRelationImage,
    action: ImplicitRelationImageAction,
    *,
    max_feature_checks: int = 1_000_000,
) -> ImplicitRelationParentExactEmpty:
    """Independently promote only mechanically proved exact-empty parent cases.

    This verifier is deliberately narrower than the active nonempty parent
    promotion path. It never constructs a value-preserving image coset and it
    never constructs an original-domain preimage.

    It can certify exact emptiness in three situations: different domain sizes,
    different named unary/binary signatures, or a mismatch between the complete
    auxiliary feature inventories of an exact faithful implicit relation action.

    Equal feature inventories are intentionally not promoted: the implicit
    image group may still contain no transporter. That stronger orbit/coset
    obstruction remains the separate value-coset child.
    """
    if not isinstance(source, BoundedArityRelationImage) or not isinstance(
        target, BoundedArityRelationImage
    ):
        raise TypeError("source and target must be BoundedArityRelationImage values")
    if not isinstance(action, ImplicitRelationImageAction):
        raise TypeError("action must be an ImplicitRelationImageAction")
    if (
        isinstance(max_feature_checks, bool)
        or not isinstance(max_feature_checks, int)
        or max_feature_checks < 1
    ):
        raise ValueError("max_feature_checks must be a positive integer")

    degree = len(source.domain)
    if len(target.domain) != degree:
        return _result(
            "exact_empty_parent_domain_size_mismatch",
            exact=True,
            complete=True,
            degree=degree,
            auxiliary_degree=0,
            checks=0,
            reason=(
                "independent source/target domain-size replay proves that no "
                "original-domain bijection can exist"
            ),
        )

    signature = _relation_signature(source)
    if _relation_signature(target) != signature:
        return _result(
            "exact_empty_parent_relation_signature_mismatch",
            exact=True,
            complete=True,
            degree=degree,
            auxiliary_degree=0,
            checks=0,
            reason=(
                "independent named unary/binary signature replay proves that "
                "no relation transporter can exist"
            ),
        )

    auxiliary_degree = _expected_auxiliary_degree(degree, signature)
    feature_checks = 2 * auxiliary_degree
    if feature_checks > max_feature_checks:
        return _result(
            "undetermined_parent_feature_scan_cap",
            exact=False,
            complete=False,
            degree=degree,
            auxiliary_degree=auxiliary_degree,
            checks=feature_checks,
            reason=(
                "independent source/target feature replay exceeds the preflight "
                "feature-check cap"
            ),
        )

    if action.status != "exact_implicit_relation_image_paired_action":
        return _result(
            "fail_closed_upstream_implicit_action_status",
            exact=False,
            complete=False,
            degree=degree,
            auxiliary_degree=auxiliary_degree,
            checks=feature_checks,
            reason=(
                "feature-inventory promotion requires the exact faithful "
                "implicit relation-image action"
            ),
        )

    if action.domain_group is None or action.image_group is None or action.kernel is None:
        return _result(
            "fail_closed_incomplete_implicit_action",
            exact=False,
            complete=False,
            degree=degree,
            auxiliary_degree=auxiliary_degree,
            checks=feature_checks,
            reason=(
                "exact implicit action status omitted its certified domain, "
                "image, or kernel group"
            ),
        )

    domain_order = action.domain_group.order
    image_order = action.image_group.order
    kernel_order = action.kernel.order

    if (
        action.domain_degree != degree
        or action.domain_group.degree != degree
        or action.kernel.degree != degree
        or action.auxiliary_degree != auxiliary_degree
        or action.image_group.degree != auxiliary_degree
    ):
        return _result(
            "fail_closed_implicit_action_degree_mismatch",
            exact=False,
            complete=False,
            degree=degree,
            auxiliary_degree=auxiliary_degree,
            checks=feature_checks,
            domain_order=domain_order,
            image_order=image_order,
            kernel_order=kernel_order,
            reason=(
                "stored implicit action degrees disagree with the independently "
                "reconstructed relation-image degrees"
            ),
        )

    if kernel_order * image_order != domain_order:
        return _result(
            "fail_closed_implicit_action_order_identity",
            exact=False,
            complete=False,
            degree=degree,
            auxiliary_degree=auxiliary_degree,
            checks=feature_checks,
            domain_order=domain_order,
            image_order=image_order,
            kernel_order=kernel_order,
            reason="stored implicit action violates |G| = |ker| * |im|",
        )
    if kernel_order != 1 or image_order != domain_order:
        return _result(
            "fail_closed_implicit_action_not_faithful",
            exact=False,
            complete=False,
            degree=degree,
            auxiliary_degree=auxiliary_degree,
            checks=feature_checks,
            domain_order=domain_order,
            image_order=image_order,
            kernel_order=kernel_order,
            reason=(
                "exact-empty parent promotion requires the faithful neutral-layer "
                "relation action certified by rev257"
            ),
        )

    expected_source = _canonical_feature_string(source)
    expected_target = _canonical_feature_string(target)
    if len(expected_source) != auxiliary_degree or len(expected_target) != auxiliary_degree:
        raise AssertionError("independent feature replay disagrees with computed auxiliary degree")

    if tuple(action.source_features) != expected_source or tuple(action.target_features) != expected_target:
        return _result(
            "fail_closed_implicit_action_feature_mismatch",
            exact=False,
            complete=False,
            degree=degree,
            auxiliary_degree=auxiliary_degree,
            checks=feature_checks,
            domain_order=domain_order,
            image_order=image_order,
            kernel_order=kernel_order,
            reason=(
                "stored implicit action feature strings disagree with an "
                "independent reconstruction from the named relations"
            ),
        )

    source_inventory = Counter(expected_source)
    target_inventory = Counter(expected_target)
    inventory_keys = set(source_inventory) | set(target_inventory)
    mismatch_count = sum(
        source_inventory[value] != target_inventory[value]
        for value in inventory_keys
    )
    common = dict(
        degree=degree,
        auxiliary_degree=auxiliary_degree,
        checks=feature_checks,
        source_classes=len(source_inventory),
        target_classes=len(target_inventory),
        mismatched_classes=mismatch_count,
        domain_order=domain_order,
        image_order=image_order,
        kernel_order=kernel_order,
    )

    if source_inventory != target_inventory:
        return _result(
            "exact_empty_parent_feature_inventory_mismatch",
            exact=True,
            complete=True,
            reason=(
                "the independently reconstructed complete auxiliary feature "
                "inventories differ; no auxiliary permutation, hence no faithful "
                "original-domain relation transporter, can map source to target"
            ),
            **common,
        )

    return _result(
        "undetermined_parent_feature_inventory_compatible",
        exact=False,
        complete=False,
        reason=(
            "feature inventories agree; exact emptiness now requires the separate "
            "implicit image-group value-coset orbit obstruction or a stronger child"
        ),
        **common,
    )


__all__ = [
    "ImplicitRelationParentExactEmpty",
    "verify_exact_empty_relation_parent",
]
