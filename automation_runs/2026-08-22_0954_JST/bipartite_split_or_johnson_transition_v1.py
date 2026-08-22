from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Iterable, Mapping


@dataclass(frozen=True)
class CorrectedSOJTransitionCertificate:
    status: str
    transition_kind: str
    theorem_input_gate: bool
    canonical: bool
    exact: bool
    progress_certified: bool
    multiplicative_cost: float
    max_multiplicative_cost: float
    small_size_before: int | None
    small_size_after: int | None
    alpha: float | None
    johnson_ground_size: int | None
    johnson_subset_size: int | None
    johnson_vertex_count: int | None
    reason: str


def _strict_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _strict_real(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


def _certificate_float(value: object) -> float:
    if _strict_real(value):
        return float(value)
    return float("nan")


def _base_gate(
    *,
    theorem_input_gate: bool,
    canonical: bool,
    exact: bool,
    multiplicative_cost: float,
    max_multiplicative_cost: float,
) -> str | None:
    if not theorem_input_gate:
        return "bipartite Split-or-Johnson theorem input gate is not certified"
    if not canonical:
        return "recursive transition is not certified canonical"
    if not exact:
        return "recursive transition is not certified exact"
    if not _strict_real(multiplicative_cost):
        return "multiplicative cost must be a real number"
    if not _strict_real(max_multiplicative_cost):
        return "multiplicative cost bound must be a real number"
    cost = float(multiplicative_cost)
    max_cost = float(max_multiplicative_cost)
    if not isfinite(cost) or cost <= 0:
        return "multiplicative cost must be finite and positive"
    if not isfinite(max_cost) or max_cost <= 0:
        return "multiplicative cost bound must be finite and positive"
    if cost > max_cost:
        return "multiplicative cost exceeds the certified bound"
    return None


def certify_small_part_reduction(
    *,
    theorem_input_gate: bool,
    small_size_before: int,
    small_size_after: int,
    alpha: float,
    canonical: bool,
    exact: bool,
    multiplicative_cost: float,
    max_multiplicative_cost: float,
) -> CorrectedSOJTransitionCertificate:
    """Certify the corrected recursive edge that shrinks the auxiliary part.

    This does not infer progress from a phase name.  The existing bipartite
    theorem input gate must already have fired, and this edge is accepted only
    when a canonical exact output reduces the auxiliary/small part by the same
    strict constant-factor inequality used by the corrected recursion.
    """
    reason = _base_gate(
        theorem_input_gate=theorem_input_gate,
        canonical=canonical,
        exact=exact,
        multiplicative_cost=multiplicative_cost,
        max_multiplicative_cost=max_multiplicative_cost,
    )
    before = small_size_before if _strict_int(small_size_before) else None
    after = small_size_after if _strict_int(small_size_after) else None
    alpha_value = float(alpha) if _strict_real(alpha) else None
    if reason is None and before is None:
        reason = "small_size_before must be an integer"
    if reason is None and after is None:
        reason = "small_size_after must be an integer"
    if reason is None and before <= 0:
        reason = "small_size_before must be positive"
    if reason is None and not 0 <= after < before:
        reason = "recursive edge must strictly reduce the auxiliary part"
    if reason is None and (alpha_value is None or not isfinite(alpha_value)):
        reason = "alpha must be a finite real number"
    if reason is None and not 2 / 3 <= alpha_value < 1.0:
        reason = "alpha must lie in [2/3,1)"
    if reason is None and not after < alpha_value * before:
        reason = "constant-factor auxiliary-part reduction is not certified"
    ok = reason is None
    return CorrectedSOJTransitionCertificate(
        "certified_corrected_soj_small_part_reduction" if ok else "corrected_soj_transition_not_certified",
        "small_part_reduction",
        bool(theorem_input_gate),
        bool(canonical),
        bool(exact),
        ok,
        _certificate_float(multiplicative_cost),
        _certificate_float(max_multiplicative_cost),
        before,
        after,
        alpha_value,
        None,
        None,
        None,
        "canonical exact constant-factor auxiliary-part reduction certified" if ok else str(reason),
    )


def certify_explicit_johnson_embedding(
    *,
    theorem_input_gate: bool,
    embedding: Iterable[Iterable[int]],
    pair_relation_distance: Mapping[tuple[int, int], int],
    johnson_ground_size: int,
    johnson_subset_size: int,
    canonical: bool,
    exact: bool,
    multiplicative_cost: float,
    max_multiplicative_cost: float,
) -> CorrectedSOJTransitionCertificate:
    """Certify an explicit Johnson-scheme structural transition.

    ``embedding[i]`` is the explicit k-subset coordinate of structural vertex i.
    ``pair_relation_distance`` must contain every unordered pair ``(i,j)`` with
    ``i < j`` and its Johnson relation distance ``k-|embedding[i]∩embedding[j]|``.
    Thus a structural label by itself can never pass this certificate.
    """
    reason = _base_gate(
        theorem_input_gate=theorem_input_gate,
        canonical=canonical,
        exact=exact,
        multiplicative_cost=multiplicative_cost,
        max_multiplicative_cost=max_multiplicative_cost,
    )
    m = johnson_ground_size if _strict_int(johnson_ground_size) else None
    k = johnson_subset_size if _strict_int(johnson_subset_size) else None
    coords: tuple[frozenset[int], ...] = ()
    try:
        raw_coords = tuple(tuple(xs) for xs in embedding)
    except (TypeError, ValueError):
        raw_coords = ()
        if reason is None:
            reason = "explicit Johnson embedding must be an iterable of integer iterables"
    if reason is None and m is None:
        reason = "Johnson ground size must be an integer"
    if reason is None and k is None:
        reason = "Johnson subset size must be an integer"
    if reason is None and m < 4:
        reason = "Johnson ground must have size at least 4"
    if reason is None and not 2 <= k <= m - 2:
        reason = "Johnson subset size must be nontrivial"
    if reason is None and not raw_coords:
        reason = "explicit Johnson embedding is empty"
    if reason is None and any(not all(_strict_int(x) for x in xs) for xs in raw_coords):
        reason = "embedding coordinates must be integers"
    if reason is None:
        coords = tuple(frozenset(xs) for xs in raw_coords)
    if reason is None and any(len(xs) != k or any(x < 0 or x >= m for x in xs) for xs in coords):
        reason = "embedding contains a malformed Johnson coordinate"
    if reason is None and len(set(coords)) != len(coords):
        reason = "Johnson embedding is not injective"
    expected_keys = {(i, j) for i in range(len(coords)) for j in range(i + 1, len(coords))}
    try:
        supplied_keys = set(pair_relation_distance)
    except TypeError:
        supplied_keys = set()
        if reason is None:
            reason = "pair relation certificate must be a mapping"
    if reason is None and supplied_keys != expected_keys:
        reason = "pair relation certificate must cover every unordered embedded pair exactly once"
    if reason is None:
        for i, j in sorted(expected_keys):
            value = pair_relation_distance[(i, j)]
            expected = k - len(coords[i] & coords[j])
            if not _strict_int(value) or value != expected:
                reason = "pair relation does not equal the explicit Johnson intersection relation"
                break
    ok = reason is None
    return CorrectedSOJTransitionCertificate(
        "certified_corrected_soj_explicit_johnson_embedding" if ok else "corrected_soj_transition_not_certified",
        "johnson_embedding",
        bool(theorem_input_gate),
        bool(canonical),
        bool(exact),
        ok,
        _certificate_float(multiplicative_cost),
        _certificate_float(max_multiplicative_cost),
        None,
        None,
        None,
        m,
        k,
        len(coords),
        "canonical exact explicit Johnson relation embedding certified" if ok else str(reason),
    )
