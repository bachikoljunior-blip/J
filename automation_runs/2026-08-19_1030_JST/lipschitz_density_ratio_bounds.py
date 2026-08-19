from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np


def _safe_exp(x: float) -> float:
    return math.inf if x >= 700.0 else math.exp(x)


def _box(x, lo, hi):
    x=np.asarray(x,dtype=float); lo=np.asarray(lo,dtype=float); hi=np.asarray(hi,dtype=float)
    if x.ndim!=2 or lo.shape!=(x.shape[1],) or hi.shape!=lo.shape or np.any(hi<=lo):
        raise ValueError('bad bounded-domain data')
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(lo)) or not np.all(np.isfinite(hi)):
        raise ValueError('finite values required')
    return x,lo,hi

@dataclass(frozen=True)
class CellRatioBounds:
    domain_lower: np.ndarray
    domain_upper: np.ndarray
    bins: tuple[int,...]
    log_ratio_lipschitz: float
    lower: np.ndarray
    upper: np.ndarray
    delta: float
    assumptions: str

    def _index(self, x):
        z=np.asarray(x,dtype=float)
        if z.shape!=self.domain_lower.shape or np.any(z<self.domain_lower) or np.any(z>self.domain_upper):
            return None
        frac=(z-self.domain_lower)/(self.domain_upper-self.domain_lower)
        idx=np.minimum((frac*np.asarray(self.bins)).astype(int),np.asarray(self.bins)-1)
        return tuple(idx.tolist())

    def interval(self,x):
        idx=self._index(x)
        if idx is None:return (0.0,math.inf)
        return float(self.lower[idx]),float(self.upper[idx])


def fit_lipschitz_grid_ratio_bounds(train_x,test_x,*,domain_lower,domain_upper,bins=4,log_ratio_lipschitz:float,delta=.05):
    p,lo,hi=_box(train_x,domain_lower,domain_upper);q,lo2,hi2=_box(test_x,domain_lower,domain_upper)
    if not np.array_equal(lo,lo2) or not np.array_equal(hi,hi2):raise ValueError('domains differ')
    if q.shape[1]!=p.shape[1] or len(q)==0 or len(p)==0:raise ValueError('dimension/sample mismatch')
    if np.any(p<lo) or np.any(p>hi) or np.any(q<lo) or np.any(q>hi):raise ValueError('samples outside declared domain')
    if isinstance(bins,int): bins=(bins,)*p.shape[1]
    bins=tuple(int(b) for b in bins)
    if len(bins)!=p.shape[1] or any(b<1 for b in bins):raise ValueError('bad bins')
    L=float(log_ratio_lipschitz)
    if L<0 or not math.isfinite(L) or not 0<delta<1:raise ValueError('bad smoothness/delta')
    G=int(np.prod(bins))
    ep=math.sqrt(math.log(4*G/delta)/(2*len(p))); eq=math.sqrt(math.log(4*G/delta)/(2*len(q)))
    shape=bins; cp=np.zeros(shape,dtype=int);cq=np.zeros(shape,dtype=int)
    def ids(a):
        f=(a-lo)/(hi-lo); return np.minimum((f*np.asarray(bins)).astype(int),np.asarray(bins)-1)
    for z in ids(p):cp[tuple(z)]+=1
    for z in ids(q):cq[tuple(z)]+=1
    lower=np.zeros(shape,dtype=float); upper=np.full(shape,math.inf,dtype=float)
    widths=(hi-lo)/np.asarray(bins)
    diam=float(np.linalg.norm(widths))
    smooth=_safe_exp(L*diam)
    for idx in np.ndindex(shape):
        pp=cp[idx]/len(p); qq=cq[idx]/len(q)
        pl=max(0.,pp-ep);pu=min(1.,pp+ep);ql=max(0.,qq-eq);qu=min(1.,qq+eq)
        rlo=0. if pu<=0 else ql/pu
        rhi=math.inf if pl<=0 else qu/pl
        lower[idx]=0.0 if not math.isfinite(smooth) else rlo/smooth
        upper[idx]=math.inf if (not math.isfinite(rhi) or not math.isfinite(smooth)) else rhi*smooth
    return CellRatioBounds(lo.copy(),hi.copy(),bins,L,lower,upper,float(delta),
        'P/Q samples are independent iid; domain and grid are fixed independently; Q is absolutely continuous wrt P; log(dQ/dP) is globally L-Lipschitz on the domain with supplied L; simultaneous Hoeffding event has probability at least 1-delta')

