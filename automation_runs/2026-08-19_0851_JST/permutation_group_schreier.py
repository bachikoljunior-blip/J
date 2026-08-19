from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import prod
from typing import Iterable, Tuple

Permutation = Tuple[int, ...]


def identity(n: int) -> Permutation:
    return tuple(range(n))


def validate_perm(p: Iterable[int]) -> Permutation:
    p=tuple(int(x) for x in p); n=len(p)
    if sorted(p)!=list(range(n)): raise ValueError('not a permutation')
    return p


def compose(p: Permutation,q: Permutation) -> Permutation:
    """Apply p, then q."""
    if len(p)!=len(q): raise ValueError('degree mismatch')
    return tuple(q[p[i]] for i in range(len(p)))


def inverse(p: Permutation) -> Permutation:
    out=[0]*len(p)
    for i,j in enumerate(p): out[j]=i
    return tuple(out)


def _dedup_nonidentity(gens,ident):
    return tuple(sorted({g for g in gens if g!=ident}))


def orbit_transversal(base:int,gens:Tuple[Permutation,...],n:int):
    """Orbit and right-action transversal t_x with t_x(base)=x."""
    ident=identity(n); trans={base:ident}; q=deque([base])
    while q:
        x=q.popleft(); tx=trans[x]
        for s in gens:
            y=s[x]
            if y not in trans:
                trans[y]=compose(tx,s); q.append(y)
    return tuple(sorted(trans)),trans


@dataclass(frozen=True)
class StabilizerLevel:
    base: int
    orbit: Tuple[int,...]
    generators: Tuple[Permutation,...]
    transversal: Tuple[Tuple[int,Permutation],...]


@dataclass(frozen=True)
class StabilizerChain:
    degree: int
    original_generators: Tuple[Permutation,...]
    levels: Tuple[StabilizerLevel,...]
    order: int

    def contains(self,p:Iterable[int]) -> bool:
        g=validate_perm(p)
        if len(g)!=self.degree: return False
        for level in self.levels:
            trans=dict(level.transversal); x=g[level.base]
            if x not in trans: return False
            g=compose(g,inverse(trans[x]))
        return g==identity(self.degree)


def schreier_stabilizer_chain(generators:Iterable[Iterable[int]]) -> StabilizerChain:
    generators=tuple(validate_perm(g) for g in generators)
    if not generators: raise ValueError('at least one generator is required; use identity generator for the trivial group')
    n=len(generators[0])
    if any(len(g)!=n for g in generators): raise ValueError('degree mismatch')
    ident=identity(n); current=_dedup_nonidentity(generators,ident); levels=[]; orbit_sizes=[]
    # A full base 0..n-1 is simple and deterministic. Schreier generators at
    # level b generate the point stabilizer of all base points through b.
    for b in range(n):
        orbit,trans=orbit_transversal(b,current,n)
        levels.append(StabilizerLevel(b,orbit,current,tuple(sorted(trans.items())))); orbit_sizes.append(len(orbit))
        if not current: continue
        next_gens=[]
        for x,tx in trans.items():
            for s in current:
                y=s[x]; ty=trans[y]
                # b --tx--> x --s--> y --ty^-1--> b
                h=compose(compose(tx,s),inverse(ty))
                if h!=ident: next_gens.append(h)
        current=_dedup_nonidentity(next_gens,ident)
    return StabilizerChain(n,_dedup_nonidentity(generators,ident),tuple(levels),prod(orbit_sizes))


def group_orbit(chain:StabilizerChain,point:int) -> Tuple[int,...]:
    if not (0<=point<chain.degree): raise ValueError('point out of range')
    gens=chain.original_generators
    return orbit_transversal(point,gens,chain.degree)[0]
