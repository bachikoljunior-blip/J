from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping,Sequence,Tuple
import math,numpy as np
from finite_family_rff_certificate import color_history
from wl_attributed_kernel import wl_attributed_feature_map
@dataclass(frozen=True)
class VertexEditCertificate:
    common_nodes:int; deleted_nodes:int; inserted_nodes:int; changed_common_colors_per_depth:Tuple[int,...]; actual_feature_l2:float; upper_bound_l2:float; passed:bool
def _validate_graph(graph):
    a=(np.asarray(graph[0])!=0); x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)): raise ValueError("expected simple undirected adjacency")
    if x.ndim!=2 or x.shape[0]!=a.shape[0] or x.shape[1]<1 or not np.all(np.isfinite(x)): raise ValueError("bad attributes")
    return a,x
def _diff(a:Mapping,b:Mapping): return math.sqrt(sum((a.get(k,0.0)-b.get(k,0.0))**2 for k in set(a)|set(b)))
def vertex_edit_stability_certificate(graph_before,graph_after,alignment:Sequence[Tuple[int,int]],*,iterations=3,rff_components=32,bandwidth=1.0,seed=0,attribute_atol=0.0):
    a,x=_validate_graph(graph_before); b,y=_validate_graph(graph_after)
    if x.shape[1]!=y.shape[1]: raise ValueError("attribute dimensions must match")
    if attribute_atol<0: raise ValueError("attribute_atol must be non-negative")
    pairs=[(int(i),int(j)) for i,j in alignment]; ia=[i for i,_ in pairs]; jb=[j for _,j in pairs]
    if len(set(ia))!=len(ia) or len(set(jb))!=len(jb): raise ValueError("alignment must be injective")
    if any(i<0 or i>=a.shape[0] or j<0 or j>=b.shape[0] for i,j in pairs): raise ValueError("alignment index out of range")
    for i,j in pairs:
        if np.max(np.abs(x[i]-y[j]))>attribute_atol: raise ValueError("aligned attributes differ beyond tolerance")
    k=len(pairs); deleted=a.shape[0]-k; inserted=b.shape[0]-k; ha=color_history(a,iterations); hb=color_history(b,iterations); alpha=1.0/math.sqrt(a.shape[0]); beta=1.0/math.sqrt(b.shape[0]); per=[]; changed_counts=[]
    for h in range(iterations+1):
        changed=sum(1 for i,j in pairs if ha[h][i]!=hb[h][j]); stable=k-changed; changed_counts.append(changed)
        per.append(math.sqrt(2.0)*(abs(alpha-beta)*stable+math.sqrt(alpha*alpha+beta*beta)*changed+alpha*deleted+beta*inserted))
    bound=math.sqrt(sum(v*v for v in per)); fa=wl_attributed_feature_map(a,x,iterations=iterations,rff_components=rff_components,bandwidth=bandwidth,seed=seed,normalize_node_mass=True); fb=wl_attributed_feature_map(b,y,iterations=iterations,rff_components=rff_components,bandwidth=bandwidth,seed=seed,normalize_node_mass=True); actual=_diff(fa,fb)
    return VertexEditCertificate(k,deleted,inserted,tuple(changed_counts),float(actual),float(bound),bool(actual<=bound+1e-10))
