from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple

from block_action_preimage_coset_v1 import _paired_chain
from permutation_group_schreier import (
    Permutation,
    StabilizerChain,
    compose,
    identity,
    inverse,
    schreier_stabilizer_chain,
    validate_perm,
)


@dataclass(frozen=True)
class PairedActionElementImage:
    status: str
    target: Permutation
    image: Optional[Permutation]
    source_group_order: int
    image_group_order: int
    kernel_order: int
    sift_levels: int
    reason: str


def _dedup_pairs(pairs):
    return tuple(sorted(set(pairs), key=repr))


def _paired_domain_chain(domain_gens, image_gens):
    """Schreier chain on the domain while carrying matching image words."""
    ng = len(domain_gens[0])
    nq = len(image_gens[0])
    eg = identity(ng)
    eq = identity(nq)
    pairs = _dedup_pairs(tuple(zip(domain_gens, image_gens)))
    levels = []

    for base in range(ng):
        if not any(g[base] != base for g, _ in pairs):
            continue
        trans = {base: (eg, eq)}
        todo = deque([base])
        while todo:
            x = todo.popleft()
            tg, tq = trans[x]
            for g, q in pairs:
                y = g[x]
                if y not in trans:
                    trans[y] = (compose(tg, g), compose(tq, q))
                    todo.append(y)
        levels.append((base, tuple(sorted(trans.items()))))

        nxt = []
        for x, (tg, tq) in trans.items():
            for g, q in pairs:
                y = g[x]
                ug, uq = trans[y]
                hg = compose(compose(tg, g), inverse(ug))
                hq = compose(compose(tq, q), inverse(uq))
                if hg != eg or hq != eq:
                    nxt.append((hg, hq))
        pairs = _dedup_pairs(nxt)

    # Once every residual domain generator is identity, well-definedness requires
    # every paired residual image word to be identity too.  A nontrivial residual
    # would exhibit a relation in the domain generators that the proposed images
    # do not satisfy.
    if any(g != eg for g, _ in pairs):
        raise AssertionError("domain Schreier chain did not reach the identity subgroup")
    if any(q != eq for _, q in pairs):
        raise ValueError("generator pairing violates a source-group relation")
    return tuple(levels)


def paired_action_image_of_element(
    group: StabilizerChain,
    image_generators,
    target,
) -> PairedActionElementImage:
    """Evaluate the certified paired homomorphism on an arbitrary group element.

    Earlier paired-action code could lift an image element to the source but could
    not map a newly reconstructed source-subgroup generator back into the image.
    Growing-beard recursion needs exactly that operation after each string-segment
    intersection.  We build a Schreier chain on the *source* action while carrying
    image words, sift the target source permutation, and compose the corresponding
    image transversals in the same reverse order as the source decomposition.
    """
    eg = identity(group.degree)
    domain_gens = tuple(group.original_generators) or (eg,)
    images = tuple(validate_perm(q) for q in image_generators)
    if len(images) != len(domain_gens):
        raise ValueError("one image generator is required for every source generator")
    if not images:
        raise ValueError("image generator list cannot be empty")
    m = len(images[0])
    if any(len(q) != m for q in images):
        raise ValueError("image generator degree mismatch")
    h = validate_perm(target)
    if len(h) != group.degree:
        raise ValueError("target source element has wrong degree")

    eq = identity(m)
    image = schreier_stabilizer_chain(images or (eq,))
    _image_levels, kernel_gens = _paired_chain(domain_gens, images)
    kernel = schreier_stabilizer_chain(kernel_gens or (eg,))
    if kernel.order * image.order != group.order:
        raise ValueError(
            "paired generators do not certify a well-defined homomorphism on the supplied source group"
        )
    levels = _paired_domain_chain(domain_gens, images)

    residual = h
    selected_images = []
    for base, raw_trans in levels:
        trans = dict(raw_trans)
        x = residual[base]
        if x not in trans:
            return PairedActionElementImage(
                "target_outside_source_group", h, None, group.order, image.order,
                kernel.order, len(levels),
                "source-domain Schreier sift proves the target permutation is outside the source group",
            )
        tg, tq = trans[x]
        selected_images.append(tq)
        residual = compose(residual, inverse(tg))
    if residual != eg:
        return PairedActionElementImage(
            "target_outside_source_group", h, None, group.order, image.order,
            kernel.order, len(levels),
            "nontrivial source residual remained after paired domain sift",
        )

    q = eq
    for tq in reversed(selected_images):
        q = compose(q, tq)
    if not image.contains(q):
        raise AssertionError("evaluated image escaped the generated image subgroup")
    return PairedActionElementImage(
        "exact_paired_action_element_image", h, q, group.order, image.order,
        kernel.order, len(levels),
        "source Schreier decomposition with carried image transversals evaluated the certified homomorphism exactly",
    )
