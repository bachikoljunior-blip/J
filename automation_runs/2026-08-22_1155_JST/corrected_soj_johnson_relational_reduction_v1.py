from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Any, Sequence

SCHEMA_VERSION = 1
REDUCTION_STATUS = "certified_johnson_ground_relational_reduction"


@dataclass(frozen=True)
class JohnsonGroundRelationalReductionEvidence:
    schema_version: int
    status: str
    certified: bool
    canonical: bool
    exact: bool
    progress_certified: bool
    solution_transport_certified: bool
    ambient_membership_transport_certified: bool
    complement_ambiguity_handled: bool
    source_action_degree: int
    johnson_ground_size: int
    johnson_subset_size: int
    child_ground_size: int
    multiplicative_cost: float
    max_multiplicative_cost: float
    reduction_identity: str
    canonical_vertex_subsets: tuple[tuple[int, ...], ...]
    canonical_ground_stars: tuple[tuple[int, ...], ...]
    induced_ground_generators: tuple[tuple[int, ...], ...]
    construction_work_bound: int
    reason: str


def _fail(reason: str, *, v: int = 0, k: int = 0, n: int = 0) -> JohnsonGroundRelationalReductionEvidence:
    return JohnsonGroundRelationalReductionEvidence(
        SCHEMA_VERSION,
        "johnson_ground_relational_reduction_not_certified",
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        n,
        v,
        k,
        0,
        0.0,
        0.0,
        "",
        (),
        (),
        (),
        0,
        reason,
    )


