from itertools import combinations, permutations
import math
import numpy as np
from partial_alignment_consensus import infer_partial_alignment_consensus


def graph_from_bits(n,bits):
    a=np.zeros((n,n),dtype=int); k=0
    for i in range(n):
        for j in range(i+1,n):
            if (bits>>k)&1: a[i,j]=a[j,i]=1
            k+=1
    return a


def oracle(a,x,b,y,unmatched_budget,edge_budget):
    n,m=len(a),len(b); min_common=max(0,math.ceil((n+m-unmatched_budget)/2)); sols=[]
    for k in range(min_common,min(n,m)+1):
        if n+m-2*k>unmatched_budget: continue
        for src in combinations(range(n),k):
            for dst in combinations(range(m),k):
                for perm in permutations(dst):
                    pairs=tuple(zip(src,perm))
                    if any(not np.array_equal(x[i],y[j]) for i,j in pairs): continue
                    dis=0
                    for q in range(k):
                        for r in range(q):
                            i,j=pairs[q]; u,v=pairs[r]
                            dis += int(bool(a[i,u]) != bool(b[j,v]))
                    if dis<=edge_budget: sols.append(frozenset(pairs))
    if not sols: return (),0,'inconsistent_constraints'
    forced=set(sols[0])
    for s in sols[1:]: forced.intersection_update(s)
    return tuple(sorted(forced)),len(sols),'unique_or_forced_consensus' if forced else 'ambiguous_no_forced_pairs'


def run_validation():
    checked=0; n=m=3
    budgets=((0,0),(0,1),(1,0),(2,0),(2,1),(3,0),(4,0))
    for ga in range(8):
      a=graph_from_bits(n,ga)
      for gb in range(8):
        b=graph_from_bits(m,gb)
        for xa_bits in range(8):
          x=np.array([[(xa_bits>>i)&1] for i in range(n)],dtype=float)
          for yb_bits in range(8):
            y=np.array([[(yb_bits>>j)&1] for j in range(m)],dtype=float)
            for unmatched,edge in budgets:
                exp=oracle(a,x,b,y,unmatched,edge)
                got=infer_partial_alignment_consensus((a,x),(b,y),max_unmatched_total=unmatched,max_common_edge_disagreements=edge,max_states=2_000_000,max_solutions=200_000)
                obs=(got.forced_pairs,got.feasible_solutions,got.status)
                assert obs==exp,(ga,gb,xa_bits,yb_bits,unmatched,edge,exp,obs)
                checked+=1
    rng=np.random.default_rng(4)
    for _ in range(500):
        n=int(rng.integers(1,5)); m=int(rng.integers(1,5))
        a=graph_from_bits(n,int(rng.integers(0,1<<(n*(n-1)//2))))
        b=graph_from_bits(m,int(rng.integers(0,1<<(m*(m-1)//2))))
        x=rng.integers(0,3,size=(n,2)).astype(float); y=rng.integers(0,3,size=(m,2)).astype(float)
        unmatched=int(rng.integers(0,n+m+1)); edge=int(rng.integers(0,4))
        exp=oracle(a,x,b,y,unmatched,edge)
        got=infer_partial_alignment_consensus((a,x),(b,y),max_unmatched_total=unmatched,max_common_edge_disagreements=edge,max_states=2_000_000,max_solutions=200_000)
        assert (got.forced_pairs,got.feasible_solutions,got.status)==exp
        checked+=1
    return checked

if __name__=='__main__': print({'cases':run_validation(),'result':'PASS'})
