from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import comb, factorial
from typing import Optional, Tuple

from permutation_group_schreier import Permutation, StabilizerChain, identity, schreier_stabilizer_chain


@dataclass(frozen=True)
class DecodedJohnsonGenerator:
    quotient_permutation: Permutation
    ground_permutation: Permutation
    complemented: bool


@dataclass(frozen=True)
class JohnsonAutomorphismActionCertificate:
    status: str
    ground_size: int
    subset_size: int
    quotient_degree: int
    quotient_group_order: int
    ground_projection_order: int
    expected_full_order: int
    complemented_generator_count: int
    generators: Tuple[DecodedJohnsonGenerator, ...]
    reason: str


def _decode_generator(p: Permutation, v: int, k: int):
    vertices = list(combinations(range(v), k))
    n = len(vertices)
    if len(p) != n:
        raise ValueError("quotient permutation degree mismatch")

    stars = [
        {i for i, S in enumerate(vertices) if a in S}
        for a in range(v)
    ]
    star_lookup = {frozenset(stars[b]): b for b in range(v)}
    all_vertices = set(range(n))
    costar_lookup = (
        {frozenset(all_vertices - stars[b]): b for b in range(v)}
        if v == 2 * k else {}
    )

    ground = []
    flags = []
    for a in range(v):
        image_star = frozenset(p[i] for i in stars[a])
        if image_star in star_lookup:
            ground.append(star_lookup[image_star])
            flags.append(False)
        elif image_star in costar_lookup:
            ground.append(costar_lookup[image_star])
            flags.append(True)
        else:
            return None

    if len(set(flags)) != 1 or sorted(ground) != list(range(v)):
        return None
    sigma = tuple(ground)
    complemented = flags[0]

    # Directly verify the decoded action on every k-subset vertex.
    index = {S: i for i, S in enumerate(vertices)}
    universe = set(range(v))
    for i, S in enumerate(vertices):
        image = {sigma[x] for x in S}
        if complemented:
            image = universe - image
        j = index[tuple(sorted(image))]
        if p[i] != j:
            return None
    return sigma, complemented


def analyze_johnson_automorphism_action(
    quotient_group: StabilizerChain,
    ground_size: int,
    subset_size: int,
) -> JohnsonAutomorphismActionCertificate:
    """Decode the full automorphism ambiguity of a standard Johnson graph.

    A quotient automorphism is decoded by the images of the canonical element
    stars (all k-subsets containing one ground point). For v!=2k every valid
    Johnson automorphism must map stars to stars. For v=2k the complement map may
    send every star to a costar, giving the known extra C2 symmetry.

    The routine verifies each supplied generator on every Johnson vertex, builds
    the projected ground permutation group, and compares exact stabilizer-chain
    orders with the full Johnson automorphism order. It therefore preserves the
    coordinate ambiguity explicitly rather than choosing an arbitrary hidden
    ground labeling and calling it canonical.
    """
    v = int(ground_size)
    k = int(subset_size)
    if not (2 <= k <= v // 2):
        raise ValueError("expected 2<=k<=v/2")
    degree = comb(v, k)
    if quotient_group.degree != degree:
        raise ValueError("quotient group degree does not match C(v,k)")

    decoded = []
    for g in quotient_group.original_generators:
        item = _decode_generator(g, v, k)
        if item is None:
            return JohnsonAutomorphismActionCertificate(
                "not_johnson_automorphism_group", v, k, degree,
                quotient_group.order, 0, 0, 0, (),
                "a quotient generator does not act as a ground permutation or allowed middle-layer complement",
            )
        sigma, complemented = item
        decoded.append(DecodedJohnsonGenerator(g, sigma, complemented))

    ground_gens = [d.ground_permutation for d in decoded] or [identity(v)]
    ground = schreier_stabilizer_chain(ground_gens)
    expected = factorial(v) * (2 if v == 2 * k else 1)
    full = quotient_group.order == expected and ground.order == factorial(v)

    return JohnsonAutomorphismActionCertificate(
        "exact_full_johnson_automorphism_action" if full else "exact_johnson_subgroup_action",
        v,
        k,
        degree,
        quotient_group.order,
        ground.order,
        expected,
        sum(d.complemented for d in decoded),
        tuple(decoded),
        "every generator decoded and was directly verified on all k-subsets; exact group orders determine whether the full Johnson automorphism group is present",
    )
