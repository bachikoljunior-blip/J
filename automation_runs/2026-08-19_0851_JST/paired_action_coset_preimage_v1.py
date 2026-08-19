from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from block_action_preimage_coset_v1 import _paired_chain
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import (
    StabilizerChain,
    compose,
    identity,
    inverse,
    schreier_stabilizer_chain,
    validate_perm,
)


@dataclass(frozen=True)
class PairedActionCosetPreimage:
    status: str
    domain_degree: int
    image_degree: int
    domain_order: int
    image_order: int
    kernel_order: int
    target_subgroup_order: int
    preimage_subgroup_order: int
    sift_levels: int
    kernel: StabilizerChain
    preimage_subgroup: Optional[StabilizerChain]
    representative: tuple[int, ...] | None
    coset: Optional[RightCoset]
    reason: str


def _lift_image_element(target, levels, *, domain_degree, image_degree):
    target = validate_perm(target)
    if len(target) != image_degree:
        raise ValueError("target image element has wrong degree")
    eg = identity(domain_degree)
    eq = identity(image_degree)
    residual = target
    selected = []
    for base, raw_trans in levels:
        trans = dict(raw_trans)
        x = residual[base]
        if x not in trans:
            return None
        tg, tq = trans[x]
        selected.append(tg)
        residual = compose(residual, inverse(tq))
    if residual != eq:
        return None
    lifted = eg
    for tg in reversed(selected):
        lifted = compose(lifted, tg)
    return lifted


def paired_action_coset_preimage(
    group: StabilizerChain,
    image_generators,
    target_coset: RightCoset,
) -> PairedActionCosetPreimage:
    """Exact preimage of an image right coset under a generator-paired action.

    ``image_generators[i]`` must be the image of
    ``group.original_generators[i]`` under one homomorphism.  A paired Schreier
    chain proves that this generator pairing is a well-defined surjective map
    from ``group`` onto the generated image: its kernel/image orders must satisfy
    |G|=|ker|*|im|.  The same chain then lifts the target representative and each
    target-subgroup generator.  Kernel plus lifted target-subgroup generators
    generate exactly the subgroup preimage, so the returned RightCoset is the
    complete preimage of ``target_coset`` without enumerating either group.

    This is action-agnostic plumbing for block quotients, Johnson-ground actions,
    pair/higher-arity relational images, and later local-certificate image SI.
    """
    domain_gens = tuple(group.original_generators)
    if not domain_gens:
        domain_gens = (identity(group.degree),)
    images = tuple(validate_perm(q) for q in image_generators)
    if len(images) != len(domain_gens):
        raise ValueError("one image generator is required for every domain generator")
    if not images:
        raise ValueError("image generator list cannot be empty")
    image_degree = len(images[0])
    if any(len(q) != image_degree for q in images):
        raise ValueError("image generator degree mismatch")
    if target_coset.subgroup.degree != image_degree or len(target_coset.representative) != image_degree:
        raise ValueError("target coset has wrong image degree")

    image = schreier_stabilizer_chain(images)
    levels, kernel_gens = _paired_chain(domain_gens, images)
    eg = identity(group.degree)
    kernel = schreier_stabilizer_chain(kernel_gens or [eg])

    if kernel.order * image.order != group.order:
        raise ValueError(
            "paired generators do not certify a well-defined action homomorphism on the supplied domain group"
        )

    target_subgroup = target_coset.subgroup
    target_rep = validate_perm(target_coset.representative)
    image_identity = identity(image_degree)
    for q in target_subgroup.original_generators or (image_identity,):
        if not image.contains(q):
            return PairedActionCosetPreimage(
                "target_subgroup_outside_image",
                group.degree,
                image_degree,
                group.order,
                image.order,
                kernel.order,
                target_subgroup.order,
                0,
                len(levels),
                kernel,
                None,
                None,
                None,
                "target coset subgroup is not contained in the certified action image",
            )
    if not image.contains(target_rep):
        return PairedActionCosetPreimage(
            "target_representative_outside_image",
            group.degree,
            image_degree,
            group.order,
            image.order,
            kernel.order,
            target_subgroup.order,
            0,
            len(levels),
            kernel,
            None,
            None,
            None,
            "target coset representative is outside the certified action image",
        )

    lifted_subgroup_gens = []
    for q in target_subgroup.original_generators or (image_identity,):
        g = _lift_image_element(
            q,
            levels,
            domain_degree=group.degree,
            image_degree=image_degree,
        )
        if g is None:
            raise AssertionError("image.contains succeeded but paired Schreier lift failed")
        lifted_subgroup_gens.append(g)
    representative = _lift_image_element(
        target_rep,
        levels,
        domain_degree=group.degree,
        image_degree=image_degree,
    )
    if representative is None:
        raise AssertionError("image.contains succeeded but representative lift failed")

    preimage_gens = list(kernel.original_generators)
    preimage_gens.extend(lifted_subgroup_gens)
    preimage_subgroup = schreier_stabilizer_chain(preimage_gens or [eg])
    expected_order = kernel.order * target_subgroup.order
    if preimage_subgroup.order != expected_order:
        raise AssertionError(
            "lifted target subgroup does not have the exact kernel-times-image order"
        )
    if not group.contains(representative):
        raise AssertionError("paired target lift escaped the source group")
    for g in preimage_subgroup.original_generators or (eg,):
        if not group.contains(g):
            raise AssertionError("preimage subgroup escaped the source group")

    result = RightCoset(preimage_subgroup, representative)
    return PairedActionCosetPreimage(
        "exact_paired_action_coset_preimage",
        group.degree,
        image_degree,
        group.order,
        image.order,
        kernel.order,
        target_subgroup.order,
        preimage_subgroup.order,
        len(levels),
        kernel,
        preimage_subgroup,
        representative,
        result,
        "paired Schreier lifting reconstructed the complete subgroup-and-representative preimage of the image right coset",
    )
