from __future__ import annotations
from dataclasses import dataclass
from typing import List,Sequence,Tuple
import math,numpy as np
from wl_attributed_kernel import _initial_colors,_refine_colors,wl_attributed_feature_map
from rff_stability_bounds import exact_rbf,rff_atomic_hoeffding_radius

@dataclass(frozen=True)
class PairApproximationCertificate:
    matched_atomic_pairs:int; absolute_error_bound:float; exact_kernel:float; approximate_kernel:float; realized_absolute_error:float; passed_realized_check:bool
@dataclass(frozen=True)
class FamilyApproximationCertificate:
    failure_probability:float; total_atomic_comparisons:int; atomic_uniform_radius:float; pair_certificates:Tuple[PairApproximationCertificate,...]

def _validate_graph(graph):
    a=(np.asarray(graph[0])!=0); x=np.asarray(graph[1],dtype=float)
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)): raise ValueError("expected simple undirected adjacency")
    if x.ndim!=2 or x.shape[0]!=a.shape[0] or x.shape[1]<1 or not np.all(np.isfinite(x)): raise ValueError("bad attributes")
    return a,x
def color_history(adjacency,iterations):
    a=(np.asarray(adjacency)!=0); c=_initial_colors(a); out=[tuple(c)]
    for _ in range(iterations): c=_refine_colors(a,c); out.append(tuple(c))
    return tuple(out)
def _groups(colors):
    out={}
    for i,c in enumerate(colors): out.setdefault(c,[]).append(i)
    return out
def matched_atomic_pair_count(graph_a,graph_b,*,iterations=3):
    a,_=_validate_graph(graph_a); b,_=_validate_graph(graph_b); total=0
    for ca,cb in zip(color_history(a,iterations),color_history(b,iterations)):
        ga,gb=_groups(ca),_groups(cb)
        for c in set(ga)&set(gb): total+=len(ga[c])*len(gb[c])
    return int(total)
def exact_structural_rbf_kernel(graph_a,graph_b,*,iterations=3,bandwidth=1.0):
    a,x=_validate_graph(graph_a); b,y=_validate_graph(graph_b)
    if x.shape[1]!=y.shape[1]: raise ValueError("attribute dimensions must match")
    total=0.0
    for ca,cb in zip(color_history(a,iterations),color_history(b,iterations)):
        ga,gb=_groups(ca),_groups(cb)
        for c in set(ga)&set(gb):
            for i in ga[c]:
                for j in gb[c]: total+=exact_rbf(x[i],y[j],bandwidth)
    return float(total/math.sqrt(a.shape[0]*b.shape[0]))
def approximate_structural_rff_kernel(graph_a,graph_b,*,iterations=3,rff_components=128,bandwidth=1.0,seed=0):
    a,x=_validate_graph(graph_a); b,y=_validate_graph(graph_b)
    fa=wl_attributed_feature_map(a,x,iterations=iterations,rff_components=rff_components,bandwidth=bandwidth,seed=seed,normalize_node_mass=True)
    fb=wl_attributed_feature_map(b,y,iterations=iterations,rff_components=rff_components,bandwidth=bandwidth,seed=seed,normalize_node_mass=True)
    if len(fa)>len(fb): fa,fb=fb,fa
    return float(sum(v*fb.get(k,0.0) for k,v in fa.items()))
def finite_family_certificate(graph_pairs:Sequence[Tuple[tuple,tuple]],*,iterations=3,rff_components=128,bandwidth=1.0,seed=0,failure_probability=.05):
    if not graph_pairs: raise ValueError("graph_pairs must be nonempty")
    counts=[matched_atomic_pair_count(a,b,iterations=iterations) for a,b in graph_pairs]; M=int(sum(counts))
    radius=0.0 if M==0 else rff_atomic_hoeffding_radius(rff_components,failure_probability/M)
    certs=[]
    for (ga,gb),count in zip(graph_pairs,counts):
        a,_=_validate_graph(ga); b,_=_validate_graph(gb); exact=exact_structural_rbf_kernel(ga,gb,iterations=iterations,bandwidth=bandwidth); approx=approximate_structural_rff_kernel(ga,gb,iterations=iterations,rff_components=rff_components,bandwidth=bandwidth,seed=seed)
        bound=0.0 if count==0 else radius*count/math.sqrt(a.shape[0]*b.shape[0]); err=abs(approx-exact)
        certs.append(PairApproximationCertificate(count,float(bound),exact,approx,float(err),bool(err<=bound+1e-10)))
    return FamilyApproximationCertificate(float(failure_probability),M,float(radius),tuple(certs))
