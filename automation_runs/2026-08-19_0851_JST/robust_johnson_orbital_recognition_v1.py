from __future__ import annotations

from collections import deque
from itertools import combinations

from johnson_pair_relation_recognizer import (
    JohnsonRelationCertificate,
    recognize_johnson_pair_relation,
)
from permutation_group_schreier import identity


def _unordered_pair_orbits(group):
    """Return the exact G-orbits on unordered pairs as an unlabeled family.

    The family itself is equivariant under conjugation/relabeling.  We do not
    assign semantic color names to individual orbitals; every member is tested as
    a possible Johnson adjacency relation and any accepted coordinate system is
    subsequently required to decode/re-induce the supplied ambient generators.
    """
    n = group.degree
    generators = group.original_generators or (identity(n),)
    remaining = set(combinations(range(n), 2))
    out = []
    while remaining:
        seed = min(remaining)
        seen = {seed}
        q = deque([seed])
        while q:
            u, v = q.popleft()
            for g in generators:
                nxt = tuple(sorted((g[u], g[v])))
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        remaining.difference_update(seen)
        out.append(frozenset(seen))
    return tuple(out)


def recognize_johnson_from_exact_unordered_orbitals(
    group,
    *,
    max_degree: int = 128,
    max_nodes_per_candidate: int = 500000,
):
    """Recover Johnson coordinates without merging equal-size pair orbitals.

    `canonical_orbital_size_relation` deliberately merges orbitals having the same
    cardinality.  That safe coarsening can erase Johnson distance colors (the
    v=2k complement-expanded cases expose this concretely).  For bounded current
    degree, this fallback enumerates the exact *family* of G-orbits on unordered
    pairs and tests each orbit relation itself.  No label-dependent orbital name
    is trusted: acceptance still requires an exact Johnson graph isomorphism
    coset, and the caller must decode/re-induce every supplied generator.

    Degrees above the explicit cap fail closed; this helper is a certification
    repair, not a substitute for the large relational/local-certificate W1 path.
    """
    n = group.degree
    if n < 2:
        raise ValueError("degree must be at least 2")
    if max_degree < 2 or max_nodes_per_candidate < 1:
        raise ValueError("invalid robust Johnson recognition caps")
    if n > max_degree:
        return JohnsonRelationCertificate(
            "undetermined_exact_orbital_degree_cap",
            None, None, None, None, 0, 0,
            "current Johnson-domain degree exceeds the explicit exact-orbital certification cap",
        )

    all_pairs = tuple(combinations(range(n), 2))
    total_nodes = 0
    any_undetermined = False
    candidates = []
    for orbit in _unordered_pair_orbits(group):
        weights = tuple((pair, 1 if pair in orbit else 0) for pair in all_pairs)
        cert = recognize_johnson_pair_relation(
            n,
            weights,
            max_nodes_per_candidate=max_nodes_per_candidate,
        )
        total_nodes += cert.search_nodes
        if cert.status == "exact_johnson_color_relation":
            candidates.append(cert)
        elif cert.status == "undetermined_search_limit":
            any_undetermined = True

    if candidates:
        # Parameter choice is invariant.  Coordinate-representative ambiguity is
        # harmless only after the caller's exact generator decode/re-induction
        # check, which is why this routine is not used as a standalone reduction.
        cert = min(
            candidates,
            key=lambda c: (
                int(c.ground_size or 0),
                int(c.subset_size or 0),
                int(c.relation_weight or 0),
                tuple(c.isomorphism_coset.representative) if c.isomorphism_coset else (),
            ),
        )
        return JohnsonRelationCertificate(
            "exact_johnson_color_relation",
            cert.relation_weight,
            cert.ground_size,
            cert.subset_size,
            cert.isomorphism_coset,
            cert.isomorphism_count,
            total_nodes,
            "an exact unordered-pair orbital, without orbital-size merging, is Johnson; complete coordinate isomorphisms are certified and require caller-side generator round-trip validation",
        )

    if any_undetermined:
        return JohnsonRelationCertificate(
            "undetermined_search_limit",
            None, None, None, None, 0, total_nodes,
            "at least one exact unordered-orbital Johnson comparison exceeded the GI search bound",
        )
    return JohnsonRelationCertificate(
        "certified_no_johnson_exact_orbital_relation",
        None, None, None, None, 0, total_nodes,
        "every exact unordered-pair orbital was certified non-Johnson within the explicit robust-recognition boundary",
    )
