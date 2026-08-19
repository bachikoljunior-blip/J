from __future__ import annotations
from dataclasses import dataclass
import math,numpy as np
@dataclass(frozen=True)
class NoiseTolerantCertificate:
    status:str;forced_pairs:tuple[tuple[int,int],...];witness_pairs:tuple[tuple[int,int],...];minimum_common_nodes:int;witness_disagreements:int;max_witness_attribute_distance:float;explored_nodes:int;reason:str

def _validate(graph):
    a=np.asarray(graph[0],dtype=np.int8);x=np.asarray(graph[1],dtype=float)
    if x.ndim==1:x=x[:,None]
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)) or not np.all((a==0)|(a==1)):raise ValueError('expected simple graph')
    if x.ndim!=2 or len(x)!=len(a) or not np.all(np.isfinite(x)):raise ValueError('bad finite attributes')
    return a,x

def _dis(a,b,pairs):return sum(int(bool(a[i,u])!=bool(b[j,v])) for q,(i,j) in enumerate(pairs) for u,v in pairs[:q])
class _CompatSearch:
    def __init__(self,a,b,compat,k,budget,max_nodes,forbidden=None):
        self.a=a;self.b=b;self.compat=compat;self.k=k;self.budget=budget;self.max_nodes=max_nodes;self.forbidden=forbidden;self.nodes=0;self.cutoff=False;self.answer=None;self.cand={i:tuple(np.flatnonzero(compat[i]).tolist()) for i in range(len(a))};self.order=sorted(range(len(a)),key=lambda i:(len(self.cand[i]),-int(a[i].sum()),i))
    def cap(self,d,used):
        targets=set();
        for i in self.order[d:]:targets.update(j for j in self.cand[i] if j not in used and self.forbidden!=(i,j))
        return min(len(self.order)-d,len(targets))
    def run(self):self.dfs(0,set(),[],0);return self.answer,self.cutoff,self.nodes
    def dfs(self,d,used,pairs,dis):
        if self.answer is not None or self.cutoff:return
        self.nodes+=1
        if self.nodes>self.max_nodes:self.cutoff=True;return
        if len(pairs)==self.k:self.answer=tuple(sorted(pairs));return
        if d>=len(self.order):return
        need=self.k-len(pairs)
        if len(self.order)-d<need or self.cap(d,used)<need:return
        i=self.order[d];opts=[]
        for j in self.cand[i]:
            if j in used or self.forbidden==(i,j):continue
            inc=sum(int(bool(self.a[i,u])!=bool(self.b[j,v])) for u,v in pairs)
            if dis+inc<=self.budget:opts.append((inc,abs(int(self.a[i].sum())-int(self.b[j].sum())),j))
        for inc,_,j in sorted(opts):
            used.add(j);pairs.append((i,j));self.dfs(d+1,used,pairs,dis+inc);pairs.pop();used.remove(j)
            if self.answer is not None or self.cutoff:return
        if len(self.order)-(d+1)>=need:self.dfs(d+1,used,pairs,dis)
def infer_noise_tolerant_forcing(graph_a,graph_b,*,max_unmatched_total:int,max_common_edge_disagreements:int,attribute_linf_tolerance:float,max_nodes_per_search:int=200_000,max_exclusion_checks:int=200):
    if min(max_unmatched_total,max_common_edge_disagreements)<0 or attribute_linf_tolerance<0:raise ValueError('bad budget/tolerance')
    a,x=_validate(graph_a);b,y=_validate(graph_b)
    if x.shape[1]!=y.shape[1]:return NoiseTolerantCertificate('inconsistent_constraints',(),(),0,0,0.0,0,'attribute dimensions differ')
    n,m=len(a),len(b);k=max(0,math.ceil((n+m-max_unmatched_total)/2))
    if k>min(n,m):return NoiseTolerantCertificate('inconsistent_constraints',(),(),k,0,0.0,0,'unmatched budget impossible')
    compat=np.max(np.abs(x[:,None,:]-y[None,:,:]),axis=2)<=attribute_linf_tolerance+1e-15;s=_CompatSearch(a,b,compat,k,max_common_edge_disagreements,max_nodes_per_search);w,cut,nodes=s.run()
    if w is None:return NoiseTolerantCertificate('undetermined_search_budget' if cut else 'inconsistent_constraints',(),(),k,0,0.0,nodes,'no witness before cutoff; no identities released' if cut else 'no compatible budget-respecting partial mapping')
    forced=[];any_cut=False
    for e in w[:max_exclusion_checks]:
        q=_CompatSearch(a,b,compat,k,max_common_edge_disagreements,max_nodes_per_search,forbidden=e);alt,c,n2=q.run();nodes+=n2
        if c:any_cut=True
        elif alt is None:forced.append(e)
    dmax=max((float(np.max(np.abs(x[i]-y[j]))) for i,j in w),default=0.0);status='certified_forced_pairs' if forced else ('undetermined_exclusion_budget' if any_cut or len(w)>max_exclusion_checks else 'feasible_no_forced_pairs')
    return NoiseTolerantCertificate(status,tuple(sorted(forced)),tuple(sorted(w)),k,_dis(a,b,list(w)),dmax,nodes,'forced pairs have no alternative mapping under explicit attribute-tolerance and edge/unmatched budgets; cutoffs fail closed')
