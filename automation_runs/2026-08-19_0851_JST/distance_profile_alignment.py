from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass(frozen=True)
class DistanceProfileCertificate:
    status: str
    pairs: Tuple[Tuple[int,int], ...]
    distinct_signatures: int
    reason: str


def _validate(graph):
    a=np.asarray(graph[0])!=0; x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)):
        raise ValueError('expected simple undirected adjacency')
    if x.ndim!=2 or x.shape[0]!=len(a) or x.shape[1]<1 or not np.all(np.isfinite(x)):
        raise ValueError('bad attributes')
    return a,x


def _key(row):
    return np.ascontiguousarray(row,dtype=np.float64).tobytes()


def _distances(a,s):
    n=len(a); d=[-1]*n; d[s]=0; q=deque([s])
    while q:
        u=q.popleft()
        for v in np.flatnonzero(a[u]):
            v=int(v)
            if d[v]<0: d[v]=d[u]+1; q.append(v)
    return d


def _signatures(a,x,attr_keys):
    keys=[_key(r) for r in x]; pos={k:i for i,k in enumerate(attr_keys)}
    out=[]
    n=len(a)
    for s in range(n):
        d=_distances(a,s)
        # For each exact attribute bucket, record the exact multiset of graph
        # distances. -1 is retained for disconnected components.
        by=[[] for _ in attr_keys]
        for v in range(n): by[pos[keys[v]]].append(d[v])
        out.append((keys[s],tuple(tuple(sorted(z)) for z in by)))
    return out


def infer_full_alignment_distance_profiles(graph_a,graph_b):
    """Exact/full fail-closed mapping from integer metric invariants.

    The signature of a vertex is its exact attribute plus, for every attribute
    bucket, the multiset of shortest-path distances to vertices in that bucket.
    Exact isomorphisms preserve these signatures. If every signature is singleton
    jointly, any isomorphism must use the induced pair. The complete mapping is
    still directly verified before release.
    """
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if len(a)!=len(b) or x.shape[1]!=y.shape[1]:
        return DistanceProfileCertificate('inconsistent_constraints',(),0,'full exact alignment requires equal sizes and attribute dimensions')
    attrs=sorted(set(_key(r) for r in x)|set(_key(r) for r in y))
    sa=_signatures(a,x,attrs); sb=_signatures(b,y,attrs)
    ca=Counter(sa); cb=Counter(sb)
    if ca!=cb:
        return DistanceProfileCertificate('inconsistent_constraints',(),len(ca),'distance-profile inventories differ')
    if any(v!=1 for v in ca.values()):
        return DistanceProfileCertificate('ambiguous_or_invariant_insufficient',(),len(ca),'non-singleton distance-profile class remains; no pairs released')
    where={s:j for j,s in enumerate(sb)}
    pairs=tuple((i,where[sa[i]]) for i in range(len(a)))
    p=np.asarray([j for _,j in pairs],dtype=int)
    if not np.array_equal(x,y[p]) or not np.array_equal(a,b[np.ix_(p,p)]):
        return DistanceProfileCertificate('inconsistent_constraints',(),len(ca),'induced invariant mapping failed direct verification')
    return DistanceProfileCertificate('certified_unique_alignment',pairs,len(ca),'all exact distance-profile classes singleton and induced mapping directly verified')
