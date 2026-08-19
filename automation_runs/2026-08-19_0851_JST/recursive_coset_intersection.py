from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from permutation_group_schreier import Permutation, StabilizerChain, compose, identity, orbit_transversal, schreier_stabilizer_chain
from coset_stabilizer_primitives import RightCoset, point_stabilizer_generators


class _NodeLimit(Exception):
    pass


@dataclass
class _Budget:
    limit: int
    used: int = 0

    def tick(self) -> None:
        self.used += 1
        if self.used > self.limit:
            raise _NodeLimit


@dataclass(frozen=True)
class RecursiveCosetIntersection:
    status: str
    coset: Optional[RightCoset]
    intersection_order: int
    search_nodes: int
    reason: str


def _gens(chain: StabilizerChain):
    return chain.original_generators or (identity(chain.degree),)


def _point_stabilizer(chain: StabilizerChain, point: int) -> StabilizerChain:
    e = identity(chain.degree)
    gens = point_stabilizer_generators(_gens(chain), point)
    return schreier_stabilizer_chain(gens or (e,))


def _subgroup_leq(a: StabilizerChain, b: StabilizerChain) -> bool:
    return a.degree == b.degree and all(b.contains(g) for g in a.original_generators)


def _find_common(a: RightCoset, b: RightCoset, budget: _Budget) -> Optional[Permutation]:
    """Find one element of aH intersect bK by recursively fixing point images."""
    budget.tick()
    H, K = a.subgroup, b.subgroup
    n = H.degree

    # Membership through the stabilizer chain gives immediate witnesses without
    # traversing any relation/double-coset orbit.
    if b.contains(a.representative):
        return a.representative
    if a.contains(b.representative):
        return b.representative

    best = None
    for x in range(n):
        oh, th = orbit_transversal(a.representative[x], _gens(H), n)
        ok, tk = orbit_transversal(b.representative[x], _gens(K), n)
        common = tuple(sorted(set(oh) & set(ok)))
        if not common:
            return None
        if len(oh) > 1 or len(ok) > 1:
            # First minimize the number of feasible image branches. The
            # remaining terms make the choice deterministic and prefer a point
            # that shrinks the input groups strongly.
            score = (len(common), len(oh) * len(ok), -(len(oh) + len(ok)), x)
            if best is None or score < best[0]:
                best = (score, x, common, th, tk)

    if best is None:
        # Both subgroups act trivially on every image point, so the two cosets
        # are singletons. The unequal-representative case is empty because the
        # two direct membership shortcuts above already failed.
        return None

    _, _x, common, th, tk = best
    for y in common:
        # If t maps the current image to y, all subgroup elements achieving
        # that image form t * G_y, where G_y is the point stabilizer of y.
        Hy = _point_stabilizer(H, y)
        Ky = _point_stabilizer(K, y)
        aa = RightCoset(Hy, compose(a.representative, th[y]))
        bb = RightCoset(Ky, compose(b.representative, tk[y]))
        witness = _find_common(aa, bb, budget)
        if witness is not None:
            return witness
    return None


def _group_intersection(H: StabilizerChain, K: StabilizerChain, budget: _Budget, memo: dict) -> StabilizerChain:
    """Construct H intersect K from point stabilizers and exact transporters."""
    budget.tick()
    key = (H.original_generators, K.original_generators)
    if key in memo:
        return memo[key]
    if _subgroup_leq(H, K):
        memo[key] = H
        return H
    if _subgroup_leq(K, H):
        memo[key] = K
        return K

    n = H.degree
    e = identity(n)
    best = None
    for p in range(n):
        oh, th = orbit_transversal(p, _gens(H), n)
        ok, tk = orbit_transversal(p, _gens(K), n)
        if len(oh) > 1 or len(ok) > 1:
            common = tuple(sorted(set(oh) & set(ok)))
            score = (len(common), len(oh) * len(ok), -(len(oh) + len(ok)), p)
            if best is None or score < best[0]:
                best = (score, p, common, th, tk)

    if best is None:
        out = schreier_stabilizer_chain((e,))
        memo[key] = out
        return out

    _, p, common, th, tk = best
    # The stabilizer in H intersect K of p is H_p intersect K_p.
    Lp = _group_intersection(_point_stabilizer(H, p), _point_stabilizer(K, p), budget, memo)
    out_gens = list(Lp.original_generators)

    # For every point actually reachable by H intersect K, one exact
    # transporter together with L_p generates that orbit fibre. Candidate
    # points in orbit_H(p) intersect orbit_K(p) that are not reachable are
    # rejected by the recursive coset-intersection witness search.
    for y in common:
        if y == p:
            continue
        Hy = _point_stabilizer(H, y)
        Ky = _point_stabilizer(K, y)
        witness = _find_common(RightCoset(Hy, th[y]), RightCoset(Ky, tk[y]), budget)
        if witness is not None:
            out_gens.append(witness)

    out = schreier_stabilizer_chain(out_gens or (e,))
    if any(not H.contains(g) or not K.contains(g) for g in out.original_generators):
        raise AssertionError("intersection generator escaped an input subgroup")
    memo[key] = out
    return out


def right_coset_intersection_recursive(a: RightCoset, b: RightCoset, *, max_nodes: int = 100000) -> RecursiveCosetIntersection:
    """Exact right-coset intersection without enumerating the full relation orbit.

    The search recursively fixes point images, replacing each branch by point
    stabilizers. Once a common representative is found, H intersect K is built
    from recursive stabilizer intersections and exact transporter witnesses.
    `max_nodes` is an explicit fail-closed bound: exhaustion returns no coset
    certificate rather than guessing.
    """
    if a.subgroup.degree != b.subgroup.degree:
        raise ValueError("degree mismatch")
    if max_nodes < 1:
        raise ValueError("max_nodes must be positive")

    budget = _Budget(max_nodes)
    try:
        witness = _find_common(a, b, budget)
        if witness is None:
            return RecursiveCosetIntersection(
                "empty_intersection", None, 0, budget.used,
                "point-image stabilizer recursion proved the cosets disjoint",
            )
        inter = _group_intersection(a.subgroup, b.subgroup, budget, {})
    except _NodeLimit:
        return RecursiveCosetIntersection(
            "undetermined_node_limit", None, 0, budget.used,
            "recursive stabilizer search exceeded max_nodes",
        )

    if not a.contains(witness) or not b.contains(witness):
        raise AssertionError("witness is not in both input cosets")
    return RecursiveCosetIntersection(
        "exact_intersection_coset", RightCoset(inter, witness), inter.order, budget.used,
        "base-point orbit branching plus recursive stabilizer intersections; no full relation orbit enumeration",
    )