def _strict_int(value: Any, name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be a strict integer")
    return value


def _strict_sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a finite sequence")
    return value


def _normalize_subset(raw: Any, *, v: int, k: int, index: int) -> tuple[int, ...]:
    seq = _strict_sequence(raw, f"embedding[{index}]")
    if len(seq) != k:
        raise ValueError(f"embedding[{index}] must contain exactly k points")
    points: list[int] = []
    for offset, point in enumerate(seq):
        point = _strict_int(point, f"embedding[{index}][{offset}]")
        if not 0 <= point < v:
            raise ValueError(f"embedding[{index}] point is outside the Johnson ground")
        points.append(point)
    if len(set(points)) != k:
        raise ValueError(f"embedding[{index}] contains a repeated ground point")
    return tuple(sorted(points))


def _normalize_permutation(raw: Any, *, degree: int, index: int) -> tuple[int, ...]:
    seq = _strict_sequence(raw, f"ambient_generators[{index}]")
    if len(seq) != degree:
        raise ValueError(f"ambient_generators[{index}] has the wrong action degree")
    perm: list[int] = []
    for offset, image in enumerate(seq):
        image = _strict_int(image, f"ambient_generators[{index}][{offset}]")
        if not 0 <= image < degree:
            raise ValueError(f"ambient_generators[{index}] has an image outside the action domain")
        perm.append(image)
    if len(set(perm)) != degree:
        raise ValueError(f"ambient_generators[{index}] is not a permutation")
    return tuple(perm)


def _sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def certify_johnson_ground_relational_reduction(
    *,
    johnson_ground_size: int,
    johnson_subset_size: int,
    embedding: Sequence[Sequence[int]],
    ambient_generators: Sequence[Sequence[int]],
) -> JohnsonGroundRelationalReductionEvidence:
    """Certify the deterministic J(v,k) -> ground relational reduction.

    ``embedding[i]`` is the k-subset represented by source action vertex ``i``.
    An ambient generator is written as the image tuple ``g[i]``. The routine
    first verifies that the supplied embedding is a complete copy of J(v,k).
    It then reconstructs ground points solely from their incidence stars in the
    represented action, canonically labels those stars, and proves that every
    supplied generator maps stars to stars and agrees with the induced set
    action on every Johnson vertex.

    The resulting ground action transports arbitrary source colorings exactly:
    a coloring of Johnson vertices is the same data as a coloring of the
    certified k-subsets, and the checked generator identities make this
    correspondence equivariant. In the v=2k case a complement automorphism
    does not map point-incidence stars to point-incidence stars, so it is
    rejected rather than silently treated as a ground permutation.
    """
    try:
        v = _strict_int(johnson_ground_size, "johnson_ground_size")
        k = _strict_int(johnson_subset_size, "johnson_subset_size")
    except ValueError as exc:
        return _fail(str(exc))

    if v < 4 or not 2 <= k <= v - 2:
        return _fail("Johnson parameters must satisfy v >= 4 and 2 <= k <= v-2", v=v, k=k)
    n = comb(v, k)
    if n <= v:
        return _fail("Johnson ground reduction must strictly shrink the recursive action measure", v=v, k=k, n=n)

    try:
        embedding_seq = _strict_sequence(embedding, "embedding")
        if len(embedding_seq) != n:
            raise ValueError("embedding length does not equal C(v,k)")
        normalized_embedding = tuple(
            _normalize_subset(raw, v=v, k=k, index=index)
            for index, raw in enumerate(embedding_seq)
        )
        expected = set(combinations(range(v), k))
        if len(set(normalized_embedding)) != n or set(normalized_embedding) != expected:
            raise ValueError("embedding is not a bijection onto all k-subsets of the Johnson ground")

        generator_seq = _strict_sequence(ambient_generators, "ambient_generators")
        generators = tuple(
            _normalize_permutation(raw, degree=n, index=index)
            for index, raw in enumerate(generator_seq)
        )
    except ValueError as exc:
        return _fail(str(exc), v=v, k=k, n=n)

    # Reconstruct ground points from incidence alone. Sorting the star
    # signatures removes any dependence on the caller's names 0,...,v-1.
    original_stars = tuple(
        tuple(index for index, subset in enumerate(normalized_embedding) if point in subset)
        for point in range(v)
    )
    if len(set(original_stars)) != v:
        return _fail("point-incidence stars do not distinguish every ground point", v=v, k=k, n=n)
    sorted_star_pairs = sorted((star, point) for point, star in enumerate(original_stars))
    canonical_label = {point: label for label, (_, point) in enumerate(sorted_star_pairs)}
    canonical_stars = tuple(star for star, _ in sorted_star_pairs)
    star_to_point = {star: point for point, star in enumerate(canonical_stars)}
    canonical_embedding = tuple(
        tuple(sorted(canonical_label[point] for point in subset))
        for subset in normalized_embedding
    )

    induced_pairs: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for gen_index, generator in enumerate(generators):
        ground_images: list[int] = []
        for star in canonical_stars:
            image_star = tuple(sorted(generator[vertex] for vertex in star))
            image_point = star_to_point.get(image_star)
            if image_point is None:
                return _fail(
                    f"ambient_generators[{gen_index}] does not preserve the point-incidence star family; non-ground/complement action rejected",
                    v=v,
                    k=k,
                    n=n,
                )
            ground_images.append(image_point)
        induced = tuple(ground_images)
        if len(set(induced)) != v:
            return _fail(
                f"ambient_generators[{gen_index}] does not induce a ground permutation",
                v=v,
                k=k,
                n=n,
            )
        for vertex, subset in enumerate(canonical_embedding):
            transported_subset = tuple(sorted(induced[point] for point in subset))
            if canonical_embedding[generator[vertex]] != transported_subset:
                return _fail(
                    f"ambient_generators[{gen_index}] fails exact Johnson set-action transport at vertex {vertex}",
                    v=v,
                    k=k,
                    n=n,
                )
        induced_pairs.append((generator, induced))

    # Pair sorting makes replay independent of the order in which a fixed
    # generator family is supplied. No group enumeration is performed.
    induced_pairs.sort()
    canonical_generators = tuple(pair[1] for pair in induced_pairs)
    canonical_ambient_generators = tuple(pair[0] for pair in induced_pairs)

    construction_work_bound = (2 + 2 * len(generators)) * n * k + len(generators) * n + v
    identity_payload = {
        "schema_version": SCHEMA_VERSION,
        "status": REDUCTION_STATUS,
        "source_action_degree": n,
        "johnson_ground_size": v,
        "johnson_subset_size": k,
        "child_ground_size": v,
        "canonical_vertex_subsets": canonical_embedding,
        "canonical_ground_stars": canonical_stars,
        "ambient_generators": canonical_ambient_generators,
        "induced_ground_generators": canonical_generators,
        "construction_work_bound": construction_work_bound,
    }
    reduction_identity = _sha256(identity_payload)

    return JohnsonGroundRelationalReductionEvidence(
        SCHEMA_VERSION,
        REDUCTION_STATUS,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        n,
        v,
        k,
        v,
        1.0,
        1.0,
        reduction_identity,
        canonical_embedding,
        canonical_stars,
        canonical_generators,
        construction_work_bound,
        "complete J(v,k) incidence reconstruction proves an exact one-child relational transport to the strictly smaller ground action; every ambient generator is verified on every Johnson vertex and complement/non-ground actions fail closed",
    )


def replay_johnson_ground_relational_reduction(
    evidence: JohnsonGroundRelationalReductionEvidence,
    *,
    johnson_ground_size: int,
    johnson_subset_size: int,
    embedding: Sequence[Sequence[int]],
    ambient_generators: Sequence[Sequence[int]],
) -> bool:
    if not isinstance(evidence, JohnsonGroundRelationalReductionEvidence) or not evidence.certified:
        return False
    replay = certify_johnson_ground_relational_reduction(
        johnson_ground_size=johnson_ground_size,
        johnson_subset_size=johnson_subset_size,
        embedding=embedding,
        ambient_generators=ambient_generators,
    )
    return bool(replay.certified and replay == evidence and replay.reduction_identity == evidence.reduction_identity)


__all__ = [
    "JohnsonGroundRelationalReductionEvidence",
    "certify_johnson_ground_relational_reduction",
    "replay_johnson_ground_relational_reduction",
]
