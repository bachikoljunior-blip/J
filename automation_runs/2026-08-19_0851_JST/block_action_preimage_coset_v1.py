from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple

from coset_stabilizer_primitives import RightCoset
from giant_block_action_certificates import _block_action
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
class BlockActionPreimageCoset:
    status: str
    quotient_degree: int
    image_order: int
    kernel_order: int
    sift_levels: int
    target_image: Permutation
    representative: Optional[Permutation]
    kernel: StabilizerChain
    coset: Optional[RightCoset]
    reason: str


@dataclass(frozen=True)
class PreparedBlockActionPreimage:
    group: StabilizerChain
    blocks: Tuple[Tuple[int, ...], ...]
    point_to_block: Tuple[Tuple[int, int], ...]
    image: StabilizerChain
    kernel: StabilizerChain
    levels: tuple


def _dedup_pairs(pairs):
    return tuple(sorted(set(pairs), key=repr))


def _paired_chain(domain_gens, image_gens):
    """Schreier chain on the image while retaining full-domain preimage words."""
    ng = len(domain_gens[0])
    nq = len(image_gens[0])
    eg = identity(ng)
    eq = identity(nq)
    pairs = _dedup_pairs(tuple(zip(domain_gens, image_gens)))
    levels = []

    while any(q != eq for _, q in pairs):
        base = next(i for i in range(nq) if any(q[i] != i for _, q in pairs))
        trans = {base: (eg, eq)}
        todo = deque([base])
        while todo:
            x = todo.popleft()
            tg, tq = trans[x]
            for g, q in pairs:
                y = q[x]
                if y not in trans:
                    trans[y] = (compose(tg, g), compose(tq, q))
                    todo.append(y)
        levels.append((base, tuple(sorted(trans.items()))))

        nxt = []
        for x, (tg, tq) in trans.items():
            for g, q in pairs:
                y = q[x]
                ug, uq = trans[y]
                hg = compose(compose(tg, g), inverse(ug))
                hq = compose(compose(tq, q), inverse(uq))
                if hg != eg or hq != eq:
                    nxt.append((hg, hq))
        pairs = _dedup_pairs(tuple(nxt))

    kernel_gens = tuple(sorted({g for g, q in pairs if q == eq and g != eg}))
    return tuple(levels), kernel_gens


def prepare_block_action_preimage(group, blocks) -> PreparedBlockActionPreimage:
    """Prepare one exact block-action homomorphism for repeated preimages.

    The paired image stabilizer chain, quotient kernel, and paired transversals
    depend only on the domain group and ordered block family.  Keeping them in a
    frozen artifact prevents local-certificate callers from rebuilding the same
    homomorphism for every standard generator of A(T).
    """
    blocks = tuple(tuple(sorted(set(int(x) for x in b))) for b in blocks)
    k = len(blocks)
    if not blocks or any(not b for b in blocks):
        raise ValueError("nonempty designated blocks required")
    flat = [u for b in blocks for u in b]
    if len(flat) != len(set(flat)) or any(u < 0 or u >= group.degree for u in flat):
        raise ValueError("blocks must be disjoint subsets of the group domain")

    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    eg = identity(group.degree)
    eq = identity(k)
    domain_gens = group.original_generators or (eg,)
    image_gens = tuple(_block_action(g, blocks, point_to_block) for g in domain_gens)
    image = schreier_stabilizer_chain(image_gens or [eq])
    levels, kernel_gens = _paired_chain(domain_gens, image_gens)
    kernel = schreier_stabilizer_chain(kernel_gens or [eg])
    if kernel.order * image.order != group.order:
        raise AssertionError("paired chain violates |G|=|ker|*|im|")
    if any(_block_action(g, blocks, point_to_block) != eq for g in kernel.original_generators):
        raise AssertionError("paired-chain kernel generator has nontrivial image")
    return PreparedBlockActionPreimage(
        group,
        blocks,
        tuple(sorted(point_to_block.items())),
        image,
        kernel,
        levels,
    )


def lift_prepared_block_action_preimage(
    prepared: PreparedBlockActionPreimage,
    target_image,
) -> BlockActionPreimageCoset:
    """Lift one quotient permutation through a prepared exact homomorphism."""
    group = prepared.group
    blocks = prepared.blocks
    k = len(blocks)
    point_to_block = dict(prepared.point_to_block)
    image = prepared.image
    kernel = prepared.kernel
    levels = prepared.levels
    target = validate_perm(target_image)
    if len(target) != k:
        raise ValueError("target quotient permutation has wrong degree")
    eg = identity(group.degree)
    eq = identity(k)

    residual = target
    selected_domain = []
    for base, raw_trans in levels:
        trans = dict(raw_trans)
        x = residual[base]
        if x not in trans:
            return BlockActionPreimageCoset(
                "quotient_not_in_image", k, image.order, kernel.order,
                len(levels), target, None, kernel, None,
                "Schreier sift proves the requested quotient permutation is outside the image",
            )
        tg, tq = trans[x]
        selected_domain.append(tg)
        residual = compose(residual, inverse(tq))

    if residual != eq:
        return BlockActionPreimageCoset(
            "quotient_not_in_image", k, image.order, kernel.order,
            len(levels), target, None, kernel, None,
            "nontrivial quotient residual remained after paired Schreier sift",
        )

    representative = eg
    for tg in reversed(selected_domain):
        representative = compose(representative, tg)

    if not group.contains(representative):
        raise AssertionError("lift escaped source group")
    if _block_action(representative, blocks, point_to_block) != target:
        raise AssertionError("paired Schreier lift has wrong quotient image")

    coset = RightCoset(kernel, representative)
    return BlockActionPreimageCoset(
        "exact_block_action_preimage_coset", k, image.order, kernel.order,
        len(levels), target, representative, kernel, coset,
        "prepared paired quotient Schreier sift returned one full-domain lift and the exact quotient kernel",
    )


def block_action_preimage_coset(group, blocks, target_image) -> BlockActionPreimageCoset:
    """Return the exact preimage coset of one quotient permutation.

    Unlike BFS over the quotient group, this builds a Schreier chain on quotient
    point orbits while carrying matching full-domain words.  Sifting the requested
    quotient permutation yields one full-domain preimage if it is in the image;
    the residual paired generators yield the exact kernel.  Hence every preimage
    is exactly kernel * representative in the repository's RightCoset convention.
    """
    return lift_prepared_block_action_preimage(
        prepare_block_action_preimage(group, blocks),
        target_image,
    )
