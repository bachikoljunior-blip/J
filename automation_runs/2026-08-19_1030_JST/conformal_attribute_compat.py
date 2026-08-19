from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Mapping
import math
import numpy as np


def _paired_arrays(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    if y.ndim == 1:
        y = y[:, None]
    if x.ndim != 2 or y.ndim != 2 or x.shape != y.shape or len(x) == 0:
        raise ValueError("calibration pairs must be nonempty arrays with the same 2-D shape")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("calibration attributes must be finite")
    return x, y


def linf_pair_scores(x, y) -> np.ndarray:
    x, y = _paired_arrays(x, y)
    return np.max(np.abs(x - y), axis=1)


def _order_index(n: int, alpha: float) -> int:
    if n < 1:
        raise ValueError("n must be positive")
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0,1)")
    return int(math.ceil((n + 1) * (1.0 - alpha)))


def _threshold_from_scores(scores: np.ndarray, alpha: float, extra_low_rank: int = 0):
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 1 or len(scores) == 0 or not np.all(np.isfinite(scores)):
        raise ValueError("scores must be a nonempty finite vector")
    if extra_low_rank < 0:
        raise ValueError("extra_low_rank must be nonnegative")
    k0 = _order_index(len(scores) - extra_low_rank, alpha) if extra_low_rank else _order_index(len(scores), alpha)
    k = k0 + extra_low_rank
    if k > len(scores):
        return math.inf, k
    return float(np.partition(scores, k - 1)[k - 1]), k


@dataclass(frozen=True)
class SplitConformalLInfCalibration:
    alpha: float
    threshold: float
    calibration_size: int
    order_index: int
    guaranteed_marginal_coverage: float
    assumptions: str

    def compatible(self, x, y) -> bool:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        return bool(np.max(np.abs(x - y)) <= self.threshold + 1e-15)

    def compatibility_matrix(self, x, y) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if x.ndim == 1:
            x = x[:, None]
        if y.ndim == 1:
            y = y[:, None]
        if x.ndim != 2 or y.ndim != 2 or x.shape[1] != y.shape[1]:
            raise ValueError("attribute matrices need a shared feature dimension")
        d = np.max(np.abs(x[:, None, :] - y[None, :, :]), axis=2)
        return d <= self.threshold + 1e-15


def calibrate_linf_split_conformal(cal_x, cal_y, *, alpha: float = 0.1) -> SplitConformalLInfCalibration:
    scores = linf_pair_scores(cal_x, cal_y)
    k = _order_index(len(scores), alpha)
    if k > len(scores):
        threshold = math.inf
        coverage = 1.0
    else:
        threshold = float(np.partition(scores, k - 1)[k - 1])
        coverage = k / (len(scores) + 1)
    return SplitConformalLInfCalibration(
        alpha=float(alpha),
        threshold=threshold,
        calibration_size=len(scores),
        order_index=k,
        guaranteed_marginal_coverage=float(coverage),
        assumptions=(
            "calibration matched pairs and the next true matched pair are exchangeable; "
            "the L-infinity score is fixed before calibration"
        ),
    )


def infer_with_calibrated_tolerance(infer_fn, graph_a, graph_b, *, cal_x, cal_y, alpha=0.1, **kwargs):
    calibration = calibrate_linf_split_conformal(cal_x, cal_y, alpha=alpha)
    certificate = infer_fn(
        graph_a,
        graph_b,
        attribute_linf_tolerance=calibration.threshold,
        **kwargs,
    )
    return calibration, certificate


@dataclass(frozen=True)
class LogLinearScaleModel:
    coef: np.ndarray
    context_dim: int
    minimum_scale: float

    def scale(self, contexts) -> np.ndarray:
        c = np.asarray(contexts, dtype=float)
        if c.ndim == 1:
            c = c[:, None]
        if c.ndim != 2 or c.shape[1] != self.context_dim:
            raise ValueError("bad context shape")
        design = np.column_stack([np.ones(len(c)), c])
        pred = np.exp(np.clip(design @ self.coef, -20.0, 20.0))
        return np.maximum(pred, self.minimum_scale)


