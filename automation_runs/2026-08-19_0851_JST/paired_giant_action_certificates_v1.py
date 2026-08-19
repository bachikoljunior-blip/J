from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import factorial, log2
from typing import Optional, Tuple

from block_action_preimage_coset_v1 import _paired_chain
from permutation_group_schreier import (
    Permutation,
    StabilizerChain,
    compose,
    group_orbit,
    identity,
    inverse,
    schreier_stabilizer_chain,
    validate_perm,
)


@dataclass(frozen=True)
class PairedGiantActionCertificate:
    status: str
    image_degree: int
    group_order: int
    image_order: int
    kernel_order: int
    giant_type: Optional[str]
    affected_points: Tuple[int, ...]
    unaffected_points: Tuple[int, ...]
    largest_group_orbit: int
    unaffected_stabilizer_theorem_applicable: bool
    unaffected_stabilizer_theorem_verified: bool
    affected_orbit_lemma_verified: bool
    reason: str


def _dedup_pairs(pairs):
    return tuple(sorted(set(pairs), key=repr))


def _paired_point_stabilizer_pairs(pairs, point, domain_degree, image_degree):
    """Schreier generators for a domain point stabilizer, carrying image words."""
    eg = identity(domain_degree)
    eq = identity(image_degree)
    pairs = _dedup_pairs(pairs)
    if not pairs:
        return ((eg, eq),)

    trans = {point: (eg, eq)}
    todo = deque([point])
    while todo:
        x = todo.popleft()
        tg, tq = trans[x]
        for g, q in pairs:
            y = g[x]
            if y not in trans:
                trans[y] = (compose(tg, g), compose(tq, q))
                todo.append(y)

    out = []
    for x, (tg, tq) in trans.items():
        for g, q in pairs:
            y = g[x]
            ug, uq = trans[y]
            hg = compose(compose(tg, g), inverse(ug))
            hq = compose(compose(tq, q), inverse(uq))
            if hg != eg or hq != eq:
                if hg[point] != point:
                    raise AssertionError("paired Schreier generator failed to stabilize requested point")
                out.append((hg, hq))
    return _dedup_pairs(out) or ((eg, eq),)


def _paired_pointwise_stabilizer_pairs(pairs, points, domain_degree, image_degree):
    current = tuple(pairs)
    for point in points:
        current = _paired_point_stabilizer_pairs(
            current, int(point), domain_degree, image_degree
        )
    return current


def _group_orbits(chain: StabilizerChain):
    remaining = set(range(chain.degree))
    out = []
    while remaining:
        x = min(remaining)
        orbit = set(group_orbit(chain, x))
        out.append(tuple(sorted(orbit)))
        remaining -= orbit
    return tuple(out)


def analyze_paired_giant_action(
    group: StabilizerChain,
    image_generators,
) -> PairedGiantActionCertificate:
    """Audit an arbitrary generator-paired homomorphism G -> Sym(m).

    This is the action-generic counterpart of ``analyze_giant_block_action``.
    ``image_generators[i]`` must be the image of
    ``group.original_generators[i]``.  A paired Schreier chain certifies the
    homomorphism by the exact order identity |G|=|ker|*|im|.  Point stabilizer
    images are then computed by Schreier generators while carrying the matching
    image words, so affected/unaffected points do not require a block system or
    an implementation-specific inverse map.

    The interface is intended for Johnson-ground and later certificate actions,
    where the structural image is known generator-by-generator but is not an
    induced action on designated blocks of the original permutation domain.
    """
    eg = identity(group.degree)
    domain_gens = tuple(group.original_generators) or (eg,)
    images = tuple(validate_perm(q) for q in image_generators)
    if len(images) != len(domain_gens):
        raise ValueError("one image generator is required for every domain generator")
    if not images:
        raise ValueError("image generator list cannot be empty")
    m = len(images[0])
    if m < 5 or any(len(q) != m for q in images):
        raise ValueError("a common image degree of at least five is required")

    eq = identity(m)
    image = schreier_stabilizer_chain(images or (eq,))
    _levels, kernel_gens = _paired_chain(domain_gens, images)
    kernel = schreier_stabilizer_chain(kernel_gens or (eg,))
    if kernel.order * image.order != group.order:
        raise ValueError(
            "paired generators do not certify a well-defined homomorphism on the supplied domain group"
        )

    full = factorial(m)
    half = full // 2
    giant_type = "S_m" if image.order == full else ("A_m" if image.order == half else None)
    pairs = tuple(zip(domain_gens, images))
    orbits = _group_orbits(group)
    affected = []
    unaffected = []

    for orbit in orbits:
        x = orbit[0]
        stab_pairs = _paired_point_stabilizer_pairs(
            pairs, x, group.degree, m
        )
        stab_domain = schreier_stabilizer_chain([g for g, _ in stab_pairs] or [eg])
        expected_stab_order = group.order // len(orbit)
        if stab_domain.order != expected_stab_order:
            raise AssertionError("paired point-stabilizer Schreier order mismatch")
        stab_image = schreier_stabilizer_chain([q for _, q in stab_pairs] or [eq])
        is_unaffected = stab_image.order in (half, full)
        (unaffected if is_unaffected else affected).extend(orbit)

    affected = tuple(sorted(affected))
    unaffected = tuple(sorted(unaffected))
    n0 = max((len(O) for O in orbits), default=0)

    theorem_applicable = bool(
        giant_type is not None and m > max(8.0, 2.0 + log2(max(1, n0)))
    )
    theorem_verified = True
    if theorem_applicable:
        stable_pairs = _paired_pointwise_stabilizer_pairs(
            pairs, unaffected, group.degree, m
        )
        stable_image = schreier_stabilizer_chain([q for _, q in stable_pairs] or [eq])
        theorem_verified = stable_image.order in (half, full) and bool(affected)

    affected_lemma = True
    if giant_type is not None:
        affected_set = set(affected)
        for orbit in orbits:
            if not set(orbit) <= affected_set:
                continue
            bound = len(orbit) / m
            remaining = set(orbit)
            while remaining:
                x = min(remaining)
                kernel_orbit = set(group_orbit(kernel, x))
                if not kernel_orbit <= set(orbit):
                    raise AssertionError("kernel orbit escaped a source-group orbit")
                remaining -= kernel_orbit
                if len(kernel_orbit) > bound + 1e-12:
                    affected_lemma = False

    status = "exact_paired_giant_action_certificate" if giant_type is not None else "exact_paired_nongiant_action"
    return PairedGiantActionCertificate(
        status, m, group.order, image.order, kernel.order, giant_type,
        affected, unaffected, n0, theorem_applicable, theorem_verified,
        affected_lemma,
        "generator-paired Schreier kernel and point-stabilizer images give an exact action-generic giant/affected-point certificate",
    )
