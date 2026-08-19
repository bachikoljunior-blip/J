from __future__ import annotations

from dataclasses import dataclass

from block_action_preimage_coset_v1 import _paired_chain
from coset_stabilizer_primitives import RightCoset
from permutation_group_schreier import compose, identity, inverse, schreier_stabilizer_chain, validate_perm


@dataclass(frozen=True)
class PairedActionPreimageCoset:
    status: str
    domain_degree: int
    image_degree: int
    image_order: int
    kernel_order: int
    target_subgroup_order: int
    preimage_subgroup_order: int
    representative: tuple | None
    subgroup: object | None
    coset: RightCoset | None
    reason: str


def _lift_one(levels, target, *, domain_degree, image_degree):
    eg = identity(domain_degree)
    eq = identity(image_degree)
    residual = validate_perm(target)
    if len(residual) != image_degree:
        raise ValueError("target image has wrong degree")
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
    representative = eg
    for tg in reversed(selected):
        representative = compose(representative, tg)
    return representative


def paired_action_preimage_coset(domain_group, image_generators, target_coset: RightCoset):
    """Exact preimage of an image right coset under a generator-paired action.

    image_generators[i] must be the image of domain_group.original_generators[i]
    under one group homomorphism.  A paired Schreier chain retains domain words
    while sifting image permutations.  The exact kernel plus lifts of generators
    of the target subgroup generate its full preimage; a lift of the target
    representative then gives the exact right coset.  Cardinality is audited by
    |preimage(K)| = |kernel|*|K|.
    """
    ng = domain_group.degree
    domain_gens = tuple(domain_group.original_generators or (identity(ng),))
    image_gens = tuple(validate_perm(g) for g in image_generators)
    if len(domain_gens) != len(image_gens):
        raise ValueError("domain and image generator lists must be paired one-for-one")
    if not image_gens:
        raise ValueError("at least one image generator required")
    nq = len(image_gens[0])
    if any(len(g) != nq for g in image_gens):
        raise ValueError("inconsistent image generator degree")
    if target_coset.subgroup.degree != nq or len(target_coset.representative) != nq:
        raise ValueError("target coset has wrong image degree")

    image = schreier_stabilizer_chain(image_gens)
    levels, kernel_gens = _paired_chain(domain_gens, image_gens)
    kernel = schreier_stabilizer_chain(kernel_gens or (identity(ng),))
    if kernel.order * image.order != domain_group.order:
        raise AssertionError("paired action violates |G|=|ker|*|im|")

    if not image.contains(target_coset.representative):
        return PairedActionPreimageCoset(
            "target_coset_outside_image", ng, nq, image.order, kernel.order,
            target_coset.subgroup.order, 0, None, None, None,
            "target representative is outside the represented image group",
        )
    if any(not image.contains(g) for g in target_coset.subgroup.original_generators):
        return PairedActionPreimageCoset(
            "target_coset_outside_image", ng, nq, image.order, kernel.order,
            target_coset.subgroup.order, 0, None, None, None,
            "target subgroup contains a generator outside the represented image group",
        )

    lifted_subgroup_gens = list(kernel.original_generators)
    for g in target_coset.subgroup.original_generators:
        lift = _lift_one(levels, g, domain_degree=ng, image_degree=nq)
        if lift is None:
            raise AssertionError("image subgroup generator passed membership but paired sift failed")
        lifted_subgroup_gens.append(lift)
    subgroup = schreier_stabilizer_chain(lifted_subgroup_gens or (identity(ng),))
    expected_order = kernel.order * target_coset.subgroup.order
    if subgroup.order != expected_order:
        raise AssertionError("preimage subgroup order disagrees with kernel*target-subgroup order")

    representative = _lift_one(
        levels,
        target_coset.representative,
        domain_degree=ng,
        image_degree=nq,
    )
    if representative is None:
        raise AssertionError("image representative passed membership but paired sift failed")
    if not domain_group.contains(representative):
        raise AssertionError("paired action representative lift escaped domain group")

    coset = RightCoset(subgroup, representative)
    return PairedActionPreimageCoset(
        "exact_paired_action_preimage_coset",
        ng,
        nq,
        image.order,
        kernel.order,
        target_coset.subgroup.order,
        subgroup.order,
        representative,
        subgroup,
        coset,
        "paired Schreier sifting exactly lifted the reduced right coset, with kernel and subgroup cardinalities mechanically audited",
    )
