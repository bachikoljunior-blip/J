from __future__ import annotations
from dataclasses import dataclass
from typing import List,Mapping,Sequence,Set,Tuple
import math,numpy as np
from wl_attributed_kernel import wl_attributed_feature_map
from finite_family_rff_certificate import color_history
@dataclass(frozen=True)
class StructuralEditCertificate:
    edit_count:int; edited_vertices:Tuple[int,...]; support_sizes:Tuple[int,...]; actual_feature_l2:float; upper_bound_l2:float; support_validated:bool; passed:bool
def _validate(a):
    a=(np.asarray(a)!=0)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)): raise ValueError("expected simple undirected adjacency")
    return a
def _edge_edits(a,b):
    edges=np.argwhere(np.triu(a!=b,1)); endpoints=tuple(sorted(set(int(v) for e in edges for v in e))); return edges,endpoints
def _radius_support(union_adj,sources,radius):
    seen=set(int(s) for s in sources); frontier=set(seen)
    for _ in range(radius):
        nxt=set()
        for i in frontier: nxt.update(int(j) for j in np.flatnonzero(union_adj[i]))
        nxt-=seen
        if not nxt: break
        seen|=nxt; frontier=nxt
    return seen
def _diff(a:Mapping,b:Mapping): return math.sqrt(sum((a.get(k,0.0)-b.get(k,0.0))**2 for k in set(a)|set(b)))
def structural_edit_stability_certificate(adjacency_before,adjacency_after,attributes,*,iterations=3,rff_components=32,bandwidth=1.0,seed=0):
    a=_validate(adjacency_before); b=_validate(adjacency_after)
    if a.shape!=b.shape: raise ValueError("same node set required")
    x=np.asarray(attributes,dtype=float)
    if x.ndim!=2 or x.shape[0]!=a.shape[0] or not np.all(np.isfinite(x)): raise ValueError("bad attributes")
    edges,endpoints=_edge_edits(a,b); union=a|b; sizes=[]; valid=True; ha=color_history(a,iterations); hb=color_history(b,iterations)
    for h in range(iterations+1):
        support=_radius_support(union,endpoints,h) if endpoints else set(); changed={i for i,(ca,cb) in enumerate(zip(ha[h],hb[h])) if ca!=cb}; valid &= changed.issubset(support); sizes.append(len(support))
    fx=wl_attributed_feature_map(a,x,iterations=iterations,rff_components=rff_components,bandwidth=bandwidth,seed=seed,normalize_node_mass=True); fy=wl_attributed_feature_map(b,x,iterations=iterations,rff_components=rff_components,bandwidth=bandwidth,seed=seed,normalize_node_mass=True)
    actual=_diff(fx,fy); bound=2.0/math.sqrt(a.shape[0])*math.sqrt(sum(s*s for s in sizes))
    return StructuralEditCertificate(int(len(edges)),endpoints,tuple(sizes),float(actual),float(bound),bool(valid),bool(valid and actual<=bound+1e-10))
