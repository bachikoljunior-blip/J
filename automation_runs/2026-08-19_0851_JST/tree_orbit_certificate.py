from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass(frozen=True)
class TreeOrbitCertificate:
    status: str
    forced_pairs: Tuple[Tuple[int,int], ...]
    orbit_count: int
    singleton_orbits: int
    witness_pairs: Tuple[Tuple[int,int], ...]
    reason: str


def _validate(graph):
    a=np.asarray(graph[0])!=0; x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)):
        raise ValueError('expected simple undirected adjacency')
    if x.ndim!=2 or x.shape[0]!=len(a) or x.shape[1]<1 or not np.all(np.isfinite(x)):
        raise ValueError('bad attributes')
    return a,x


def _key(row): return np.ascontiguousarray(row,dtype=np.float64).tobytes()


def _is_tree(a):
    n=len(a)
    if n==0: return False
    if int(a.sum())//2 != n-1: return False
    seen={0}; q=deque([0])
    while q:
        u=q.popleft()
        for v in np.flatnonzero(a[u]):
            v=int(v)
            if v not in seen: seen.add(v); q.append(v)
    return len(seen)==n


def _rooted_codes(a,x,root):
    n=len(a); parent=[-2]*n; parent[root]=-1; order=[root]
    for u in order:
        for vv in np.flatnonzero(a[u]):
            v=int(vv)
            if parent[v]==-2: parent[v]=u; order.append(v)
    code=[None]*n
    for u in reversed(order):
        children=[code[v] for v in np.flatnonzero(a[u]) if parent[int(v)]==u]
        code[u]=(_key(x[u]),tuple(sorted(children,key=repr)))
    return code[root],parent,code


def _all_root_codes(a,x):
    return tuple(_rooted_codes(a,x,r)[0] for r in range(len(a)))


def _construct_rooted_mapping(a,x,b,y,ra,rb):
    _,pa,ca=_rooted_codes(a,x,ra); _,pb,cb=_rooted_codes(b,y,rb)
    mapping={}; stack=[(ra,rb)]
    while stack:
        u,v=stack.pop(); mapping[u]=v
        ga=defaultdict(list); gb=defaultdict(list)
        for ww in np.flatnonzero(a[u]):
            w=int(ww)
            if pa[w]==u: ga[ca[w]].append(w)
        for zz in np.flatnonzero(b[v]):
            z=int(zz)
            if pb[z]==v: gb[cb[z]].append(z)
        if set(ga)!=set(gb): return None
        for c in ga:
            if len(ga[c])!=len(gb[c]): return None
            for w,z in zip(sorted(ga[c]),sorted(gb[c])): stack.append((w,z))
    return tuple(sorted(mapping.items()))


def exact_tree_orbit_certificate(graph_a,graph_b):
    """Polynomial exact forced-identity certificate for attributed trees.

    For trees, vertices u and v lie in the same automorphism orbit exactly when
    the rooted attributed trees (T,u) and (T,v) are isomorphic. AHU-style rooted
    canonical forms therefore name the exact vertex orbits. Across two isomorphic
    trees, a source identity is forced exactly when its rooted canonical form is a
    singleton orbit (and hence has one matching target vertex). A full witness is
    also constructed and directly verified before any identities are released.
    """
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if len(a)!=len(b) or x.shape[1]!=y.shape[1]:
        return TreeOrbitCertificate('inconsistent_constraints',(),0,0,(),'tree isomorphism requires equal sizes and attribute dimensions')
    if not _is_tree(a) or not _is_tree(b):
        return TreeOrbitCertificate('not_applicable',(),0,0,(),'both graphs must be connected trees')
    sa=_all_root_codes(a,x); sb=_all_root_codes(b,y); ca=Counter(sa); cb=Counter(sb)
    if ca!=cb:
        return TreeOrbitCertificate('inconsistent_constraints',(),len(ca),0,(),'rooted-tree canonical-form inventories differ')
    where=defaultdict(list)
    for j,c in enumerate(sb): where[c].append(j)
    forced=[]
    for i,c in enumerate(sa):
        if ca[c]==1: forced.append((i,where[c][0]))

    # Any matching rooted canonical form yields an exact rooted tree isomorphism.
    rb=where[sa[0]][0]; witness=_construct_rooted_mapping(a,x,b,y,0,rb)
    if witness is None or len(witness)!=len(a):
        return TreeOrbitCertificate('inconsistent_constraints',(),len(ca),0,(),'failed to construct rooted canonical witness')
    p=np.asarray([j for _,j in witness],dtype=int)
    if not np.array_equal(x,y[p]) or not np.array_equal(a,b[np.ix_(p,p)]):
        return TreeOrbitCertificate('inconsistent_constraints',(),len(ca),0,(),'constructed tree-isomorphism witness failed direct verification')
    return TreeOrbitCertificate(
        'certified_no_forced_pairs' if not forced else 'certified_exact_forced_pairs',
        tuple(forced),len(ca),sum(1 for v in ca.values() if v==1),witness,
        'rooted attributed-tree canonical forms exactly identify automorphism orbits; full witness directly verified'
    )
