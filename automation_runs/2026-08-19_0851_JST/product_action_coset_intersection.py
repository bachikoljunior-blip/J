from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from permutation_group_schreier import Permutation, StabilizerChain, compose, identity, schreier_stabilizer_chain, validate_perm
from coset_stabilizer_primitives import RightCoset
from state_orbit_schreier import string_orbit_stabilizer_transporter


def _lift_first(g:Permutation,n:int) -> Permutation:
    return tuple(g[u]*n+v for u in range(n) for v in range(n))


def _lift_second(g:Permutation,n:int) -> Permutation:
    return tuple(u*n+g[v] for u in range(n) for v in range(n))


def _relation_state(a:Permutation,b:Permutation,n:int) -> Tuple[int,...]:
    s=[0]*(n*n)
    for i in range(n): s[a[i]*n+b[i]]=1
    return tuple(s)


def _diagonal_state(n:int) -> Tuple[int,...]:
    s=[0]*(n*n)
    for i in range(n): s[i*n+i]=1
    return tuple(s)


def _decode_product(p:Permutation,n:int):
    h=[]; k=[]
    for u in range(n): h.append(p[u*n]//n)
    for v in range(n): k.append(p[v]%n)
    h=tuple(h); k=tuple(k)
    if any(p[u*n+v] != h[u]*n+k[v] for u in range(n) for v in range(n)):
        raise AssertionError('permutation is not separable product action')
    return h,k


def _subgroup_contains_group(a:StabilizerChain,b:StabilizerChain) -> bool:
    """Return whether A <= B from generator membership."""
    return a.degree==b.degree and all(b.contains(g) for g in a.original_generators)


@dataclass(frozen=True)
class ProductCosetIntersection:
    status: str
    coset: Optional[RightCoset]
    intersection_order: int
    product_image_orbit_size: int
    reason: str


def right_coset_intersection_product_action(a:RightCoset,b:RightCoset,*,max_images:int=100000) -> ProductCosetIntersection:
    """Exact coset intersection without enumerating H or K elements.

    For generic subgroups, HxK acts on ordered pairs. The relation
    R={(a(i),b(i))} is transported to the diagonal exactly when some h in H,
    k in K satisfy a*h=b*k. The diagonal stabilizer consists of pairs (g,g)
    with g in H intersection K; projecting its generators yields the intersection
    subgroup. State-orbit size, not |H||K|, is explicitly bounded.
    """
    H=a.subgroup; K=b.subgroup
    if H.degree!=K.degree: raise ValueError('degree mismatch')
    n=H.degree; ar=validate_perm(a.representative); br=validate_perm(b.representative)

    # Containment shortcuts avoid a potentially large product state orbit.
    if _subgroup_contains_group(H,K):
        if not b.contains(ar): return ProductCosetIntersection('empty_intersection',None,0,0,'H <= K and a representative is outside bK')
        return ProductCosetIntersection('exact_intersection_coset',RightCoset(H,ar),H.order,0,'H <= K and aH is contained in bK')
    if _subgroup_contains_group(K,H):
        if not a.contains(br): return ProductCosetIntersection('empty_intersection',None,0,0,'K <= H and b representative is outside aH')
        return ProductCosetIntersection('exact_intersection_coset',RightCoset(K,br),K.order,0,'K <= H and bK is contained in aH')

    e=identity(n); hg=H.original_generators or (e,); kg=K.original_generators or (e,)
    product_gens=tuple(_lift_first(g,n) for g in hg)+tuple(_lift_second(g,n) for g in kg)
    source=_relation_state(ar,br,n); target=_diagonal_state(n)
    tr=string_orbit_stabilizer_transporter(product_gens,source,target,max_images=max_images)
    if tr.status=='undetermined_image_orbit_limit':
        return ProductCosetIntersection('undetermined_image_orbit_limit',None,0,tr.orbit_size,'HxK relation orbit exceeds max_images')
    if tr.status=='empty_transporter':
        return ProductCosetIntersection('empty_intersection',None,0,tr.orbit_size,'no product-group element transports relation to diagonal')
    if tr.transporter is None:
        raise AssertionError('expected exact transporter')

    product_rep=tr.transporter.representative; h,k=_decode_product(product_rep,n)
    common=compose(ar,h)
    if common!=compose(br,k): raise AssertionError('decoded transporter does not produce common coset element')

    diag_stab=tr.transporter.subgroup; projected=[]
    for pg in diag_stab.original_generators:
        gh,gk=_decode_product(pg,n)
        if gh!=gk: raise AssertionError('diagonal stabilizer generator has unequal factors')
        projected.append(gh)
    inter_chain=schreier_stabilizer_chain(projected or [e])
    cos=RightCoset(inter_chain,common)
    return ProductCosetIntersection('exact_intersection_coset',cos,inter_chain.order,tr.orbit_size,'product-action transporter plus projected diagonal stabilizer')