@dataclass(frozen=True)
class SlabRatioBounds:
    domain_lower: np.ndarray
    domain_upper: np.ndarray
    direction: np.ndarray
    edges: np.ndarray
    log_ratio_lipschitz: float
    lower: np.ndarray
    upper: np.ndarray
    delta: float
    assumptions: str

    def interval(self,x):
        x=np.asarray(x,dtype=float)
        if x.shape!=self.domain_lower.shape or np.any(x<self.domain_lower) or np.any(x>self.domain_upper):return (0.,math.inf)
        t=float(x@self.direction); j=int(np.searchsorted(self.edges,t,side='right')-1)
        j=max(0,min(j,len(self.lower)-1)); return float(self.lower[j]),float(self.upper[j])


def fit_lipschitz_slab_ratio_bounds(train_x,test_x,*,domain_lower,domain_upper,direction,bins=8,log_ratio_lipschitz:float,delta=.05):
    p,lo,hi=_box(train_x,domain_lower,domain_upper);q,_,_=_box(test_x,domain_lower,domain_upper)
    if q.shape[1]!=p.shape[1] or np.any(p<lo) or np.any(p>hi) or np.any(q<lo) or np.any(q>hi):raise ValueError('bad samples')
    v=np.asarray(direction,dtype=float)
    if v.shape!=(p.shape[1],) or not np.all(np.isfinite(v)) or np.linalg.norm(v)<=0:raise ValueError('bad direction')
    v=v/np.linalg.norm(v); bins=int(bins);L=float(log_ratio_lipschitz)
    if bins<1 or L<0 or not 0<delta<1:raise ValueError('bad controls')
    corners_lo=np.where(v>=0,lo,hi); corners_hi=np.where(v>=0,hi,lo)
    tlo=float(corners_lo@v); thi=float(corners_hi@v); edges=np.linspace(tlo,thi,bins+1)
    ip=np.minimum(np.searchsorted(edges,p@v,side='right')-1,bins-1); iq=np.minimum(np.searchsorted(edges,q@v,side='right')-1,bins-1)
    ip=np.maximum(ip,0);iq=np.maximum(iq,0)
    G=bins; ep=math.sqrt(math.log(4*G/delta)/(2*len(p)));eq=math.sqrt(math.log(4*G/delta)/(2*len(q)))
    lower=np.zeros(bins);upper=np.full(bins,math.inf)
    diam=float(np.linalg.norm(hi-lo)); smooth=_safe_exp(L*diam)
    for j in range(bins):
        pp=np.mean(ip==j);qq=np.mean(iq==j);pl=max(0.,pp-ep);pu=min(1.,pp+ep);ql=max(0.,qq-eq);qu=min(1.,qq+eq)
        rlo=0. if pu<=0 else ql/pu
        lower[j]=0.0 if not math.isfinite(smooth) else rlo/smooth
        rhi=math.inf if pl<=0 else qu/pl;upper[j]=math.inf if (not math.isfinite(rhi) or not math.isfinite(smooth)) else rhi*smooth
    return SlabRatioBounds(lo.copy(),hi.copy(),v,edges,L,lower,upper,float(delta),
        'same as grid bound, but fixed slab partition avoids exponential cell count; bounds may become vacuous as dimension/domain diameter grows')
