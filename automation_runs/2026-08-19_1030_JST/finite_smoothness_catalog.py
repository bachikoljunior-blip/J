from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np

@dataclass(frozen=True)
class CatalogModel:
    name: str
    feature_mean: np.ndarray
    log_ratio_lipschitz_upper: float

@dataclass(frozen=True)
class CatalogSmoothnessCertificate:
    surviving_models: tuple[str,...]
    lipschitz_upper: float
    delta: float
    status: str
    assumptions: str


def certify_finite_catalog_smoothness(feature_samples, models, *, feature_lower=0.0, feature_upper=1.0, delta=.05):
    z=np.asarray(feature_samples,dtype=float)
    if z.ndim==1:z=z[:,None]
    if z.ndim!=2 or len(z)==0 or not np.all(np.isfinite(z)):raise ValueError('finite nonempty 2-D features required')
    lo=np.broadcast_to(np.asarray(feature_lower,dtype=float),(z.shape[1],))
    hi=np.broadcast_to(np.asarray(feature_upper,dtype=float),(z.shape[1],))
    if np.any(hi<=lo) or np.any(z<lo) or np.any(z>hi) or not 0<delta<1:raise ValueError('bad bounds/delta')
    models=tuple(models)
    if not models:raise ValueError('nonempty model catalog required')
    for m in models:
        mu=np.asarray(m.feature_mean,dtype=float)
        if mu.shape!=(z.shape[1],) or np.any(~np.isfinite(mu)) or not math.isfinite(m.log_ratio_lipschitz_upper) or m.log_ratio_lipschitz_upper<0:
            raise ValueError('invalid catalog model')
    width=hi-lo
    eps=width*np.sqrt(math.log(2*z.shape[1]/delta)/(2*len(z)))
    mean=z.mean(axis=0)
    surviving=[]
    for m in models:
        mu=np.asarray(m.feature_mean,dtype=float)
        if np.all(np.abs(mu-mean)<=eps+1e-15):surviving.append(m)
    if not surviving:
        return CatalogSmoothnessCertificate((),math.inf,float(delta),'inconsistent_catalog',
            'finite audited catalog membership was assumed, but no model survived the simultaneous concentration event')
    L=max(float(m.log_ratio_lipschitz_upper) for m in surviving)
    return CatalogSmoothnessCertificate(tuple(m.name for m in surviving),L,float(delta),'certified_conditional_on_catalog',
        'the true Q is exactly one supplied audited catalog model; diagnostic features are iid and bounded by supplied limits; model feature means and model global log-ratio Lipschitz bounds are exact/proven')
