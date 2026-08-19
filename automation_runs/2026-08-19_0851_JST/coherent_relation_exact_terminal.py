from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Optional

import numpy as np

from group_pruned_canonical_label import exact_group_pruned_canonical_label


@dataclass(frozen=True)
class CoherentRelationTerminalCertificate:
    status: str
    quotient_size: int
    incidence_graph_size: int
    canonical_code: Optional[bytes]
    automorphism_order: int
    states_explored: int
    reason: str


def canonicalize_pair_relation_terminal(
    quotient_size: int,
    pair_weights,
    *,
    max_quotient_size: int = 24,
    max_states: int = 500000,
    max_group_nodes: int = 500000,
) -> CoherentRelationTerminalCertificate:
    """Exact bounded terminal canonicalization for a complete edge-colored relation.

    The pair-colored quotient is encoded as a typed incidence graph: one point
    vertex per quotient point and one pair vertex per unordered pair, whose vertex
    attribute contains the pair color. Pair vertices are adjacent exactly to their
    two endpoints. This encoding is information-preserving and converts pair-color
    isomorphism into ordinary attributed-graph isomorphism. rev112 then supplies an
    exact fail-closed canonical code.

    The O(m^2) incidence expansion is intentionally a bounded terminal only; it is
    not used as the claimed worst-case quasipolynomial large-domain route.
    """
    m = int(quotient_size)
    if m < 2:
        raise ValueError("quotient_size must be at least 2")
    if max_quotient_size < 2:
        raise ValueError("max_quotient_size must be at least 2")
    if m > max_quotient_size:
        return CoherentRelationTerminalCertificate(
            "undetermined_size_limit", m, 0, None, 0, 0,
            "quotient exceeds bounded exact-terminal size",
        )

    pairs = {tuple(map(int, p)): int(w) for p, w in pair_weights}
    expected = {(u, v) for u, v in combinations(range(m), 2)}
    if set(pairs) != expected:
        raise ValueError("pair_weights must contain each unordered pair exactly once")

    pair_list = tuple(sorted(pairs))
    N = m + len(pair_list)
    adjacency = np.zeros((N, N), dtype=np.uint8)
    # Two numeric attributes: vertex type and pair color. Point vertices use a
    # fixed zero color; pair vertices have type 1 and the exact integer weight.
    attrs = np.zeros((N, 2), dtype=float)
    for j, (u, v) in enumerate(pair_list):
        q = m + j
        adjacency[u, q] = adjacency[q, u] = 1
        adjacency[v, q] = adjacency[q, v] = 1
        attrs[q, 0] = 1.0
        attrs[q, 1] = float(pairs[(u, v)])

    cert = exact_group_pruned_canonical_label(
        (adjacency, attrs),
        max_states=max_states,
        max_group_nodes=max_group_nodes,
    )
    if cert.status != "exact_canonical_label":
        return CoherentRelationTerminalCertificate(
            cert.status, m, N, None, cert.automorphism_order,
            cert.states_explored, cert.reason,
        )
    return CoherentRelationTerminalCertificate(
        "exact_pair_relation_canonical_code", m, N, cert.canonical_code,
        cert.automorphism_order, cert.states_explored,
        "typed pair-incidence encoding canonicalized exactly by rev112 group-pruned IR",
    )