def fit_loglinear_scale(contexts, pair_x, pair_y, *, ridge: float = 1e-3, minimum_scale: float = 1e-6):
    c = np.asarray(contexts, dtype=float)
    if c.ndim == 1:
        c = c[:, None]
    scores = linf_pair_scores(pair_x, pair_y)
    if c.ndim != 2 or len(c) != len(scores) or not np.all(np.isfinite(c)):
        raise ValueError("contexts must align with fit pairs")
    if ridge <= 0 or minimum_scale <= 0:
        raise ValueError("ridge/minimum_scale must be positive")
    design = np.column_stack([np.ones(len(c)), c])
    target = np.log(np.maximum(scores, minimum_scale))
    reg = ridge * np.eye(design.shape[1])
    reg[0, 0] = 0.0
    coef = np.linalg.solve(design.T @ design + reg, design.T @ target)
    return LogLinearScaleModel(coef=coef, context_dim=c.shape[1], minimum_scale=float(minimum_scale))


@dataclass(frozen=True)
class NormalizedConformalCalibration:
    alpha: float
    normalized_threshold: float
    calibration_size: int
    order_index: int
    guaranteed_marginal_coverage: float
    scale_model: LogLinearScaleModel
    assumptions: str

    def tolerance(self, contexts) -> np.ndarray:
        return self.normalized_threshold * self.scale_model.scale(contexts)

    def compatible(self, x, y, context) -> bool:
        score = float(linf_pair_scores(np.asarray(x)[None, ...], np.asarray(y)[None, ...])[0])
        tol = float(self.tolerance(np.asarray(context)[None, ...])[0])
        return score <= tol + 1e-15


def calibrate_normalized_conformal(
    fit_contexts,
    fit_x,
    fit_y,
    cal_contexts,
    cal_x,
    cal_y,
    *,
    alpha: float = 0.1,
    ridge: float = 1e-3,
    minimum_scale: float = 1e-6,
) -> NormalizedConformalCalibration:
    model = fit_loglinear_scale(fit_contexts, fit_x, fit_y, ridge=ridge, minimum_scale=minimum_scale)
    c = np.asarray(cal_contexts, dtype=float)
    if c.ndim == 1:
        c = c[:, None]
    scores = linf_pair_scores(cal_x, cal_y)
    if len(c) != len(scores):
        raise ValueError("calibration contexts must align with calibration pairs")
    normalized = scores / model.scale(c)
    k = _order_index(len(normalized), alpha)
    if k > len(normalized):
        q = math.inf
        coverage = 1.0
    else:
        q = float(np.partition(normalized, k - 1)[k - 1])
        coverage = k / (len(normalized) + 1)
    return NormalizedConformalCalibration(
        alpha=float(alpha), normalized_threshold=q, calibration_size=len(normalized),
        order_index=k, guaranteed_marginal_coverage=float(coverage), scale_model=model,
        assumptions=(
            "the scale model is fitted independently of the calibration/test pairs; "
            "normalized calibration and next true-pair scores are exchangeable"
        ),
    )


@dataclass(frozen=True)
class GroupwiseConformalCalibration:
    alpha: float
    thresholds: Mapping[Hashable, float]
    group_sizes: Mapping[Hashable, int]
    group_coverage_lower_bounds: Mapping[Hashable, float]
    assumptions: str

    def tolerance(self, group: Hashable) -> float:
        return float(self.thresholds.get(group, math.inf))


