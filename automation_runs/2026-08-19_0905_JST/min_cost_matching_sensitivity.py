from __future__ import annotations
from dataclasses import dataclass
from typing import Dict,Iterable,Tuple,Optional
import heapq

@dataclass(frozen=True)
class MatchingSensitivity:
    minimum_cost:int; matching:Tuple[Tuple[int,int],...]; alternative_cost_without:Tuple[Tuple[Tuple[int,int],Optional[int]],...]

def _build_optimal_residual(left,right,costs,k):
    left=tuple(left);right=tuple(right)
    if k<0 or k>min(len(left),len(right)):return None
    S=0;L={u:1+i for i,u in enumerate(left)};R={v:1+len(left)+i for i,v in enumerate(right)};T=1+len(left)+len(right);N=T+1;g=[[] for _ in range(N)]
    def add(u,v,cap,c,tag=None):g[u].append([v,len(g[v]),cap,int(c),tag]);g[v].append([u,len(g[u])-1,0,-int(c),None])
    for u in left:add(S,L[u],1,0)
    for v in right:add(R[v],T,1,0)
    for (u,v),c in costs.items():
        if u in L and v in R:
            if c<0:raise ValueError('nonnegative original costs required')
            add(L[u],R[v],1,int(c),(u,v))
    pot=[0]*N;total=0
    for _ in range(k):
        INF=10**18;d=[INF]*N;pr=[None]*N;d[S]=0;pq=[(0,S)]
        while pq:
            du,u=heapq.heappop(pq)
            if du!=d[u]:continue
            for ei,e in enumerate(g[u]):
                v,rev,cap,c,tag=e
                if cap<=0:continue
                nd=du+c+pot[u]-pot[v]
                if nd<d[v]:d[v]=nd;pr[v]=(u,ei);heapq.heappush(pq,(nd,v))
        if d[T]>=INF:return None
        for z in range(N):
            if d[z]<INF:pot[z]+=d[z]
        v=T
        while v!=S:
            u,ei=pr[v];e=g[u][ei];total+=e[3];e[2]-=1;g[v][e[1]][2]+=1;v=u
    matching=[];edge_meta={}
    for u in left:
        for e in g[L[u]]:
            if e[4] is not None and e[2]==0:matching.append(e[4]);edge_meta[e[4]]=(L[u],e[0],int(e[3]))
    return int(total),tuple(sorted(matching)),g,L,R,edge_meta

def _feasible_potential(g):
    n=len(g);h=[0]*n
    for _ in range(n):
        changed=False
        for u in range(n):
            hu=h[u]
            for v,rev,cap,c,tag in g[u]:
                if cap>0 and h[v]>hu+c:h[v]=hu+c;changed=True
        if not changed:return h
    raise RuntimeError('negative cycle in residual network')

def _shortest_reduced(g,h,s,t):
    INF=10**18;d=[INF]*len(g);d[s]=0;pq=[(0,s)]
    while pq:
        du,u=heapq.heappop(pq)
        if du!=d[u]:continue
        if u==t:break
        for v,rev,cap,c,tag in g[u]:
            if cap<=0:continue
            rc=c+h[u]-h[v]
            if rc<0 and rc>-1e-9:rc=0
            if rc<0:raise RuntimeError('invalid reduced cost')
            nd=du+rc
            if nd<d[v]:d[v]=nd;heapq.heappush(pq,(nd,v))
    if d[t]>=INF:return None
    return int(d[t]-h[s]+h[t])

def minimum_cost_matching_exclusion_sensitivity(left:Iterable[int],right:Iterable[int],costs:Dict[Tuple[int,int],int],k:int)->Optional[MatchingSensitivity]:
    built=_build_optimal_residual(left,right,costs,k)
    if built is None:return None
    opt,matching,g,L,R,meta=built;h=_feasible_potential(g);out=[]
    for e in matching:
        lu,rv,c=meta[e];path=_shortest_reduced(g,h,lu,rv);alt=None if path is None else int(opt+path-c);out.append((e,alt))
    return MatchingSensitivity(opt,matching,tuple(out))
