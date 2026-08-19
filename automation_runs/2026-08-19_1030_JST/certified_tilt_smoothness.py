from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np


def tilt_mean(theta: float) -> float:
    t=float(theta)
    if abs(t)<1e-6:
        return 0.5 + t/12.0 - t**3/720.0
    if t > 0:
        return 1.0/(-math.expm1(-t)) - 1.0/t
    return math.exp(t)/math.expm1(t) - 1.0/t


def _invert_mean(mu: float, theta_lo: float, theta_hi: float, iters: int = 100) -> float:
    if mu <= tilt_mean(theta_lo): return float(theta_lo)
    if mu >= tilt_mean(theta_hi): return float(theta_hi)
    lo,hi=float(theta_lo),float(theta_hi)
    for _ in range(iters):
        mid=(lo+hi)/2.0
        if tilt_mean(mid) < mu: lo=mid
        else: hi=mid
    return (lo+hi)/2.0

@dataclass(frozen=True)
class ExponentialTiltSmoothnessCertificate:
    theta_lower: np.ndarray
    theta_upper: np.ndarray
    l2_log_ratio_lipschitz_upper: float
    delta: float
    sample_size: int
    status: str
    assumptions: str


def certify_box_exponential_tilt_smoothness(q_samples, *, theta_lower=-4.0, theta_upper=4.0, delta=.05):
    x=np.asarray(q_samples,dtype=float)
    if x.ndim==1:x=x[:,None]
    if x.ndim!=2 or len(x)==0 or not np.all(np.isfinite(x)) or np.any(x<0) or np.any(x>1):
        raise ValueError('q_samples must lie in [0,1]^d')
    d=x.shape[1]
    lo=np.broadcast_to(np.asarray(theta_lower,dtype=float), (d,)).copy()
    hi=np.broadcast_to(np.asarray(theta_upper,dtype=float), (d,)).copy()
    if np.any(~np.isfinite(lo)) or np.any(~np.isfinite(hi)) or np.any(lo>=hi) or not 0<delta<1:
        raise ValueError('bad parameter box/delta')
    eps=math.sqrt(math.log(2*d/delta)/(2*len(x)))
    m=x.mean(axis=0)
    tl=np.empty(d);tu=np.empty(d)
    for j in range(d):
        ml=max(0.0,float(m[j]-eps)); mu=min(1.0,float(m[j]+eps))
        family_lo=tilt_mean(float(lo[j])); family_hi=tilt_mean(float(hi[j]))
        if mu < family_lo or ml > family_hi:
            return ExponentialTiltSmoothnessCertificate(lo,hi,math.inf,float(delta),len(x),'inconsistent_family',
                'declared product exponential-tilt family is contradicted by the simultaneous mean confidence event')
        tl[j]=_invert_mean(max(ml,family_lo),float(lo[j]),float(hi[j]))
        tu[j]=_invert_mean(min(mu,family_hi),float(lo[j]),float(hi[j]))
    far=np.maximum(np.abs(tl),np.abs(tu))
    L=float(np.linalg.norm(far))
    return ExponentialTiltSmoothnessCertificate(tl,tu,L,float(delta),len(x),'certified_under_family',
        'P is Uniform([0,1]^d); Q is the declared product exponential tilt exp(theta^T x)/Z(theta); theta lies in the declared box; Q samples are iid; simultaneous Hoeffding mean intervals cover theta with probability at least 1-delta')


def sample_box_exponential_tilt(rng, n: int, theta):
    theta=np.asarray(theta,dtype=float)
    if theta.ndim==0:theta=theta[None]
    u=rng.random((int(n),len(theta)));x=np.empty_like(u)
    for j,t in enumerate(theta):
        t=float(t)
        if abs(t)<1e-10:
            x[:,j]=u[:,j]
        elif t > 50.0:
            a=np.log1p(-u[:,j])
            b=np.log(u[:,j])+t
            x[:,j]=np.logaddexp(a,b)/t
        else:
            x[:,j]=np.log1p(u[:,j]*math.expm1(t))/t
    return x

@dataclass(frozen=True)
class SmoothnessEnvelopeDecision:
    status: str
    lipschitz_upper: float
    failure_probability: float
    conditional_on: str
    reason: str


def resolve_smoothness_envelope(*, evidence_kind: str, external_lipschitz=None, q_samples=None,
                                theta_lower=-4.0, theta_upper=4.0, delta=.05):
    if evidence_kind == 'externally_certified_lipschitz':
        L=float(external_lipschitz) if external_lipschitz is not None else math.inf
        if not math.isfinite(L) or L < 0:
            return SmoothnessEnvelopeDecision('abstain_invalid_external_certificate',math.inf,1.0,'none','finite nonnegative external L required')
        return SmoothnessEnvelopeDecision('certified_external',L,0.0,'external certification','L supplied by an external certification boundary')
    if evidence_kind == 'declared_product_exponential_tilt_contract':
        if q_samples is None:
            return SmoothnessEnvelopeDecision('abstain_missing_samples',math.inf,1.0,'none','Q samples required')
        c=certify_box_exponential_tilt_smoothness(q_samples,theta_lower=theta_lower,theta_upper=theta_upper,delta=delta)
        if c.status!='certified_under_family':
            return SmoothnessEnvelopeDecision('abstain_family_inconsistent',math.inf,1.0,'none','declared family contradicted by confidence event')
        return SmoothnessEnvelopeDecision('certified_conditional_on_family',c.l2_log_ratio_lipschitz_upper,float(delta),c.assumptions,'finite-sample parameter uncertainty propagated to global gradient norm')
    return SmoothnessEnvelopeDecision('abstain_uncertified_model_membership',math.inf,1.0,'none','finite-sample fit diagnostics alone cannot certify an unseen-region global derivative bound')
