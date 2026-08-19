from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import factorial, log2
from typing import Iterable, Optional, Tuple

from permutation_group_schreier import Permutation, StabilizerChain, compose, group_orbit, identity, inverse, schreier_stabilizer_chain
from coset_stabilizer_primitives import pointwise_stabilizer_chain


@dataclass(frozen=True)
class GiantBlockActionCertificate:
    status: str
    block_count: int
    image_order: int
    kernel_order: int
    group_order: int
    giant_type: Optional[str]
    affected_points: Tuple[int, ...]
    unaffected_points: Tuple[int, ...]
    largest_group_orbit: int
    unaffected_stabilizer_theorem_applicable: bool
    unaffected_stabilizer_theorem_verified: bool
    affected_orbit_lemma_verified: bool
    kernel_generator_count: int
    reason: str


def _dedup_pairs(pairs):
    return tuple(sorted(set(pairs), key=repr))


def _paired_kernel_generators(domain_gens, image_gens):
    """Kernel generators for a generator-defined homomorphism without image enumeration.

    Schreier recursion is performed on the image action while carrying a preimage
    word for every image transversal. When the residual image becomes trivial,
    the accumulated domain generators generate exactly the kernel.
    """
    if len(domain_gens) != len(image_gens) or not domain_gens:
        raise ValueError("paired generators required")
    ng = len(domain_gens[0])
    nq = len(image_gens[0])
    eg = identity(ng)
    eq = identity(nq)
    pairs = _dedup_pairs(tuple(zip(domain_gens, image_gens)))

    def rec(ps):
        if all(q == eq for _, q in ps):
            return tuple(sorted({g for g, _ in ps if g != eg}))

        base = next(i for i in range(nq) if any(q[i] != i for _, q in ps))
        trans = {base: (eg, eq)}
        todo = deque([base])
        while todo:
            x = todo.popleft()
            tg, tq = trans[x]
            for g, q in ps:
                y = q[x]
                if y not in trans:
                    trans[y] = (compose(tg, g), compose(tq, q))
                    todo.append(y)

        nxt = []
        for x, (tg, tq) in trans.items():
            for g, q in ps:
                y = q[x]
                ug, uq = trans[y]
                hg = compose(compose(tg, g), inverse(ug))
                hq = compose(compose(tq, q), inverse(uq))
                if hg != eg or hq != eq:
                    nxt.append((hg, hq))
        return rec(_dedup_pairs(tuple(nxt)))

    return rec(pairs)


def _block_action(p: Permutation, blocks, point_to_block):
    k = len(blocks)
    out = []
    for block in blocks:
        images = {point_to_block.get(p[u], -1) for u in block}
        if len(images) != 1 or -1 in images:
            raise ValueError("designated block family is not invariant under generator")
        j = next(iter(images))
        if {p[u] for u in block} != set(blocks[j]):
            raise ValueError("generator does not map a block exactly onto a designated block")
        out.append(j)
    if sorted(out) != list(range(k)):
        raise ValueError("induced block action is not a permutation")
    return tuple(out)


def _image_chain(chain: StabilizerChain, blocks, point_to_block):
    k = len(blocks)
    gens = chain.original_generators or (identity(chain.degree),)
    images = [_block_action(g, blocks, point_to_block) for g in gens]
    return schreier_stabilizer_chain(images or [identity(k)])


def _group_orbits(chain: StabilizerChain):
    remaining = set(range(chain.degree))
    out = []
    while remaining:
        x = min(remaining)
        orbit = set(group_orbit(chain, x))
        out.append(tuple(sorted(orbit)))
        remaining -= orbit
    return tuple(out)


def analyze_giant_block_action(group: StabilizerChain, blocks: Iterable[Iterable[int]]) -> GiantBlockActionCertificate:
    """Audit a supplied invariant block action as a Babai-style giant representation.

    The designated block family need not cover the full permutation domain. This
    permits unaffected points outside the quotient-support. For k>=5, an image of
    order k!/2 or k! is exactly A_k or S_k. Affected points are classified from
    the exact image of their point stabilizer. The paired-Schreier kernel is then
    used to machine-check the affected-orbit bound. When the numerical hypothesis
    k > max(8, 2+log2(n0)) holds, the unaffected-stabilizer conclusion is also
    checked exactly.
    """
    blocks = tuple(tuple(sorted(set(int(x) for x in b))) for b in blocks)
    if len(blocks) < 5 or any(not b for b in blocks):
        raise ValueError("at least five nonempty designated blocks required")
    flat = [u for b in blocks for u in b]
    if len(set(flat)) != len(flat) or any(u < 0 or u >= group.degree for u in flat):
        raise ValueError("blocks must be disjoint subsets of the permutation domain")

    point_to_block = {u: i for i, b in enumerate(blocks) for u in b}
    k = len(blocks)
    eg = identity(group.degree)
    eq = identity(k)
    domain_gens = group.original_generators or (eg,)
    image_gens = tuple(_block_action(g, blocks, point_to_block) for g in domain_gens)
    image = schreier_stabilizer_chain(image_gens or [eq])

    full = factorial(k)
    half = full // 2
    giant_type = "S_k" if image.order == full else ("A_k" if image.order == half else None)

    kernel_gens = _paired_kernel_generators(domain_gens, image_gens)
    kernel = schreier_stabilizer_chain(kernel_gens or [eg])
    if any(_block_action(g, blocks, point_to_block) != eq for g in kernel.original_generators):
        raise AssertionError("kernel generator has nontrivial quotient image")
    if kernel.order * image.order != group.order:
        raise AssertionError("homomorphism order theorem mismatch")

    orbits = _group_orbits(group)
    affected = []
    unaffected = []
    for orbit in orbits:
        x = orbit[0]
        stabilizer = pointwise_stabilizer_chain(group, [x])
        stabilizer_image = _image_chain(stabilizer, blocks, point_to_block)
        is_unaffected = stabilizer_image.order in (half, full)
        (unaffected if is_unaffected else affected).extend(orbit)

    affected = tuple(sorted(affected))
    unaffected = tuple(sorted(unaffected))
    n0 = max(map(len, orbits), default=0)

    theorem_applicable = giant_type is not None and k > max(8, 2 + log2(max(1, n0)))
    theorem_verified = True
    if theorem_applicable:
        unaffected_stabilizer = pointwise_stabilizer_chain(group, unaffected)
        unaffected_image = _image_chain(unaffected_stabilizer, blocks, point_to_block)
        theorem_verified = unaffected_image.order in (half, full) and len(affected) > 0

    affected_lemma_verified = True
    if giant_type is not None and k >= 5:
        affected_set = set(affected)
        for orbit in orbits:
            if not set(orbit) <= affected_set:
                continue
            bound = len(orbit) / k
            remaining = set(orbit)
            while remaining:
                x = min(remaining)
                kernel_orbit = set(group_orbit(kernel, x))
                remaining -= kernel_orbit
                if len(kernel_orbit) > bound + 1e-12:
                    affected_lemma_verified = False

    status = "exact_giant_action_certificate" if giant_type is not None else "exact_nongiant_action"
    return GiantBlockActionCertificate(
        status, k, image.order, kernel.order, group.order, giant_type,
        affected, unaffected, n0,
        theorem_applicable, theorem_verified, affected_lemma_verified,
        len(kernel.original_generators),
        "exact induced block homomorphism, paired-Schreier kernel, affected-point images, and theorem-side audits",
    )
