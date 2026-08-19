from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import combinations
from typing import Tuple

from permutation_group_schreier import StabilizerChain, identity


@dataclass(frozen=True)
class CanonicalOrbitalSizeRelation:
    status: str
    degree: int
    signature_count: int
    pair_weights: Tuple[Tuple[Tuple[int, int], int], ...]
    signatures: Tuple[Tuple[int, Tuple[int, int]], ...]
    max_ordered_pair_orbit: int
    reason: str


def _gens(group: StabilizerChain):
    return group.original_generators or (identity(group.degree),)


def _ordered_pair_orbit_size(group: StabilizerChain, source, cache):
    if source in cache:
        return cache[source]
    gens = _gens(group)
    seen = {source}
    q = deque([source])
    while q:
        u, v = q.popleft()
        for g in gens:
            nxt = (g[u], g[v])
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    size = len(seen)
    for item in seen:
        cache[item] = size
    return size


def canonical_orbital_size_relation(group: StabilizerChain) -> CanonicalOrbitalSizeRelation:
    """Color unordered pairs by canonically ordered orbital-size signatures.

    For {u,v}, use the sorted pair of ordered-orbit sizes
    (|Orb_G(u,v)|, |Orb_G(v,u)|). Orbit cardinalities are invariant under every
    relabeling/conjugation of the permutation action, so sorting the distinct
    signatures yields canonical integer pair colors without naming individual
    orbitals. This is a safe coarsening: equal-size orbitals may merge, but no
    label-dependent distinction is introduced.
    """
    n = group.degree
    if n < 2:
        raise ValueError("degree must be at least 2")
    cache = {}
    raw = {}
    max_orbit = 0
    for u, v in combinations(range(n), 2):
        a = _ordered_pair_orbit_size(group, (u, v), cache)
        b = _ordered_pair_orbit_size(group, (v, u), cache)
        signature = tuple(sorted((a, b)))
        raw[(u, v)] = signature
        max_orbit = max(max_orbit, a, b)

    unique = tuple(sorted(set(raw.values())))
    ids = {sig: i for i, sig in enumerate(unique)}
    return CanonicalOrbitalSizeRelation(
        "canonical_orbital_size_pair_relation",
        n,
        len(unique),
        tuple(((u, v), ids[sig]) for (u, v), sig in sorted(raw.items())),
        tuple((ids[sig], sig) for sig in unique),
        max_orbit,
        "unordered pair colors are canonical IDs of ordered-pair orbit-size signatures; equal-size orbitals are intentionally coarsened",
    )
