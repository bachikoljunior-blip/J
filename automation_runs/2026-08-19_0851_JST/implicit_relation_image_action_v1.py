from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from block_action_preimage_coset_v1 import _paired_chain
from bounded_arity_relation_image_solver import BoundedArityRelationImage
from bounded_relation_image_coset_v1 import (
    _feature_string,
    _induced_permutation,
    _relation_signature,
)
from permutation_group_schreier import (
    Permutation,
    StabilizerChain,
    identity,
    schreier_stabilizer_chain,
    validate_perm,
)


@dataclass(frozen=True)
class ImplicitRelationImageAction:
    status: str
    domain_degree: int
    auxiliary_degree: int
    generator_count: int
    action_point_checks: int
    source_features: tuple[object, ...]
    target_features: tuple[object, ...]
    domain_group: Optional[StabilizerChain]
    image_group: Optional[StabilizerChain]
    kernel: Optional[StabilizerChain]
    image_generators: tuple[Permutation, ...]
    paired_levels: tuple
    reason: str


def _closed(
    status: str,
    *,
    degree: int,
    auxiliary_degree: int,
    generator_count: int,
    checks: int,
    reason: str,
) -> ImplicitRelationImageAction:
    return ImplicitRelationImageAction(
        status,
        degree,
        auxiliary_degree,
        generator_count,
        checks,
        (),
        (),
        None,
        None,
        None,
        (),
        (),
        reason,
    )


def prepare_implicit_relation_image_action(
    source: BoundedArityRelationImage,
    target: BoundedArityRelationImage,
    domain_generators: Iterable[Iterable[int]],
    *,
    max_auxiliary_degree: int = 100_000,
    max_generators: int = 10_000,
    max_action_point_checks: int = 10_000_000,
) -> ImplicitRelationImageAction:
    """Build a faithful generator-paired action without enumerating the group.

    The auxiliary action is rev256's neutral point layer followed by every named
    unary/binary tuple slot.  The neutral layer makes the action faithful.  A
    paired Schreier chain independently certifies the homomorphism image and its
    kernel, including ``|G| = |ker| |im|``.  Resource caps are checked before the
    first induced auxiliary generator is materialized.

    This artifact deliberately stops before relation-string coset intersection.
    It solves only rev257 child (1); completeness and quasipolynomial accounting
    for the later transporter search remain separate obligations.
    """

    if not isinstance(source, BoundedArityRelationImage) or not isinstance(
        target, BoundedArityRelationImage
    ):
        raise TypeError("source and target must be BoundedArityRelationImage values")
    for name, value in (
        ("max_auxiliary_degree", max_auxiliary_degree),
        ("max_generators", max_generators),
        ("max_action_point_checks", max_action_point_checks),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")

    degree = len(source.domain)
    if len(target.domain) != degree:
        return _closed(
            "exact_empty_domain_size_mismatch",
            degree=degree,
            auxiliary_degree=0,
            generator_count=0,
            checks=0,
            reason="different finite domain sizes imply exact empty relation transport",
        )
    signature = _relation_signature(source)
    if _relation_signature(target) != signature:
        return _closed(
            "exact_empty_relation_signature_mismatch",
            degree=degree,
            auxiliary_degree=0,
            generator_count=0,
            checks=0,
            reason="different named unary/binary signatures imply exact empty relation transport",
        )

    raw_generators = tuple(validate_perm(g) for g in domain_generators)
    if not raw_generators:
        raise ValueError("at least one domain generator is required; use identity for the trivial group")
    if any(len(g) != degree for g in raw_generators):
        raise ValueError("domain generator degree mismatch")

    source_features = _feature_string(source)
    target_features = _feature_string(target)
    auxiliary_degree = len(source_features)
    if len(target_features) != auxiliary_degree:
        raise AssertionError("equal relation signatures produced unequal auxiliary degrees")
    generator_count = len(raw_generators)
    checks = generator_count * auxiliary_degree
    if auxiliary_degree > max_auxiliary_degree:
        return _closed(
            "undetermined_auxiliary_degree_cap",
            degree=degree,
            auxiliary_degree=auxiliary_degree,
            generator_count=generator_count,
            checks=checks,
            reason="faithful relation-image degree exceeds its pre-materialization cap",
        )
    if generator_count > max_generators:
        return _closed(
            "undetermined_generator_count_cap",
            degree=degree,
            auxiliary_degree=auxiliary_degree,
            generator_count=generator_count,
            checks=checks,
            reason="domain generator count exceeds its pre-materialization cap",
        )
    if checks > max_action_point_checks:
        return _closed(
            "undetermined_action_point_check_cap",
            degree=degree,
            auxiliary_degree=auxiliary_degree,
            generator_count=generator_count,
            checks=checks,
            reason="all generator/action-point images do not fit the finite preflight budget",
        )

    domain_group = schreier_stabilizer_chain(raw_generators)
    domain_gens = domain_group.original_generators or (identity(degree),)
    image_gens = tuple(
        _induced_permutation(generator, signature, degree)
        for generator in domain_gens
    )
    image_identity = identity(auxiliary_degree)
    image_group = schreier_stabilizer_chain(image_gens or (image_identity,))
    levels, kernel_gens = _paired_chain(domain_gens, image_gens)
    domain_identity = identity(degree)
    kernel = schreier_stabilizer_chain(kernel_gens or (domain_identity,))

    if kernel.order * image_group.order != domain_group.order:
        raise AssertionError("paired relation-image chain violates |G|=|ker|*|im|")
    for generator in kernel.original_generators or (domain_identity,):
        if _induced_permutation(generator, signature, degree) != image_identity:
            raise AssertionError("paired-chain kernel generator has nontrivial auxiliary image")
    if kernel.order != 1 or image_group.order != domain_group.order:
        raise AssertionError("neutral point layer failed to make the auxiliary action faithful")

    return ImplicitRelationImageAction(
        "exact_implicit_relation_image_paired_action",
        degree,
        auxiliary_degree,
        generator_count,
        checks,
        source_features,
        target_features,
        domain_group,
        image_group,
        kernel,
        image_gens,
        levels,
        "all supplied generators were lifted to a faithful unary/binary incidence action; paired Schreier replay certifies the exact image and trivial kernel without group enumeration",
    )
