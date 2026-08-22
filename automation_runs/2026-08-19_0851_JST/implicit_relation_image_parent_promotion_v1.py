from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bounded_arity_relation_image_solver import BoundedArityRelationImage
from coset_stabilizer_primitives import RightCoset
from paired_action_coset_preimage_v1 import PairedActionCosetPreimage
from permutation_group_schreier import StabilizerChain, identity, validate_perm


@dataclass(frozen=True)
class ImplicitRelationParentPromotion:
    status: str
    exact: bool
    complete: bool
    domain_degree: int
    auxiliary_degree: int
    domain_order: int
    image_order: int
    kernel_order: int
    image_target_subgroup_order: int
    preimage_subgroup_order: int
    subgroup_generator_count: int
    reserved_membership_sifts: int
    reserved_relation_action_point_checks: int
    coset: Optional[RightCoset]
    reason: str


def _closed(
    status: str,
    *,
    degree: int,
    auxiliary_degree: int,
    domain_order: int,
    image_order: int,
    kernel_order: int,
    image_target_subgroup_order: int,
    preimage_subgroup_order: int,
    subgroup_generators: int,
    membership_sifts: int,
    relation_checks: int,
    reason: str,
) -> ImplicitRelationParentPromotion:
    return ImplicitRelationParentPromotion(
        status,
        False,
        False,
        degree,
        auxiliary_degree,
        domain_order,
        image_order,
        kernel_order,
        image_target_subgroup_order,
        preimage_subgroup_order,
        subgroup_generators,
        membership_sifts,
        relation_checks,
        None,
        reason,
    )


def _signature(image: BoundedArityRelationImage) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((relation.name, relation.arity) for relation in image.relations))


def _indexed_relations(
    image: BoundedArityRelationImage,
) -> dict[str, tuple[int, frozenset[tuple[int, ...]]]]:
    index = {value: point for point, value in enumerate(image.domain)}
    return {
        relation.name: (
            relation.arity,
            frozenset(
                tuple(index[value] for value in relation_tuple)
                for relation_tuple in relation.tuples
            ),
        )
        for relation in image.relations
    }


def _transports(
    source: dict[str, tuple[int, frozenset[tuple[int, ...]]]],
    target: dict[str, tuple[int, frozenset[tuple[int, ...]]]],
    permutation: tuple[int, ...],
) -> bool:
    for name, (arity, tuples) in source.items():
        target_arity, target_tuples = target[name]
        if target_arity != arity:
            return False
        transported = frozenset(
            tuple(permutation[point] for point in relation_tuple)
            for relation_tuple in tuples
        )
        if transported != target_tuples:
            return False
    return True


