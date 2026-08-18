from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
import math, numpy as np
from wl_attributed_kernel import RFFConfig, wl_attributed_feature_map

@dataclass(frozen=True)
class FeatureStabilityCertificate:
    actual_l2: float
    upper_bound_l2: float
    lipschitz_constant: float
    frobenius_perturbation: float
    passed: bool

def _diff(a:Mapping,b:Mapping)->float:
    return math.sqrt(sum((a.get(k,0.0)-b.get(k,0.0))**2 for k in set(a)|set(b)))
def _norm(a:Mapping)->float:
    return math.sqrt(sum(v*v for v in a.values()))
def rff_attribute_lipschitz(config:RFFConfig)->float:
    w,_=config.matrices(); spectral=float(np.linalg.svd(w,compute_uv=False)[0])
    return math.sqrt(2.0/config.components)*spectral

def graph_feature_stability_certificate(adjacency,x,y,*,iterations=3,rff_components=32,bandwidth=1.0,seed=0):
    x=np.asarray(x,dtype=float); y=np.asarray(y,dtype=float)
    if x.shape!=y.shape or x.ndim!=2: raise ValueError("x and y must have same 2-D shape")
    cfg=RFFConfig(x.shape[1],rff_components,bandwidth,seed); L=rff_attribute_lipschitz(cfg)
    fx=wl_attributed_feature_map(adjacency,x,iterations=iterations,rff_components=rff_components,bandwidth=bandwidth,seed=seed,normalize_node_mass=True)
    fy=wl_attributed_feature_map(adjacency,y,iterations=iterations,rff_components=rff_components,bandwidth=bandwidth,seed=seed,normalize_node_mass=True)
    actual=_diff(fx,fy); perturb=float(np.linalg.norm(x-y,ord="fro")); bound=math.sqrt(iterations+1.0)*L*perturb
    return FeatureStabilityCertificate(actual,bound,L,perturb,actual<=bound+1e-10)

def normalized_kernel_change_bound(delta_feature_bound,norm_before,norm_after):
    m=min(float(norm_before),float(norm_after))
    return 2.0 if m<=0 else min(2.0,2.0*float(delta_feature_bound)/m)
def feature_norm(adjacency,x,*,iterations=3,rff_components=32,bandwidth=1.0,seed=0):
    return _norm(wl_attributed_feature_map(adjacency,x,iterations=iterations,rff_components=rff_components,bandwidth=bandwidth,seed=seed))
def rff_atomic_hoeffding_radius(components,failure_probability):
    if components<1: raise ValueError("components must be positive")
    if not (0.0<failure_probability<1.0): raise ValueError("failure_probability must be in (0,1)")
    return math.sqrt(8.0*math.log(2.0/failure_probability)/components)
def exact_rbf(x,y,bandwidth):
    d=np.asarray(x,dtype=float)-np.asarray(y,dtype=float); return float(math.exp(-0.5*float(d@d)/(bandwidth*bandwidth)))
def approximate_rbf(x,y,config:RFFConfig):
    w,b=config.matrices(); sx=np.cos(w@np.asarray(x,dtype=float)+b); sy=np.cos(w@np.asarray(y,dtype=float)+b)
    return float((2.0/config.components)*(sx@sy))
