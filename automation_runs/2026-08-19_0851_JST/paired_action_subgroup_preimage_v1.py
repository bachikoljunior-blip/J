from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from block_action_preimage_coset_v1 import _paired_chain
from paired_action_coset_preimage_v1 import _lift_image_element
from permutation_group_schreier import (
    Permutation,
    StabilizerChain,
    identity,
    schreier_stabilizer_chain,
    validate_perm,
)


@dataclass(frozen=True)
class PairedActionSubgroupPreimage:
    status: str
    domain_degree: int
    image_degree: int
    source_group_order: int
    source_image_order: int
    kernel_order: int
    target_subgroup_order: int
    preimage_subgroup_order: int
    preimage_subgroup: Optional[StabilizerChain]
    paired_domain_generators: Tuple[Permutation, ...]
    paired_image_generators: Tuple[Permutation, ...]
    reason: str


def paired_action_subgroup_preimage(
    group: StabilizerChain,
    image_generators,
    target_subgroup: StabilizerChain,
) -> PairedActionSubgroupPreimage:
    """Exact subgroup preimage while preserving a usable generator pairing.

    ``paired_action_coset_preimage`` proves exact coset preimages but intentionally
    returns only the full-domain coset. Local-certificate recursion needs to apply
    the same structural homomorphism again to the resulting subgroup. This helper
    therefore reconstructs the subgroup preimage and, crucially, returns a domain
    generator and its exact image at the same index for every retained generator.

    The returned pairs consist of paired-Schreier kernel generators with identity
    image plus one lifted generator for every supplied target-subgroup generator.
    Exact order checks on source image, kernel, target image and reconstructed
    preimage make the interface fail closed if the supplied generator pairing is
    not a homomorphism or the target subgroup is not contained in the image.
    """
    eg = identity(group.degree)
    domain_gens = tuple(group.original_generators) or (eg,)
    images = tuple(validate_perm(q) for q in image_generators)
    if len(images) != len(domain_gens):
        raise ValueError("one image generator is required for every domain generator")
    if not images:
        raise ValueError("image generator list cannot be empty")
    m = len(images[0])
    if any(len(q) != m for q in images):
        raise ValueError("image generator degree mismatch")
    if target_subgroup.degree != m:
        raise ValueError("target subgroup has wrong image degree")

    eq = identity(m)
    image = schreier_stabilizer_chain(images or (eq,))
    levels, kernel_gens = _paired_chain(domain_gens, images)
    kernel = schreier_stabilizer_chain(kernel_gens or (eg,))
    if kernel.order * image.order != group.order:
        raise ValueError(
            "paired generators do not certify a well-defined action homomorphism on the supplied source group"
        )

    target_gens = tuple(target_subgroup.original_generators) or (eq,)
    if any(not image.contains(q) for q in target_gens):
        return PairedActionSubgroupPreimage(
            "target_subgroup_outside_image", group.degree, m, group.order,
            image.order, kernel.order, target_subgroup.order, 0, None, (), (),
            "a target-subgroup generator lies outside the certified source image",
        )

    paired_domain = []
    paired_image = []
    for g in kernel.original_generators:
        paired_domain.append(g)
        paired_image.append(eq)
    for q in target_gens:
        g = _lift_image_element(
            q, levels, domain_degree=group.degree, image_degree=m
        )
        if g is None:
            raise AssertionError("target generator was in the image but paired lift failed")
        paired_domain.append(g)
        paired_image.append(q)

    if not paired_domain:
        paired_domain = [eg]
        paired_image = [eq]
    preimage = schreier_stabilizer_chain(paired_domain)
    paired_image_chain = schreier_stabilizer_chain(paired_image)
    expected = kernel.order * target_subgroup.order
    if preimage.order != expected:
        raise AssertionError("reconstructed subgroup preimage has the wrong kernel-times-target order")
    if paired_image_chain.order != target_subgroup.order:
        raise AssertionError("returned paired image generators do not regenerate the target subgroup")
    if any(not group.contains(g) for g in preimage.original_generators):
        raise AssertionError("subgroup preimage escaped the source group")

    return PairedActionSubgroupPreimage(
        "exact_paired_action_subgroup_preimage", group.degree, m, group.order,
        image.order, kernel.order, target_subgroup.order, preimage.order,
        preimage, tuple(paired_domain), tuple(paired_image),
        "paired Schreier kernel plus lifted target generators reconstruct the exact subgroup preimage and retain generator-by-generator image witnesses for recursive use",
    )
