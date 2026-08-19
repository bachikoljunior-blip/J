from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from permutation_group_schreier import Permutation, StabilizerChain, compose, identity, orbit_transversal, schreier_stabilizer_chain
from coset_stabilizer_primitives import RightCoset, pointwise_stabilizer_chain


class NodeLimit(Exception):
    pass


@dataclass
class _Budget:
    limit: int
    used: int = 0

    def tick(self) -> None:
        self.used += 1
        if self.used > self.limit:
            raise NodeLimit


@dataclass(frozen=True)
class RecursiveCosetIntersection:
    status: str
    coset: Optional[RightCoset]
    intersection_order: int
    search_nodes: int
    reason: str


def _gens(chain: StabilizerChain):
    e = identity(chain.degree)
    return chain.original_generators or (e,)


def _subgroup_leq(a: StabilizerChain, b: StabilizerChain) -> bool:
    return a.degree == b.degree and all(b.contains(g) for g in a.original_generators)


def _refine_to_image(c: RightCoset, domain_point: int, image: int) -> Optional[RightCoset]:
    H = c.subgroup
    n = H.degree
    u = c.representative[domain_point]
    _, trans = orbit_transversal(u, _gens(H), n)
    if image not in trans:
        return None
    t = trans[image]
    stab = pointwise_stabilizer_chain(H, [image])
    return RightCoset(stab, compose(c.representative, t))


def _find_witness(a: RightCoset, b: RightCoset, budget: _Budget) -> Optional[Permutation]:
    budget.tick()
    H, K = a.subgroup, b.subgroup
    if H.degree != K.degree:
        raise ValueError("degree mismatch")

    if a.contains(b.representative):
        return b.representative
    if b.contains(a.representative):
        return a.representative
    if H.order == 1 and K.order == 1:
        return None

    n = H.degree
    best = None
    for i in range(n):
        oh, _ = orbit_transversal(a.representative[i], _gens(H), n)
        ok, _ = orbit_transversal(b.representative[i], _gens(K), n)
        common = tuple(sorted(set(oh) & set(ok)))
        if not common:
            return None
        if len(oh) > 1 or len(ok) > 1:
            score = (len(common), len(oh) * len(ok), i)
            if best is None or score < best[0]:
                best = (score, i, common)

    if best is None:
        return None

    _, i, common = best
    for y in common:
        aa = _refine_to_image(a, i, y)
        bb = _refine_to_image(b, i, y)
        if aa is None or bb is None:
            continue
        witness = _find_witness(aa, bb, budget)
        if witness is not None:
            return witness
    return None


def _intersect_subgroups(H: StabilizerChain, K: StabilizerChain, budget: _Budget) -> StabilizerChain:
    budget.tick()
    if H.degree != K.degree:
        raise ValueError("degree mismatch")
    n = H.degree
    e = identity(n)

    if H.order == 1 or K.order == 1:
        return schreier_stabilizer_chain([e])
    if _subgroup_leq(H, K):
        return H
    if _subgroup_leq(K, H):
        return K

    best = None
    for p in range(n):
        oh, th = orbit_transversal(p, _gens(H), n)
        ok, tk = orbit_transversal(p, _gens(K), n)
        if len(oh) == 1 and len(ok) == 1:
            continue
        common = tuple(sorted(set(oh) & set(ok)))
        score = (len(common), len(oh) * len(ok), p)
        if best is None or score < best[0]:
            best = (score, p, common, th, tk)

    if best is None:
        return schreier_stabilizer_chain([e])

    _, p, common, th, tk = best
    Hp = pointwise_stabilizer_chain(H, [p])
    Kp = pointwise_stabilizer_chain(K, [p])
    Gp = _intersect_subgroups(Hp, Kp, budget)

    generators = list(Gp.original_generators)
    orbit_witnesses = []
    for y in common:
        Hy = pointwise_stabilizer_chain(H, [y])
        Ky = pointwise_stabilizer_chain(K, [y])
        AH = RightCoset(Hy, th[y])
        BK = RightCoset(Ky, tk[y])
        witness = _find_witness(AH, BK, budget)
        if witness is None:
            continue
        if witness[p] != y or not H.contains(witness) or not K.contains(witness):
            raise AssertionError("invalid intersection-orbit witness")
        orbit_witnesses.append((y, witness))
        if witness != e:
            generators.append(witness)

    G = schreier_stabilizer_chain(generators or [e])
    expected_order = Gp.order * len(orbit_witnesses)
    if G.order != expected_order:
        raise AssertionError("orbit-stabilizer reconstruction mismatch")
    if not all(H.contains(g) and K.contains(g) for g in G.original_generators):
        raise AssertionError("constructed subgroup escaped H intersection K")
    return G


def right_coset_intersection_recursive(a: RightCoset, b: RightCoset, *, max_nodes: int = 100000) -> RecursiveCosetIntersection:
    """Exact right-coset intersection without relation-image-orbit enumeration.

    A witness is found by recursively constraining point images.  H intersection K
    is then reconstructed by orbit-stabilizer recursion: the point stabilizer is
    intersected recursively, while each feasible common orbit image is certified
    by an exact transporter-coset witness.  Work is bounded by `max_nodes`; limit
    exhaustion returns fail-closed rather than an approximate certificate.
    """
    budget = _Budget(max_nodes)
    try:
        H, K = a.subgroup, b.subgroup
        if H.degree != K.degree:
            raise ValueError("degree mismatch")
        witness = _find_witness(a, b, budget)
        if witness is None:
            return RecursiveCosetIntersection(
                "empty_intersection", None, 0, budget.used,
                "recursive point-image transporter search proved disjoint",
            )
        G = _intersect_subgroups(H, K, budget)
        if not a.contains(witness) or not b.contains(witness):
            raise AssertionError("returned witness is not in both cosets")
        return RecursiveCosetIntersection(
            "exact_intersection_coset", RightCoset(G, witness), G.order, budget.used,
            "recursive point-image search plus exact orbit-stabilizer subgroup-intersection reconstruction",
        )
    except NodeLimit:
        return RecursiveCosetIntersection(
            "undetermined_node_limit", None, 0, budget.used,
            "recursive exact search exceeded max_nodes",
        )