def calibrate_groupwise_conformal(groups, cal_x, cal_y, *, alpha: float = 0.1) -> GroupwiseConformalCalibration:
    groups = np.asarray(groups, dtype=object)
    scores = linf_pair_scores(cal_x, cal_y)
    if groups.ndim != 1 or len(groups) != len(scores):
        raise ValueError("groups must align with calibration pairs")
    thresholds = {}
    sizes = {}
    coverage = {}
    for g in dict.fromkeys(groups.tolist()):
        s = scores[groups == g]
        k = _order_index(len(s), alpha)
        if k > len(s):
            thresholds[g] = math.inf
            coverage[g] = 1.0
        else:
            thresholds[g] = float(np.partition(s, k - 1)[k - 1])
            coverage[g] = k / (len(s) + 1)
        sizes[g] = int(len(s))
    return GroupwiseConformalCalibration(
        alpha=float(alpha), thresholds=thresholds, group_sizes=sizes,
        group_coverage_lower_bounds=coverage,
        assumptions=(
            "within each declared group, calibration true-pair scores and the next true-pair score are exchangeable; "
            "group labels are known at inference"
        ),
    )


@dataclass(frozen=True)
class ContaminationRobustCalibration:
    alpha: float
    threshold: float
    calibration_size: int
    max_contaminated: int
    order_index: int
    guaranteed_clean_marginal_coverage: float
    assumptions: str


def calibrate_with_bounded_contamination(cal_x, cal_y, *, alpha: float = 0.1, max_contaminated: int = 0) -> ContaminationRobustCalibration:
    scores = linf_pair_scores(cal_x, cal_y)
    n = len(scores)
    c = int(max_contaminated)
    if c < 0 or c >= n:
        raise ValueError("max_contaminated must be in [0,n)")
    clean_min = n - c
    clean_order = _order_index(clean_min, alpha)
    k = c + clean_order
    threshold = math.inf if k > n else float(np.partition(scores, k - 1)[k - 1])
    return ContaminationRobustCalibration(
        alpha=float(alpha), threshold=threshold, calibration_size=n,
        max_contaminated=c, order_index=k, guaranteed_clean_marginal_coverage=1.0 - float(alpha),
        assumptions=(
            "at most max_contaminated calibration pairs are arbitrary corruptions; "
            "the remaining clean calibration scores and the next clean true-pair score are exchangeable"
        ),
    )

@dataclass(frozen=True)
class WeightedCovariateShiftCalibration:
    alpha: float
    sorted_scores: np.ndarray
    sorted_calibration_weights: np.ndarray
    assumptions: str

    def tolerance(self, test_weight: float) -> float:
        wt = float(test_weight)
        if not math.isfinite(wt) or wt < 0:
            raise ValueError("test_weight must be finite and nonnegative")
        w = self.sorted_calibration_weights
        total_cal = float(w.sum())
        if total_cal <= 0 and wt <= 0:
            raise ValueError("all calibration/test weights are zero")
        target = (1.0 - self.alpha) * (total_cal + wt)
        cumulative = np.cumsum(w)
        idx = int(np.searchsorted(cumulative, target, side="left"))
        if idx >= len(self.sorted_scores):
            return math.inf
        return float(self.sorted_scores[idx])


def calibrate_weighted_covariate_shift(cal_x, cal_y, calibration_weights, *, alpha: float = 0.1) -> WeightedCovariateShiftCalibration:
    scores = linf_pair_scores(cal_x, cal_y)
    w = np.asarray(calibration_weights, dtype=float)
    if w.ndim != 1 or len(w) != len(scores) or not np.all(np.isfinite(w)) or np.any(w < 0):
        raise ValueError("calibration_weights must be finite nonnegative and align with calibration pairs")
    if float(w.sum()) <= 0:
        raise ValueError("at least one calibration weight must be positive")
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0,1)")
    order = np.argsort(scores, kind="mergesort")
    return WeightedCovariateShiftCalibration(
        alpha=float(alpha),
        sorted_scores=scores[order].copy(),
        sorted_calibration_weights=w[order].copy(),
        assumptions=(
            "the test covariate law is absolutely continuous with respect to the calibration covariate law; "
            "provided weights are proportional to the exact test/calibration covariate density ratio; "
            "the conditional true-pair score law given covariates is unchanged"
        ),
    )


