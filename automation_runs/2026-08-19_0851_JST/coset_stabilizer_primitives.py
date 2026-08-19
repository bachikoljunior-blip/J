from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Tuple
from permutation_group_schreier import Permutation, StabilizerChain, compose, identity, inverse, orbit_transversal, schreier_stabilizer_chain, validate_perm

def point_stabilizer_generators(generators:Iterable[Iterable[int]], point:int) -> Tuple[Permutation,...]:
    gens=tuple(validate_perm(g) for g in generators)
    if not gens: raise ValueError('at least one generator required')
    n=len(gens[0])
    if not 0<=point<n: raise ValueError('point out of range')
    _,trans=orbit_transversal(point,gens,n); out=set(); e=identity(n)
    for x,tx in trans.items():
        for s in gens:
            y=s[x]; h=compose(compose(tx,s),inverse(trans[y]))
            if h!=e: out.add(h)
    return tuple(sorted(out))

def pointwise_stabilizer_chain(chain:StabilizerChain, points:Iterable[int]) -> StabilizerChain:
    n=chain.degree; gens=chain.original_generators or (identity(n),); seen=set()
    for raw in points:
        p=int(raw)
        if p in seen: continue
        if not 0<=p<n: raise ValueError('point out of range')
        gens=point_stabilizer_generators(gens,p) or (identity(n),); seen.add(p)
    return schreier_stabilizer_chain(gens)

@dataclass(frozen=True)
class RightCoset:
    subgroup: StabilizerChain
    representative: Permutation
    def contains(self,p:Iterable[int]) -> bool:
        p=validate_perm(p); r=validate_perm(self.representative)
        if len(p)!=self.subgroup.degree or len(r)!=self.subgroup.degree: return False
        return self.subgroup.contains(compose(inverse(r),p))