def promote_nonempty_exact_relation_preimage(
    source: BoundedArityRelationImage,
    target: BoundedArityRelationImage,
    domain_group: StabilizerChain,
    preimage: PairedActionCosetPreimage,
    *,
    max_membership_sifts: int = 100_000,
    max_relation_action_point_checks: int = 10_000_000,
) -> ImplicitRelationParentPromotion:
    """Fail-closed promotion gate for an already-certified nonempty preimage.

    This function deliberately does *not* construct the auxiliary image coset or
    lift it back to the original domain. Those are upstream obligations. It
    consumes one concrete ``PairedActionCosetPreimage`` artifact and independently
    checks the conditions needed to expose its nonempty right coset as a full
    named unary/binary relation transporter on the original domain:

    * the exact paired-preimage status and all stored order identities agree;
    * the artifact's image degree is exactly the faithful relation-action degree;
    * the artifact's coset, subgroup, representative, and stored fields agree;
    * representative and subgroup generators stay inside ``domain_group``;
    * the representative transports every named relation from source to target;
    * every returned subgroup generator stabilizes the complete target relation.

    Generator stabilization suffices for the whole target subgroup. Upstream
    completeness is not inferred from semantic transport checks: exact promotion
    is conditional on the exact paired-preimage artifact itself. Empty image
    intersections remain an upstream case and are intentionally outside this
    nonempty promotion gate.
    """
    if not isinstance(source, BoundedArityRelationImage) or not isinstance(
        target, BoundedArityRelationImage
    ):
        raise TypeError("source and target must be BoundedArityRelationImage values")
    if not isinstance(domain_group, StabilizerChain):
        raise TypeError("domain_group must be a StabilizerChain")
    if not isinstance(preimage, PairedActionCosetPreimage):
        raise TypeError("preimage must be a PairedActionCosetPreimage")
    for name, value in (
        ("max_membership_sifts", max_membership_sifts),
        ("max_relation_action_point_checks", max_relation_action_point_checks),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")

    degree = len(source.domain)
    domain_order = domain_group.order
    signature = _signature(source)
    auxiliary_degree = degree + sum(
        degree if arity == 1 else degree * degree for _name, arity in signature
    )

    candidate_coset = preimage.coset
    subgroup = candidate_coset.subgroup if candidate_coset is not None else None
    subgroup_generators = (
        tuple(subgroup.original_generators) or (identity(subgroup.degree),)
        if subgroup is not None
        else ()
    )
    generator_count = len(subgroup_generators)
    membership_sifts = 1 + generator_count if candidate_coset is not None else 0
    relation_checks = membership_sifts * auxiliary_degree

    common = dict(
        degree=degree,
        auxiliary_degree=auxiliary_degree,
        domain_order=domain_order,
        image_order=preimage.image_order,
        kernel_order=preimage.kernel_order,
        image_target_subgroup_order=preimage.target_subgroup_order,
        preimage_subgroup_order=preimage.preimage_subgroup_order,
        subgroup_generators=generator_count,
        membership_sifts=membership_sifts,
        relation_checks=relation_checks,
    )

    if preimage.status != "exact_paired_action_coset_preimage":
        return _closed(
            "fail_closed_upstream_preimage_status",
            reason="parent promotion requires the exact paired-preimage contract",
            **common,
        )
    if candidate_coset is None or preimage.preimage_subgroup is None or preimage.representative is None:
        return _closed(
            "fail_closed_incomplete_preimage_artifact",
            reason="exact paired-preimage status must carry subgroup, representative, and right coset",
            **common,
        )
    if len(target.domain) != degree:
        return _closed(
            "fail_closed_domain_size_mismatch",
            reason="a nonempty original-domain transporter cannot change domain degree",
            **common,
        )
    if _signature(target) != signature:
        return _closed(
            "fail_closed_relation_signature_mismatch",
            reason="a nonempty transporter cannot change the named unary/binary signature",
            **common,
        )
    if (
        domain_group.degree != degree
        or preimage.domain_degree != degree
        or subgroup.degree != degree
        or preimage.kernel.degree != degree
    ):
        return _closed(
            "fail_closed_group_degree_mismatch",
            reason="domain, paired-preimage, kernel, and returned subgroup degrees must agree",
            **common,
        )
    if preimage.image_degree != auxiliary_degree:
        return _closed(
            "fail_closed_auxiliary_degree_mismatch",
            reason="paired-preimage image degree is not the faithful named-relation auxiliary degree",
            **common,
        )

    representative = validate_perm(candidate_coset.representative)
    stored_representative = validate_perm(preimage.representative)
    if len(representative) != degree or len(stored_representative) != degree:
        return _closed(
            "fail_closed_representative_degree_mismatch",
            reason="returned preimage representative has the wrong original-domain degree",
            **common,
        )
    if representative != stored_representative:
        return _closed(
            "fail_closed_preimage_representative_mismatch",
            reason="stored paired-preimage representative disagrees with its returned right coset",
            **common,
        )
    if subgroup != preimage.preimage_subgroup:
        return _closed(
            "fail_closed_preimage_subgroup_mismatch",
            reason="stored paired-preimage subgroup disagrees with its returned right coset",
            **common,
        )

    if preimage.domain_order != domain_order:
        return _closed(
            "fail_closed_domain_order_mismatch",
            reason="paired-preimage domain order disagrees with the supplied certified domain group",
            **common,
        )
    if domain_order != preimage.kernel_order * preimage.image_order:
        return _closed(
            "fail_closed_domain_kernel_image_order",
            reason="stored paired evidence violates |G| = |ker| * |im|",
            **common,
        )
    if (
        preimage.target_subgroup_order > preimage.image_order
        or preimage.image_order % preimage.target_subgroup_order
    ):
        return _closed(
            "fail_closed_image_subgroup_order",
            reason="stored target image subgroup order is not a subgroup order of the image",
            **common,
        )
    if preimage.preimage_subgroup_order != preimage.kernel_order * preimage.target_subgroup_order:
        return _closed(
            "fail_closed_preimage_order_identity",
            reason="stored evidence violates |preimage subgroup| = |ker| * |image target subgroup|",
            **common,
        )
    if subgroup.order != preimage.preimage_subgroup_order:
        return _closed(
            "fail_closed_returned_subgroup_order",
            reason="returned original-domain subgroup order disagrees with paired-preimage evidence",
            **common,
        )

    if membership_sifts > max_membership_sifts:
        return _closed(
            "undetermined_parent_membership_sift_cap",
            reason="promotion membership checks exceed the preflight sift cap",
            **common,
        )
    if relation_checks > max_relation_action_point_checks:
        return _closed(
            "undetermined_parent_relation_action_cap",
            reason="promotion relation checks exceed the preflight action-point cap",
            **common,
        )

    if not domain_group.contains(representative):
        return _closed(
            "fail_closed_representative_outside_domain_group",
            reason="paired-preimage representative escaped the certified original-domain group",
            **common,
        )
    for generator in subgroup_generators:
        if not domain_group.contains(generator):
            return _closed(
                "fail_closed_subgroup_outside_domain_group",
                reason="paired-preimage subgroup generator escaped the certified original-domain group",
                **common,
            )

    source_relations = _indexed_relations(source)
    target_relations = _indexed_relations(target)
    if not _transports(source_relations, target_relations, representative):
        return _closed(
            "fail_closed_representative_not_full_relation_transporter",
            reason="returned representative does not transport the complete named relation image",
            **common,
        )
    for generator in subgroup_generators:
        if not _transports(target_relations, target_relations, generator):
            return _closed(
                "fail_closed_subgroup_not_target_relation_stabilizer",
                reason="returned preimage subgroup contains a generator that does not stabilize the target relation image",
                **common,
            )

    return ImplicitRelationParentPromotion(
        "exact_implicit_relation_parent_coset",
        True,
        True,
        degree,
        auxiliary_degree,
        domain_order,
        preimage.image_order,
        preimage.kernel_order,
        preimage.target_subgroup_order,
        preimage.preimage_subgroup_order,
        generator_count,
        membership_sifts,
        relation_checks,
        candidate_coset,
        "exact paired-preimage artifact consistency, original-domain containment, representative transport, and target-subgroup stabilization all verified",
    )
