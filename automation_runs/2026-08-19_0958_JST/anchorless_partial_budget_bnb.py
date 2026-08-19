from __future__ import annotations
from dataclasses import dataclass
from collections import Counter
import math,numpy as np
@dataclass(frozen=True)
class BnBPartialCertificate:
    status:str;forced_pairs:tuple[tuple[int,int],...];witness_pairs:tuple[tuple[int,int],...];minimum_common_nodes:int;witness_disagreements:int;explored_nodes:int;exclusion_checks:int;reason:str

def _validate(graph):
    a=np.asarray(graph[0],dtype=np.int8);x=np.asarray(graph[1]);
    if x.ndim==1:x=x[:,None]
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)) or not np.all((a==0)|(a==1)):raise ValueError('expected simple graph')
    if x.ndim!=2 or len(x)!=len(a):raise ValueError('bad attributes')
    return a,x

def _key(row):return tuple(np.asarray(row).tolist())
def _dis(a,b,pairs):return sum(int(bool(a[i,u])!=bool(b[j,v])) for q,(i,j) in enumerate(pairs) for u,v in pairs[:q])
class _Search:
    def __init__(self,a,x,b,y,k,budget,max_nodes,forbidden=None):
        self.a=a;self.x=x;self.b=b;self.y=y;self.k=k;self.budget=budget;self.max_nodes=max_nodes;self.forbidden=forbidden;self.nodes=0;self.cutoff=False;self.answer=None;self.kx=[_key(r) for r in x];self.ky=[_key(r) for r in y];tb={}
        for j,q in enumerate(self.ky):tb.setdefault(q,[]).append(j)
        self.cand={i:tuple(tb.get(self.kx[i],())) for i in range(len(a))};self.order=sorted(range(len(a)),key=lambda i:(len(self.cand[i]),-int(a[i].sum()),i))
    def capacity(self,depth,used):
        sx=Counter(self.kx[i] for i in self.order[depth:]);ty=Counter(self.ky[j] for j in range(len(self.b)) if j not in used);return sum(min(sx[q],ty[q]) for q in sx.keys()|ty.keys())
    def run(self):self._dfs(0,set(),[],0);return self.answer,self.cutoff,self.nodes
    def _dfs(self,depth,used,pairs,dis):
        if self.answer is not None or self.cutoff:return
        self.nodes+=1
        if self.nodes>self.max_nodes:self.cutoff=True;return
        if len(pairs)==self.k:self.answer=tuple(sorted(pairs));return
        if depth>=len(self.order):return
        need=self.k-len(pairs)
        if len(self.order)-depth<need or self.capacity(depth,used)<need:return
        i=self.order[depth];opts=[]
        for j in self.cand[i]:
            if j in used or self.forbidden==(i,j):continue
            inc=sum(int(bool(self.a[i,u])!=bool(self.b[j,v])) for u,v in pairs)
            if dis+inc<=self.budget:opts.append((inc,abs(int(self.a[i].sum())-int(self.b[j].sum())),j))
        for inc,_,j in sorted(opts):
            used.add(j);pairs.append((i,j));self._dfs(depth+1,used,pairs,dis+inc);pairs.pop();used.remove(j)
            if self.answer is not None or self.cutoff:return
        if len(self.order)-(depth+1)>=need:self._dfs(depth+1,used,pairs,dis)
def infer_anchorless_partial_budget_bnb(graph_a,graph_b,*,max_unmatched_total:int,max_common_edge_disagreements:int,max_nodes_per_search:int=200_000,max_exclusion_checks:int=200):
    a,x=_validate(graph_a);b,y=_validate(graph_b)
    if x.shape[1]!=y.shape[1]:return BnBPartialCertificate('inconsistent_constraints',(),(),0,0,0,0,'attribute dimensions differ')
    n,m=len(a),len(b);k=max(0,math.ceil((n+m-max_unmatched_total)/2))
    if k>min(n,m):return BnBPartialCertificate('inconsistent_constraints',(),(),k,0,0,0,'unmatched budget impossible')
    s=_Search(a,x,b,y,k,max_common_edge_disagreements,max_nodes_per_search);w,cut,nodes=s.run()
    if w is None:return BnBPartialCertificate('undetermined_search_budget' if cut else 'inconsistent_constraints',(),(),k,0,nodes,0,'no witness before cutoff' if cut else 'no feasible partial mapping')
    forced=[];checks=0;any_cut=False;total=nodes
    for e in w:
        if checks>=max_exclusion_checks:break
        checks+=1;s=_Search(a,x,b,y,k,max_common_edge_disagreements,max_nodes_per_search,forbidden=e);alt,c,n2=s.run();total+=n2
        if c:any_cut=True
        elif alt is None:forced.append(e)
    status='certified_forced_pairs' if forced else ('undetermined_exclusion_budget' if any_cut or checks<len(w) else 'feasible_no_forced_pairs')
    return BnBPartialCertificate(status,tuple(sorted(forced)),tuple(sorted(w)),k,_dis(a,b,list(w)),total,checks,'forced pairs have no alternative feasible minimum-cardinality mapping; cutoffs never create a forced claim')