@dataclass(frozen=True)
class WeightIntervalRobustCalibration:
    alpha: float
    sorted_scores: np.ndarray
    sorted_weight_lower: np.ndarray
    sorted_weight_upper: np.ndarray
    assumptions: str

    def tolerance(self, test_weight_lower: float, test_weight_upper: float) -> float:
        lt, ut = float(test_weight_lower), float(test_weight_upper)
        if not (math.isfinite(lt) and math.isfinite(ut) and 0 <= lt <= ut):
            raise ValueError("bad test weight interval")
        lo = self.sorted_weight_lower
        hi = self.sorted_weight_upper
        prefix_lo = np.cumsum(lo)
        suffix_hi = np.r_[np.cumsum(hi[::-1])[::-1][1:], 0.0]
        target = 1.0 - self.alpha
        for idx in range(len(self.sorted_scores)):
            numerator = float(prefix_lo[idx])
            denominator = numerator + float(suffix_hi[idx]) + ut
            if denominator <= 0:
                continue
            if numerator / denominator + 1e-15 >= target:
                return float(self.sorted_scores[idx])
        return math.inf


def calibrate_weight_interval_robust(cal_x, cal_y, weight_lower, weight_upper, *, alpha: float = 0.1) -> WeightIntervalRobustCalibration:
    scores = linf_pair_scores(cal_x, cal_y)
    lo = np.asarray(weight_lower, dtype=float)
    hi = np.asarray(weight_upper, dtype=float)
    if lo.ndim != 1 or hi.ndim != 1 or len(lo) != len(scores) or len(hi) != len(scores):
        raise ValueError("weight intervals must align with calibration pairs")
    if not np.all(np.isfinite(lo)) or not np.all(np.isfinite(hi)) or np.any(lo < 0) or np.any(hi < lo):
        raise ValueError("invalid weight bounds")
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0,1)")
    order = np.argsort(scores, kind="mergesort")
    return WeightIntervalRobustCalibration(
        alpha=float(alpha), sorted_scores=scores[order].copy(),
        sorted_weight_lower=lo[order].copy(), sorted_weight_upper=hi[order].copy(),
        assumptions=(
            "the true covariate density-ratio weight of every calibration/test point lies in the supplied interval; "
            "the conditional true-pair score law given covariates is unchanged"
        ),
    )

@dataclass(frozen=True)
class CompatibilityValidityDecision:
    status: str
    finite_threshold: bool
    threshold: float
    guarantee: str
    reason: str


def fail_closed_validity_gate(calibration, *, test_context=None, group=None, test_weight=None, test_weight_interval=None) -> CompatibilityValidityDecision:
    if isinstance(calibration, SplitConformalLInfCalibration):
        q = calibration.threshold
        guarantee = f"marginal coverage >= {calibration.guaranteed_marginal_coverage:.6f} under exchangeability"
    elif isinstance(calibration, NormalizedConformalCalibration):
        if test_context is None:
            return CompatibilityValidityDecision('abstain_missing_context', False, math.inf, 'none', 'normalized calibration requires test context')
        q = float(calibration.tolerance(np.asarray(test_context, dtype=float).reshape(1, -1))[0])
        guarantee = f"marginal coverage >= {calibration.guaranteed_marginal_coverage:.6f} for fixed independent scale model"
    elif isinstance(calibration, GroupwiseConformalCalibration):
        if group is None or group not in calibration.thresholds:
            return CompatibilityValidityDecision('abstain_unseen_group', False, math.inf, 'none', 'groupwise guarantee unavailable for this group')
        q = calibration.tolerance(group)
        guarantee = f"group-conditional marginal coverage >= {calibration.group_coverage_lower_bounds[group]:.6f}"
    elif isinstance(calibration, WeightedCovariateShiftCalibration):
        if test_weight is None:
            return CompatibilityValidityDecision('abstain_missing_density_ratio', False, math.inf, 'none', 'weighted covariate-shift calibration requires a test density-ratio weight')
        q = calibration.tolerance(test_weight)
        guarantee = f"marginal coverage >= {1.0-calibration.alpha:.6f} under the stated exact covariate-shift ratio"
    elif isinstance(calibration, WeightIntervalRobustCalibration):
        if test_weight_interval is None:
            return CompatibilityValidityDecision('abstain_missing_weight_bounds', False, math.inf, 'none', 'robust weighted calibration requires certified test-weight bounds')
        q = calibration.tolerance(*test_weight_interval)
        guarantee = f"marginal coverage >= {1.0-calibration.alpha:.6f} for every ratio realization within certified bounds"
    elif isinstance(calibration, ContaminationRobustCalibration):
        q = calibration.threshold
        guarantee = f"clean marginal coverage >= {calibration.guaranteed_clean_marginal_coverage:.6f} under bounded calibration contamination"
    else:
        return CompatibilityValidityDecision('abstain_uncertified_calibrator', False, math.inf, 'none', 'no recognized coverage certificate')
    if not math.isfinite(q):
        return CompatibilityValidityDecision('abstain_uninformative_threshold', False, math.inf, guarantee, 'coverage contract is valid but finite-sample/shift uncertainty forces an infinite threshold')
    return CompatibilityValidityDecision('certified_finite_threshold', True, float(q), guarantee, 'finite threshold released under an explicit coverage contract')

