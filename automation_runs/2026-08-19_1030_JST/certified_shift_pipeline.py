from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from certified_tilt_smoothness import certify_box_exponential_tilt_smoothness
from lipschitz_density_ratio_bounds import fit_lipschitz_grid_ratio_bounds
from conformal_attribute_compat import calibrate_weight_interval_robust
from guarantee_composition import compose_conditional_coverage

@dataclass(frozen=True)
class ShiftPipelineCertificate:
    status: str
    threshold: float
    unconditional_coverage_lower: float
    smoothness_upper: float
    reason: str


def fit_certified_shift_threshold(*,p_ratio_samples,q_ratio_samples,q_smoothness_samples,
                                  calibration_covariates,calibration_scores,test_covariate,
                                  theta_lower,theta_upper,bins=4,alpha=.1,
                                  smoothness_delta=.01,ratio_delta=.01):
    p=np.asarray(p_ratio_samples,dtype=float);q=np.asarray(q_ratio_samples,dtype=float)
    if p.ndim==1:p=p[:,None]
    if q.ndim==1:q=q[:,None]
    d=p.shape[1]
    if q.shape[1]!=d:return ShiftPipelineCertificate('abstain_dimension_mismatch',math.inf,0.,math.inf,'ratio samples differ in dimension')
    s=certify_box_exponential_tilt_smoothness(q_smoothness_samples,theta_lower=theta_lower,theta_upper=theta_upper,delta=smoothness_delta)
    if s.status!='certified_under_family':
        return ShiftPipelineCertificate('abstain_smoothness_contract',math.inf,0.,math.inf,'smoothness family certificate unavailable')
    rb=fit_lipschitz_grid_ratio_bounds(p,q,domain_lower=np.zeros(d),domain_upper=np.ones(d),bins=bins,log_ratio_lipschitz=s.l2_log_ratio_lipschitz_upper,delta=ratio_delta)
    c=np.asarray(calibration_covariates,dtype=float)
    if c.ndim==1:c=c[:,None]
    scores=np.asarray(calibration_scores,dtype=float)
    if c.ndim!=2 or c.shape[1]!=d or scores.shape!=(len(c),) or np.any(scores<0) or np.any(~np.isfinite(scores)):
        raise ValueError('bad calibration data')
    intervals=[rb.interval(x) for x in c]
    lo=np.array([z[0] for z in intervals]);hi=np.array([z[1] for z in intervals])
    tlo,thi=rb.interval(test_covariate)
    if not np.all(np.isfinite(hi)) or not math.isfinite(thi):
        cov=compose_conditional_coverage(alpha,smoothness_delta,ratio_delta).conservative_unconditional_coverage_lower
        return ShiftPipelineCertificate('abstain_insufficient_support',math.inf,cov,s.l2_log_ratio_lipschitz_upper,'some certified ratio upper bound is infinite')
    zeros=np.zeros((len(scores),1));vals=scores[:,None]
    cal=calibrate_weight_interval_robust(zeros,vals,lo,hi,alpha=alpha)
    threshold=cal.tolerance(tlo,thi)
    cov=compose_conditional_coverage(alpha,smoothness_delta,ratio_delta).conservative_unconditional_coverage_lower
    status='certified_finite_threshold' if math.isfinite(threshold) else 'abstain_uninformative_threshold'
    return ShiftPipelineCertificate(status,float(threshold),cov,s.l2_log_ratio_lipschitz_upper,
        'coverage lower bound composes conditional robust weighted conformal with smoothness and ratio interval failure events by union bound')

@dataclass
class FittedCertifiedShiftCalibrator:
    status: str
    ratio_bounds: object
    robust_calibration: object
    smoothness_upper: float
    unconditional_coverage_lower: float
    reason: str

    def threshold(self,test_covariate):
        if self.status!='ready':return math.inf
        lo,hi=self.ratio_bounds.interval(test_covariate)
        if not math.isfinite(hi):return math.inf
        return float(self.robust_calibration.tolerance(lo,hi))


def fit_certified_shift_calibrator(*,p_ratio_samples,q_ratio_samples,q_smoothness_samples,
                                   calibration_covariates,calibration_scores,
                                   theta_lower,theta_upper,bins=4,alpha=.1,
                                   smoothness_delta=.01,ratio_delta=.01):
    p=np.asarray(p_ratio_samples,dtype=float);q=np.asarray(q_ratio_samples,dtype=float)
    if p.ndim==1:p=p[:,None]
    if q.ndim==1:q=q[:,None]
    if p.ndim!=2 or q.ndim!=2 or p.shape[1]!=q.shape[1]:
        return FittedCertifiedShiftCalibrator('abstain',None,None,math.inf,0.,'dimension mismatch')
    d=p.shape[1]
    s=certify_box_exponential_tilt_smoothness(q_smoothness_samples,theta_lower=theta_lower,theta_upper=theta_upper,delta=smoothness_delta)
    cov=compose_conditional_coverage(alpha,smoothness_delta,ratio_delta).conservative_unconditional_coverage_lower
    if s.status!='certified_under_family':return FittedCertifiedShiftCalibrator('abstain',None,None,math.inf,cov,'smoothness contract unavailable')
    rb=fit_lipschitz_grid_ratio_bounds(p,q,domain_lower=np.zeros(d),domain_upper=np.ones(d),bins=bins,log_ratio_lipschitz=s.l2_log_ratio_lipschitz_upper,delta=ratio_delta)
    c=np.asarray(calibration_covariates,dtype=float);scores=np.asarray(calibration_scores,dtype=float)
    if c.ndim==1:c=c[:,None]
    if c.shape!=(len(scores),d) or np.any(scores<0) or np.any(~np.isfinite(scores)):raise ValueError('bad calibration data')
    ints=[rb.interval(x) for x in c];lo=np.array([z[0] for z in ints]);hi=np.array([z[1] for z in ints])
    if not np.all(np.isfinite(hi)):return FittedCertifiedShiftCalibrator('abstain',rb,None,s.l2_log_ratio_lipschitz_upper,cov,'insufficient support')
    cal=calibrate_weight_interval_robust(np.zeros((len(scores),1)),scores[:,None],lo,hi,alpha=alpha)
    return FittedCertifiedShiftCalibrator('ready',rb,cal,s.l2_log_ratio_lipschitz_upper,cov,'conditional certificate stack ready')
