"""Exact unary/binary relation-image transporter cosets over explicit groups.

The finite relation structure is encoded as a Boolean string on a faithful
auxiliary action: a neutral point layer plus every unary/binary tuple slot.
The rev251 independent replay verifier then checks the complete match set and
target-stabilizer right-coset reconstruction.  Exactness is deliberately
limited to the explicitly enumerated candidate group.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from bounded_arity_relation_image_solver import BoundedArityRelationImage
from exact_result_replay_verifier_v1 import (
    ReplayCaps,
    ReplayStatus,
    ReplayVerification,
    build_certificate,
    verify_exact_result_replay,
)


Permutation = tuple[int, ...]


@dataclass(frozen=True)
class BoundedRelationImageCoset:
    status: str
    exact: bool
    complete: bool
    degree: int
    auxiliary_degree: int
    candidate_group_size: int
    match_count: int
    representative: Permutation | None
    target_stabilizer: tuple[Permutation, ...]
    matches: tuple[Permutation, ...]
    reserved_group_compositions: int
    reserved_action_point_checks: int
    replay: ReplayVerification | None
    reason: str


def _closed(
    status: str,
    *,
    degree: int,
    auxiliary_degree: int,
    group_size: int,
    compositions: int,
    checks: int,
    reason: str,
    exact: bool = False,
    complete: bool = False,
) -> BoundedRelationImageCoset:
    return BoundedRelationImageCoset(
        status, exact, complete, degree, auxiliary_degree, group_size, 0, None,
        (), (), compositions, checks, None, reason,
    )


def _normalize_group(raw_group: Iterable[Iterable[int]], degree: int) -> tuple[Permutation, ...]:
    try:
        group = tuple(tuple(item) for item in raw_group)
    except TypeError as exc:
        raise TypeError("candidate_group must be an iterable of permutations") from exc
    for permutation in group:
        if len(permutation) != degree or any(type(point) is not int for point in permutation):
            raise ValueError("every candidate must be an integer permutation of the domain")
        if set(permutation) != set(range(degree)):
            raise ValueError("every candidate must be a permutation of range(degree)")
    return group


def _relation_signature(image: BoundedArityRelationImage) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((relation.name, relation.arity) for relation in image.relations))


def _feature_string(image: BoundedArityRelationImage) -> tuple[object, ...]:
    n = len(image.domain)
    index = {value: point for point, value in enumerate(image.domain)}
    result: list[object] = [("point", False)] * n
    for relation in sorted(image.relations, key=lambda item: item.name):
        indexed = {
            tuple(index[value] for value in relation_tuple)
            for relation_tuple in relation.tuples
        }
        if relation.arity == 1:
            result.extend((relation.name, (point,) in indexed) for point in range(n))
        else:
            result.extend(
                (relation.name, (left, right) in indexed)
                for left in range(n)
                for right in range(n)
            )
    return tuple(result)


def _induced_permutation(
    permutation: Permutation,
    signature: tuple[tuple[str, int], ...],
    degree: int,
) -> Permutation:
    result = list(permutation)  # faithful neutral point layer
    offset = degree
    for _name, arity in signature:
        if arity == 1:
            result.extend(offset + permutation[point] for point in range(degree))
            offset += degree
        else:
            result.extend(
                offset + permutation[left] * degree + permutation[right]
                for left in range(degree)
                for right in range(degree)
            )
            offset += degree * degree
    return tuple(result)


def exact_bounded_relation_image_coset(
    source: BoundedArityRelationImage,
    target: BoundedArityRelationImage,
    candidate_group: Iterable[Iterable[int]],
    *,
    caps: ReplayCaps = ReplayCaps(),
) -> BoundedRelationImageCoset:
    """Return the complete exact transporter set or fail closed.

    Resource quantities needed by rev251 are checked before any candidate is
    matched against the relation strings.  The returned exact result is only
    relative to ``candidate_group``; it does not certify that this group is an
    ambient action supplied by an upstream CRX1 reduction.
    """
    if not isinstance(source, BoundedArityRelationImage) or not isinstance(
        target, BoundedArityRelationImage
    ):
        raise TypeError("source and target must be BoundedArityRelationImage values")
    caps.validate()
    degree = len(source.domain)
    if len(target.domain) != degree:
        return _closed(
            "exact_empty_domain_size_mismatch", degree=degree,
            auxiliary_degree=0, group_size=0, compositions=0, checks=0,
            exact=True, complete=True,
            reason="different finite domain sizes imply an exact empty transporter",
        )
    source_signature = _relation_signature(source)
    if _relation_signature(target) != source_signature:
        return _closed(
            "exact_empty_relation_signature_mismatch", degree=degree,
            auxiliary_degree=0, group_size=0, compositions=0, checks=0,
            exact=True, complete=True,
            reason="different named unary/binary signatures imply an exact empty transporter",
        )

    group = _normalize_group(candidate_group, degree)
    group_size = len(group)
    auxiliary_degree = degree + sum(
        degree if arity == 1 else degree * degree
        for _name, arity in source_signature
    )
    compositions = group_size * group_size
    checks = 2 * group_size * auxiliary_degree
    if auxiliary_degree > caps.max_degree:
        return _closed(
            "undetermined_auxiliary_degree_cap", degree=degree,
            auxiliary_degree=auxiliary_degree, group_size=group_size,
            compositions=compositions, checks=checks,
            reason="faithful relation-incidence action exceeds max_degree; no candidate match started",
        )
    if group_size > caps.max_group_size:
        return _closed(
            "undetermined_candidate_group_cap", degree=degree,
            auxiliary_degree=auxiliary_degree, group_size=group_size,
            compositions=compositions, checks=checks,
            reason="explicit candidate group exceeds max_group_size; no candidate match started",
        )
    if compositions > caps.max_group_compositions:
        return _closed(
            "undetermined_group_composition_cap", degree=degree,
            auxiliary_degree=auxiliary_degree, group_size=group_size,
            compositions=compositions, checks=checks,
            reason="complete group-closure replay exceeds its cap; no candidate match started",
        )
    if checks > caps.max_action_point_checks:
        return _closed(
            "undetermined_action_check_cap", degree=degree,
            auxiliary_degree=auxiliary_degree, group_size=group_size,
            compositions=compositions, checks=checks,
            reason="complete source/target action replay exceeds its cap; no candidate match started",
        )

    source_features = _feature_string(source)
    target_features = _feature_string(target)
    induced = tuple(
        _induced_permutation(permutation, source_signature, degree)
        for permutation in group
    )
    matches = tuple(
        permutation
        for permutation, action in zip(group, induced)
        if all(source_features[i] == target_features[action[i]] for i in range(auxiliary_degree))
    )
    match_set = set(matches)
    induced_matches = tuple(
        action for permutation, action in zip(group, induced) if permutation in match_set
    )
    certificate = build_certificate(
        source=source_features,
        target=target_features,
        candidate_group=induced,
        claimed_matches=induced_matches,
        universe_label="bounded-unary-binary-relation-incidence-action-v1",
    )
    replay = verify_exact_result_replay(certificate, caps=caps)
    if not replay.accepted:
        return BoundedRelationImageCoset(
            f"fail_closed_replay_{replay.status.value}", False, False, degree,
            auxiliary_degree, group_size, 0, None, (), (), compositions,
            checks, replay, replay.reason,
        )

    target_stabilizer = tuple(
        permutation
        for permutation, action in zip(group, induced)
        if all(target_features[i] == target_features[action[i]] for i in range(auxiliary_degree))
    )
    ordered_matches = tuple(sorted(matches))
    return BoundedRelationImageCoset(
        "exact_bounded_relation_image_transporter_coset"
        if ordered_matches else "exact_empty_bounded_relation_image_transporter",
        True, True, degree, auxiliary_degree, group_size, len(ordered_matches),
        ordered_matches[0] if ordered_matches else None,
        tuple(sorted(target_stabilizer)), ordered_matches, compositions, checks,
        replay,
        "complete unary/binary incidence action replay and target-stabilizer coset verification succeeded",
    )