@dataclass(frozen=True)
class GroupDensityRatioIntervals:
    lower: Mapping[Hashable,float]
    upper: Mapping[Hashable,float]
    delta: float
    train_size: int
    test_size: int
    assumptions: str

    def interval(self, group: Hashable):
        return float(self.lower.get(group,0.0)), float(self.upper.get(group,math.inf))


def estimate_group_density_ratio_intervals(train_groups, test_groups, *, delta: float = 0.05) -> GroupDensityRatioIntervals:
    tr=np.asarray(train_groups,dtype=object);te=np.asarray(test_groups,dtype=object)
    if tr.ndim!=1 or te.ndim!=1 or len(tr)==0 or len(te)==0:raise ValueError('nonempty 1-D group samples required')
    if not 0<delta<1:raise ValueError('delta must be in (0,1)')
    groups=list(dict.fromkeys(np.r_[tr,te].tolist()));G=len(groups)
    et=math.sqrt(math.log(4*G/delta)/(2*len(tr)));ee=math.sqrt(math.log(4*G/delta)/(2*len(te)))
    lo={};hi={}
    for g in groups:
        pt=float(np.mean(tr==g));pe=float(np.mean(te==g))
        ptl=max(0.0,pt-et);ptu=min(1.0,pt+et);pel=max(0.0,pe-ee);peu=min(1.0,pe+ee)
        lo[g]=0.0 if ptu<=0 else pel/ptu
        hi[g]=math.inf if ptl<=0 else peu/ptl
    return GroupDensityRatioIntervals(lo,hi,float(delta),len(tr),len(te),
        'train/test unlabeled group samples are i.i.d. from their covariate laws; finite group partition fixed before sampling; simultaneous Hoeffding bounds hold with probability at least 1-delta')


def calibrate_from_group_ratio_intervals(cal_groups, cal_x, cal_y, ratio_intervals: GroupDensityRatioIntervals, *, alpha=.1):
    g=np.asarray(cal_groups,dtype=object);scores=linf_pair_scores(cal_x,cal_y)
    if g.ndim!=1 or len(g)!=len(scores):raise ValueError('calibration groups must align with pairs')
    lo=np.array([ratio_intervals.interval(z)[0] for z in g],dtype=float)
    hi=np.array([ratio_intervals.interval(z)[1] for z in g],dtype=float)
    if not np.all(np.isfinite(hi)):
        raise ValueError('some calibration groups lack finite density-ratio upper bounds')
    return calibrate_weight_interval_robust(cal_x,cal_y,lo,hi,alpha=alpha)
