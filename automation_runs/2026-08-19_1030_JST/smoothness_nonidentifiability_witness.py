from __future__ import annotations
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class BumpWitness:
    sample_points: np.ndarray
    positive_interval: tuple[float,float]
    negative_interval: tuple[float,float]
    amplitude: float

    @staticmethod
    def _triangle(x, interval):
        a,b=interval;m=(a+b)/2.;w=b-a
        return np.maximum(0.,1.-2.*np.abs(np.asarray(x)-m)/w)

    def ratio(self,x):
        x=np.asarray(x,dtype=float)
        hp=self._triangle(x,self.positive_interval);hm=self._triangle(x,self.negative_interval)
        return 1.+self.amplitude*(hp-hm)

    def single_draw_total_variation(self):
        w=self.positive_interval[1]-self.positive_interval[0]
        return 0.5*self.amplitude*w

    def n_sample_total_variation_upper_bound(self,n:int):
        if n<1: raise ValueError('n must be positive')
        return min(1.0,n*self.single_draw_total_variation())

    def max_log_slope_lower_bound(self):
        w=self.positive_interval[1]-self.positive_interval[0]
        return 2.*self.amplitude/(w*(1.+self.amplitude))


def construct_bump_witness(sample_points, *, width_fraction=.08, amplitude=.5):
    s=np.sort(np.unique(np.asarray(sample_points,dtype=float)))
    if s.ndim!=1 or np.any(~np.isfinite(s)) or np.any(s<0) or np.any(s>1):raise ValueError('sample points must be finite in [0,1]')
    if not 0<width_fraction<.2 or not 0<amplitude<1:raise ValueError('bad controls')
    boundaries=np.r_[0.,s,1.]
    gaps=np.diff(boundaries);i=int(np.argmax(gaps));left,right=boundaries[i],boundaries[i+1];g=right-left
    if g<=0:raise ValueError('no open gap')
    w=g*width_fraction
    c1=left+.30*g;c2=left+.70*g
    p=(c1-w/2,c1+w/2);n=(c2-w/2,c2+w/2)
    return BumpWitness(s,p,n,float(amplitude))
