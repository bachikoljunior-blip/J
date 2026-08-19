from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Optional, Tuple

from canonical_orbital_size_relation import canonical_orbital_size_relation
from johnson_pair_relation_recognizer import recognize_johnson_pair_relation
from permutation_group_schreier import StabilizerChain, identity, schreier_stabilizer_chain
from primitive_johnson_ground_terminal_v1 import _induced_subset_permutation


@dataclass(frozen=True)
class JohnsonGroundActionCertificate:
    status: str
    original_degree: int
    ground_size: int
    subset_size: int
    coordinate: Tuple[int, ...]
    ground_group: Optional[StabilizerChain]
    ground_generators: Tuple[Tuple[int, ...], ...]
    original_group_order: int
    ground_group_order: int
    recognition_search_nodes: int
    reason: str


def _standard_action(original_perm, coordinate):
    out = [0] * len(coordinate)
    for original, standard_index in enumerate(coordinate):
        out[standard_index] = coordinate[original_perm[original]]
    return tuple(out)


def _star_families(standard_subsets, ground_size):
    stars = []
    for x in range(ground_size):
        stars.append(frozenset(i for i, subset in enumerate(standard_subsets) if x in subset))
    return tuple(stars)


def recover_johnson_ground_action(
    group: StabilizerChain,
    *,
    max_recognition_nodes: int = 500000,
) -> JohnsonGroundActionCertificate:
    """Recover H's faithful action on the ground of a certified J(v,k).

    A Johnson-coordinate isomorphism sends current-domain points to standard
    k-subsets. For every supplied generator of H, we conjugate its current-domain
    action into subset coordinates and recover the underlying ground permutation
    from its action on the canonical star family {S:x in S}.  Each recovered
    generator is re-induced to C(v,k) and must reproduce the original generator
    exactly.  Finally the Schreier-certified ground-group order must equal H's
    order, proving that the recovered homomorphism is faithful on the represented
    subgroup.

    If a v=2k complement-type automorphism occurs, star families are not mapped
    to star families and the certificate fails closed rather than silently
    dropping the complement coset.
    """
    m = group.degree
    if m < 2 or max_recognition_nodes < 1:
        raise ValueError("invalid Johnson ground-action parameters")
    relation = canonical_orbital_size_relation(group)
    johnson = recognize_johnson_pair_relation(
        m, relation.pair_weights, max_nodes_per_candidate=max_recognition_nodes
    )
    if johnson.status != "exact_johnson_color_relation" or johnson.isomorphism_coset is None:
        return JohnsonGroundActionCertificate(
            "undetermined_not_certified_johnson", m,
            int(johnson.ground_size or 0), int(johnson.subset_size or 0), (),
            None, (), group.order, 0, johnson.search_nodes, johnson.reason,
        )

    v = int(johnson.ground_size)
    k = int(johnson.subset_size)
    coordinate = tuple(johnson.isomorphism_coset.representative)
    standard_subsets = tuple(combinations(range(v), k))
    if len(standard_subsets) != m or sorted(coordinate) != list(range(m)):
        raise AssertionError("invalid Johnson coordinate certificate")
    stars = _star_families(standard_subsets, v)
    star_to_vertex = {star: x for x, star in enumerate(stars)}
    if len(star_to_vertex) != v:
        raise AssertionError("Johnson stars are not distinct")

    ground_gens = []
    for g in (group.original_generators or (identity(m),)):
        gstd = _standard_action(g, coordinate)
        sigma = []
        for star in stars:
            moved = frozenset(gstd[i] for i in star)
            y = star_to_vertex.get(moved)
            if y is None:
                return JohnsonGroundActionCertificate(
                    "undetermined_johnson_complement_or_nonstandard_action",
                    m, v, k, coordinate, None, tuple(ground_gens),
                    group.order, 0, johnson.search_nodes,
                    "a represented Johnson automorphism does not send ground-point stars to ground-point stars; this includes the v=2k complement coset and must be handled relation-level",
                )
            sigma.append(y)
        sigma = tuple(sigma)
        if sorted(sigma) != list(range(v)):
            raise AssertionError("recovered Johnson ground generator is not a permutation")
        reproduced = _induced_subset_permutation(
            coordinate, sigma, v, k, complement=False
        )
        if reproduced != tuple(g):
            raise AssertionError("recovered ground generator does not reproduce current-domain generator")
        ground_gens.append(sigma)

    ground = schreier_stabilizer_chain(ground_gens or (identity(v),))
    if ground.order != group.order:
        return JohnsonGroundActionCertificate(
            "undetermined_nonfaithful_ground_recovery", m, v, k, coordinate,
            ground, tuple(ground_gens), group.order, ground.order,
            johnson.search_nodes,
            "recovered ground action order differs from the represented current-domain subgroup; exact recursion is withheld",
        )
    return JohnsonGroundActionCertificate(
        "exact_johnson_ground_action", m, v, k, coordinate,
        ground, tuple(ground_gens), group.order, ground.order,
        johnson.search_nodes,
        "every current-domain generator was exactly recovered from Johnson star transport, re-induced, and the ground Schreier order matches H",
    )
