from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass(frozen=True)
class CycleOrbitCertificate:
    status: str
    forced_pairs: Tuple[Tuple[int,int], ...]
    isomorphism_count: int
    reason: str


def _validate(graph):
    a=np.asarray(graph[0])!=0; x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)):
        raise ValueError('expected simple undirected adjacency')
    if x.ndim!=2 or x.shape[0]!=len(a) or x.shape[1]<1 or not np.all(np.isfinite(x)):
        raise ValueError('bad attributes')
    return a,x


def _is_single_cycle(a):
    n=len(a)
    if n<3 or not np.all(a.sum(axis=1)==2): return False
    seen={0}; stack=[0]
    while stack:
        u=stack.pop()
        for v in np.flatnonzero(a[u]):
            v=int(v)
            if v not in seen: seen.add(v); stack.append(v)
    return len(seen)==n


def _walk_cycle(a,start,next_vertex):
    n=len(a); order=[int(start)]; prev=-1; cur=int(start); nxt=int(next_vertex)
    for _ in range(n-1):
        order.append(nxt); prev,cur=cur,nxt
        cand=[int(v) for v in np.flatnonzero(a[cur]) if int(v)!=prev]
        if not cand: return None
        nxt=cand[0]
    if nxt!=start: return None
    return tuple(order)


def exact_cycle_orbit_certificate(graph_a,graph_b):
    """Complete O(n^2) isomorphism-intersection certificate for single cycles.

    The two orientations from every possible target start enumerate the complete
    dihedral isomorphism family, filtered by exact vertex attributes. The forced
    set is therefore the exact intersection of all valid cycle isomorphisms.
    """
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if len(a)!=len(b) or x.shape[1]!=y.shape[1]:
        return CycleOrbitCertificate('inconsistent_constraints',(),0,'cycle isomorphism requires equal sizes and attribute dimensions')
    if not _is_single_cycle(a) or not _is_single_cycle(b):
        return CycleOrbitCertificate('not_applicable',(),0,'both graphs must be connected single cycles')
    n=len(a)
    an=[int(v) for v in np.flatnonzero(a[0])]
    aorder=_walk_cycle(a,0,an[0])
    if aorder is None:
        return CycleOrbitCertificate('inconsistent_constraints',(),0,'failed to traverse source cycle')

    intersection=None; count=0
    for start in range(n):
        for nxt in [int(v) for v in np.flatnonzero(b[start])]:
            border=_walk_cycle(b,start,nxt)
            if border is None: continue
            pairs=tuple((aorder[t],border[t]) for t in range(n))
            if not all(np.array_equal(x[i],y[j]) for i,j in pairs):
                continue
            # Cycle traversal plus degree-2 connected-cycle validation proves
            # adjacency preservation; verify every traversed source edge maps to
            # an edge and every mapped vertex remains degree 2.
            if not all(bool(b[pairs[t][1],pairs[(t+1)%n][1]]) for t in range(n)):
                continue
            s=set(pairs); count += 1
            intersection=s if intersection is None else intersection & s
    if count==0:
        return CycleOrbitCertificate('inconsistent_constraints',(),0,'no attribute-preserving cycle isomorphism exists')
    forced=tuple(sorted(intersection or ()))
    return CycleOrbitCertificate(
        'certified_no_forced_pairs' if not forced else 'certified_exact_forced_pairs',
        forced,count,
        'complete dihedral cycle-isomorphism enumeration; forced set is exact intersection'
    )
