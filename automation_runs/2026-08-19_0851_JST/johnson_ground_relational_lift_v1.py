from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Tuple

from canonical_orbital_size_relation import canonical_orbital_size_relation
from johnson_pair_relation_recognizer import recognize_johnson_pair_relation


GroundPermutation = Tuple[int, ...]


@dataclass(frozen=True)
class SignedJohnsonGroundGenerator:
    ground_permutation: GroundPermutation
    complement: bool


@dataclass(frozen=True)
class JohnsonGroundRelationalLift:
    status: str
    ground_size: int
    subset_size: int
    current_degree: int
    coordinate: Tuple[int, ...]
    source_on_standard_subsets: Tuple[object, ...]
    target_on_standard_subsets: Tuple[object, ...]
    lifted_generators: Tuple[SignedJohnsonGroundGenerator, ...]
    strict_auxiliary_progress: bool
    equivariant_up_to_johnson_automorphism: bool
    recognition_search_nodes: int
    reason: str


def _standard_subsets(v: int, k: int):
    return tuple(combinations(range(v), k))


def _induce_signed_ground_generator(v: int, k: int, sigma, complement: bool):
    subsets = _standard_subsets(v, k)
    index = {subset: i for i, subset in enumerate(subsets)}
    universe = set(range(v))
    out = []
    for subset in subsets:
        moved = tuple(sorted(sigma[x] for x in subset))
        if complement:
            moved = tuple(sorted(universe.difference(moved)))
        out.append(index[moved])
    return tuple(out)


def _decode_johnson_automorphism(v: int, k: int, p_std):
    """Decode a Johnson-domain automorphism as a ground permutation + optional complement.

    A ground point a is represented by its star of k-subsets containing a.  An
    induced S_v automorphism maps stars to stars.  When v=2k, the exceptional
    complement coset maps every star to an anti-star.  Requiring one common mode
    for all ground points and then re-inducing the result makes this decoder
    fail-closed rather than accepting an arbitrary permutation of k-subsets.
    """
    subsets = _standard_subsets(v, k)
    m = len(subsets)
    universe_indices = frozenset(range(m))
    stars = tuple(
        frozenset(i for i, subset in enumerate(subsets) if a in subset)
        for a in range(v)
    )
    star_index = {star: a for a, star in enumerate(stars)}
    anti_index = {
        universe_indices.difference(star): a for a, star in enumerate(stars)
    }

    sigma = []
    modes = []
    for a, star in enumerate(stars):
        image = frozenset(p_std[i] for i in star)
        if image in star_index:
            sigma.append(star_index[image])
            modes.append(False)
        elif v == 2 * k and image in anti_index:
            sigma.append(anti_index[image])
            modes.append(True)
        else:
            return None

    if len(set(modes)) != 1 or sorted(sigma) != list(range(v)):
        return None
    signed = SignedJohnsonGroundGenerator(tuple(sigma), modes[0])
    if _induce_signed_ground_generator(v, k, signed.ground_permutation, signed.complement) != tuple(p_std):
        return None
    return signed


def lift_primitive_johnson_to_ground_relation(
    group,
    source_values,
    target_values,
    *,
    max_recognition_nodes: int = 500000,
) -> JohnsonGroundRelationalLift:
    """Exact structural lift from a certified Johnson-domain SI instance to its ground relation.

    This does not claim to solve the resulting large-ground relational SI problem.
    It proves the reduction interface needed for that recursion: one exact Johnson
    coordinate gauge, the source/target colors transported to standard k-subsets,
    and every supplied ambient generator decoded to the faithful ground action
    (with the v=2k complement bit when present).

    The chosen coordinate representative need not itself be canonical.  Because
    the recognizer returns the complete Johnson isomorphism coset, any other gauge
    differs by a Johnson automorphism; the returned reduction is therefore exact
    and equivariant up to that explicitly represented automorphism group.
    """
    source = tuple(source_values)
    target = tuple(target_values)
    m = group.degree
    if len(source) != m or len(target) != m:
        raise ValueError("string/group degree mismatch")
    if max_recognition_nodes < 1:
        raise ValueError("max_recognition_nodes must be positive")

    relation = canonical_orbital_size_relation(group)
    johnson = recognize_johnson_pair_relation(
        m,
        relation.pair_weights,
        max_nodes_per_candidate=max_recognition_nodes,
    )
    if johnson.status != "exact_johnson_color_relation" or johnson.isomorphism_coset is None:
        return JohnsonGroundRelationalLift(
            "undetermined_not_certified_johnson",
            int(johnson.ground_size or 0),
            int(johnson.subset_size or 0),
            m,
            (), (), (), (), False, False,
            johnson.search_nodes,
            johnson.reason,
        )

    v = int(johnson.ground_size)
    k = int(johnson.subset_size)
    coordinate = tuple(johnson.isomorphism_coset.representative)
    if sorted(coordinate) != list(range(m)):
        raise AssertionError("Johnson coordinate representative is not a permutation")

    source_std = [None] * m
    target_std = [None] * m
    for current in range(m):
        std = coordinate[current]
        source_std[std] = source[current]
        target_std[std] = target[current]

    lifted = []
    for generator in group.original_generators:
        p_std = [0] * m
        for current in range(m):
            p_std[coordinate[current]] = coordinate[generator[current]]
        signed = _decode_johnson_automorphism(v, k, tuple(p_std))
        if signed is None:
            return JohnsonGroundRelationalLift(
                "undetermined_generator_not_johnson_automorphism",
                v, k, m, coordinate,
                tuple(source_std), tuple(target_std), tuple(lifted),
                v < m, False, johnson.search_nodes,
                "a supplied ambient generator did not decode and re-induce as an exact Johnson automorphism",
            )
        lifted.append(signed)

    return JohnsonGroundRelationalLift(
        "exact_johnson_ground_relational_lift",
        v, k, m, coordinate,
        tuple(source_std), tuple(target_std), tuple(lifted),
        v < m,
        True,
        johnson.search_nodes,
        "certified Johnson coordinates transport the colored k-subset relation to a strictly smaller ground; every ambient generator was exactly decoded and re-induced",
    )
