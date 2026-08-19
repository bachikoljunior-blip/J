from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class CoverageComposition:
    conditional_miscoverage: float
    certificate_failure_probabilities: tuple[float,...]
    conservative_unconditional_coverage_lower: float
    method: str


def compose_conditional_coverage(alpha:float,*certificate_failure_probabilities:float)->CoverageComposition:
    a=float(alpha);ds=tuple(float(x) for x in certificate_failure_probabilities)
    if not 0<=a<=1 or any((not math.isfinite(x) or x<0 or x>1) for x in ds):raise ValueError('probabilities must lie in [0,1]')
    lower=max(0.0,1.0-a-sum(ds))
    return CoverageComposition(a,ds,lower,'union bound; no independence assumed')
