from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass(frozen=True)
class OneVertexIROrbitCertificate:
    status: str
    forced_pairs: Tuple[Tuple[int,int], ...]
    base_vertex: int
    seed_targets_checked: int
    isomorphism_count: int
    reason: str


def _validate(graph):
    a=np.asarray(graph[0])!=0; x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)):
        raise ValueError('expected simple undirected adjacency')
    if x.ndim!=2 or x.shape[0]!=len(a) or x.shape[1]<1 or not np.all(np.isfinite(x)):
        raise ValueError('bad attributes')
    return a,x


def _key(row): return np.ascontiguousarray(row,dtype=np.float64).tobytes()


def _compress_joint(sa,sb):
    labels={s:i for i,s in enumerate(sorted(set(sa+sb),key=repr))}
    return [labels[s] for s in sa],[labels[s] for s in sb]


def _individualized_wl(a,x,b,y,source_seed,target_seed,max_rounds):
    n=len(a)
    sa=[(_key(x[i]),i==source_seed) for i in range(n)]
    sb=[(_key(y[j]),j==target_seed) for j in range(n)]
    ca,cb=_compress_joint(sa,sb)
    for _ in range(max_rounds):
        sa=[(ca[i],tuple(sorted(Counter(ca[k] for k in np.flatnonzero(a[i])).items()))) for i in range(n)]
        sb=[(cb[j],tuple(sorted(Counter(cb[k] for k in np.flatnonzero(b[j])).items()))) for j in range(n)]
        na,nb=_compress_joint(sa,sb)
        if na==ca and nb==cb: break
        ca,cb=na,nb
    return ca,cb


def exact_one_vertex_ir_orbit(graph_a,graph_b,*,max_rounds=64,max_base_trials=64):
    """Polynomial exact orbit enumeration when one-vertex IR becomes discrete.

    For a chosen source base vertex, every exact isomorphism maps it to a target
    vertex with the same persistent attribute. Every such target is tried. If
    individualized joint 1-WL gives unequal color inventories, that seed target
    is impossible. If it becomes discrete, the unique color-preserving mapping
    is directly verified; failure then proves that seed target impossible. A
    non-discrete matching inventory leaves that base unresolved. If one base has
    every seed target resolved, the verified mappings are the complete exact
    isomorphism family, and their intersection is the exact forced-pair set.
    """
    if max_rounds<1 or max_base_trials<1: raise ValueError('limits must be positive')
    a,x=_validate(graph_a); b,y=_validate(graph_b)
    if len(a)!=len(b) or x.shape[1]!=y.shape[1]:
        return OneVertexIROrbitCertificate('inconsistent_constraints',(),-1,0,0,'full exact alignment requires equal sizes and attribute dimensions')
    n=len(a); ax=[_key(r) for r in x]; by=[_key(r) for r in y]
    if Counter(ax)!=Counter(by):
        return OneVertexIROrbitCertificate('inconsistent_constraints',(),-1,0,0,'attribute inventories differ')

    # Try vertices from smaller attribute classes first to reduce seed targets.
    ac=Counter(ax); base_order=sorted(range(n),key=lambda i:(ac[ax[i]],i))[:max_base_trials]
    for base in base_order:
        targets=[j for j in range(n) if by[j]==ax[base]]
        mappings=[]; unresolved=False
        for target in targets:
            ca,cb=_individualized_wl(a,x,b,y,base,target,max_rounds)
            if Counter(ca)!=Counter(cb):
                continue
            if any(v!=1 for v in Counter(ca).values()):
                unresolved=True; break
            pos={c:j for j,c in enumerate(cb)}
            pairs=tuple((i,pos[ca[i]]) for i in range(n)); p=np.asarray([j for _,j in pairs],dtype=int)
            # With discrete isomorphism-invariant colors, if this induced mapping
            # fails exact verification no isomorphism can realize this seed pair.
            if not np.array_equal(x,y[p]) or not np.array_equal(a,b[np.ix_(p,p)]):
                continue
            mappings.append(set(pairs))
        if unresolved:
            continue
        if not mappings:
            return OneVertexIROrbitCertificate('inconsistent_constraints',(),base,len(targets),0,'all seed targets disproved for a fully resolved base vertex')
        inter=set(mappings[0])
        for w in mappings[1:]: inter &= w
        forced=tuple(sorted(inter))
        return OneVertexIROrbitCertificate(
            'certified_no_forced_pairs' if not forced else 'certified_exact_forced_pairs',
            forced,base,len(targets),len(mappings),
            'all possible images of one base vertex resolved by individualized discrete 1-WL; verified mappings form complete isomorphism family'
        )
    return OneVertexIROrbitCertificate('undetermined_refinement_depth',(),-1,0,0,'no tried base vertex made every possible seed target discrete or inconsistent')
