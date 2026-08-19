from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Optional

from permutation_group_schreier import Permutation, compose, identity, inverse, schreier_stabilizer_chain
from coset_stabilizer_primitives import RightCoset


def _relation(a: Permutation, b: Permutation) -> Permutation:
    # r[a(i)] = b(i)
    return compose(inverse(a), b)


def _act_relation(r: Permutation, h: Permutation, k: Permutation) -> Permutation:
    # (h,k) sends graph(r) to graph(k o r o h^-1).
    return compose(compose(inverse(h), r), k)


@dataclass(frozen=True)
class CompressedCosetIntersection:
    status: str
    coset: Optional[RightCoset]
    intersection_order: int
    relation_orbit_size: int
    reason: str


def right_coset_intersection_compressed(a: RightCoset, b: RightCoset, *, max_images: int = 100000) -> CompressedCosetIntersection:
    """Exact aH ∩ bK using an n-symbol permutation relation, not an n^2 bitmap.

    The source relation is the bijection r with r[a(i)] = b(i). HxK acts by
    r -> k o r o h^-1. Reaching identity is equivalent to a*h = b*k.
    A complete orbit yields an exact transporter and the diagonal stabilizer
    projects to H∩K. Orbit-limit exhaustion fails closed.
    """
    H, K = a.subgroup, b.subgroup
    if H.degree != K.degree:
        raise ValueError("degree mismatch")
    n = H.degree
    e = identity(n)
    source = _relation(a.representative, b.representative)
    gens = [(g, e) for g in (H.original_generators or (e,))] + [(e, g) for g in (K.original_generators or (e,))]

    trans: dict[Permutation, tuple[Permutation, Permutation]] = {source: (e, e)}
    q = deque([source])
    while q:
        state = q.popleft()
        th, tk = trans[state]
        for h, k in gens:
            nxt = _act_relation(state, h, k)
            if nxt not in trans:
                if len(trans) >= max_images:
                    return CompressedCosetIntersection("undetermined_image_orbit_limit", None, 0, len(trans), "relation orbit exceeds max_images")
                trans[nxt] = (compose(th, h), compose(tk, k))
                q.append(nxt)

    if e not in trans:
        return CompressedCosetIntersection("empty_intersection", None, 0, len(trans), "identity relation is outside the complete HxK orbit")

    rh, rk = trans[e]
    common = compose(a.representative, rh)
    if common != compose(b.representative, rk):
        raise AssertionError("relation transporter did not produce a common coset element")

    projected = []
    for state, (th, tk) in trans.items():
        for h, k in gens:
            nxt = _act_relation(state, h, k)
            nh, nk = trans[nxt]
            # Schreier loop stabilizing source.
            lh = compose(compose(th, h), inverse(nh))
            lk = compose(compose(tk, k), inverse(nk))
            if lh == e and lk == e:
                continue
            # Conjugate source stabilizer to target(identity) stabilizer.
            ch = compose(compose(inverse(rh), lh), rh)
            ck = compose(compose(inverse(rk), lk), rk)
            if ch != ck:
                raise AssertionError("identity-relation stabilizer is not diagonal")
            if ch != e:
                projected.append(ch)

    inter = schreier_stabilizer_chain(projected or [e])
    return CompressedCosetIntersection("exact_intersection_coset", RightCoset(inter, common), inter.order, len(trans), "complete compressed relation orbit and projected diagonal stabilizer")
