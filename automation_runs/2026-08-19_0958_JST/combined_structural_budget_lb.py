from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
import heapq, math
import numpy as np

@dataclass(frozen=True)
class CombinedStructuralCertificate:
    minimum_common_nodes:int; attribute_capacity:int; degree_lower_bound:int; triangle_lower_bound:int; combined_lower_bound:int; inconsistent:bool; reason:str

def _validate(graph):
    a=np.asarray(graph[0],dtype=np.int8); x=np.asarray(graph[1]);
    if x.ndim==1:x=x[:,None]
    if a.ndim!=2 or a.shape[0]!=a.shape[1] or not np.array_equal(a,a.T) or np.any(np.diag(a)) or not np.all((a==0)|(a==1)):raise ValueError('expected simple undirected adjacency')
    if x.ndim!=2 or len(x)!=len(a):raise ValueError('attributes must align')
    return a,x

def _key(row):return tuple(np.asarray(row).tolist())

def _minimum_cost_k_matching(left,right,costs,k):
    left,right=tuple(left),tuple(right)
    if k<0 or k>min(len(left),len(right)):return None
    if k==0:return 0
    S=0;ln={u:1+i for i,u in enumerate(left)};rn={v:1+len(left)+i for i,v in enumerate(right)};T=1+len(left)+len(right);N=T+1;g=[[] for _ in range(N)]
    def add(u,v,cap,cost):g[u].append([v,len(g[v]),cap,int(cost)]);g[v].append([u,len(g[u])-1,0,-int(cost)])
    for u in left:add(S,ln[u],1,0)
    for v in right:add(rn[v],T,1,0)
    for (u,v),c in costs.items():add(ln[u],rn[v],1,c)
    pot=[0]*N;total=0
    for _ in range(k):
        INF=10**18;dist=[INF]*N;prev=[None]*N;dist[S]=0;pq=[(0,S)]
        while pq:
            d,u=heapq.heappop(pq)
            if d!=dist[u]:continue
            for ei,e in enumerate(g[u]):
                v,rev,cap,c=e
                if cap<=0:continue
                nd=d+c+pot[u]-pot[v]
                if nd<dist[v]:dist[v]=nd;prev[v]=(u,ei);heapq.heappush(pq,(nd,v))
        if dist[T]==INF:return None
        for v in range(N):
            if dist[v]<INF:pot[v]+=dist[v]
        v=T
        while v!=S:
            u,ei=prev[v];e=g[u][ei];total+=e[3];e[2]-=1;g[v][e[1]][2]+=1;v=u
    return int(total)

def _selected_degree_interval(adj,node,k):
    d=int(adj[node].sum());omitted=len(adj)-k;return max(0,d-omitted),min(d,k-1)

def _gap(a,b):
    if a[1]<b[0]:return b[0]-a[1]
    if b[1]<a[0]:return a[0]-b[1]
    return 0

def _triangle_interval(adj,k):
    a=np.asarray(adj,dtype=np.int64);a3=(a@a)@a;td=np.diag(a3)//2;total=int(td.sum()//3);omitted=len(a)-k;rem=int(np.sort(td)[::-1][:omitted].sum()) if omitted else 0
    return max(0,total-rem),min(total,math.comb(k,3) if k>=3 else 0)

def infer_combined_structural_lower_bound(graph_a,graph_b,*,max_unmatched_total:int,max_common_edge_disagreements:int|None=None):
    if max_unmatched_total<0:raise ValueError('bad unmatched budget')
    a,x=_validate(graph_a);b,y=_validate(graph_b)
    if x.shape[1]!=y.shape[1]:return CombinedStructuralCertificate(0,0,0,0,0,True,'attribute dimensions differ')
    n,m=len(a),len(b);k=max(0,math.ceil((n+m-max_unmatched_total)/2));aa=defaultdict(list);bb=defaultdict(list)
    for i in range(n):aa[_key(x[i])].append(i)
    for j in range(m):bb[_key(y[j])].append(j)
    cap=sum(min(len(aa[q]),len(bb[q])) for q in aa.keys()|bb.keys())
    if k>min(n,m) or cap<k:return CombinedStructuralCertificate(k,cap,0,0,0,True,'unmatched/attribute inventory infeasible')
    ia=[_selected_degree_interval(a,i,k) for i in range(n)];ib=[_selected_degree_interval(b,j,k) for j in range(m)];costs={}
    for q in aa.keys()&bb.keys():
        for i in aa[q]:
            for j in bb[q]:costs[(i,j)]=_gap(ia[i],ib[j])
    s=_minimum_cost_k_matching(range(n),range(m),costs,k)
    if s is None:return CombinedStructuralCertificate(k,cap,0,0,0,True,'same-attribute candidate graph infeasible')
    dlb=math.ceil(s/2);tg=_gap(_triangle_interval(a,k),_triangle_interval(b,k));tlb=0 if k<=2 or tg==0 else math.ceil(tg/(k-2));comb=max(dlb,tlb);bad=max_common_edge_disagreements is not None and comb>max_common_edge_disagreements
    return CombinedStructuralCertificate(k,cap,int(dlb),int(tlb),int(comb),bool(bad),'combined structural lower bound exceeds edge budget' if bad else 'safe max of degree-interval assignment and triangle-motif lower bounds')
