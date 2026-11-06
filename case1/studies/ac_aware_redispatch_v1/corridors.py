"""Pure, testable sampling logic for conditional AC-feasible inverter-P bands.

A sampled band is only a hypothesis between sampled feasible points. It MUST be
rechecked with pandapower after dispatch; it is not an AC-feasibility certificate.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Iterable


@dataclass(frozen=True)
class Corridor:
    p_min_kw: float
    p_max_kw: float
    reference_kw: float
    sampled_feasible: int

    def __post_init__(self):
        if not (0 <= self.p_min_kw <= self.p_max_kw):
            raise ValueError('Bad inverter P corridor')
        if not all(math.isfinite(x) for x in (self.p_min_kw,self.p_max_kw,self.reference_kw)):
            raise ValueError('Non-finite corridor')


def grid_points(pmax_kw: float, reference_kw: float, count: int) -> list[float]:
    if not (math.isfinite(pmax_kw) and math.isfinite(reference_kw)):
        raise ValueError('Non-finite P')
    if pmax_kw < 0 or reference_kw < -1e-8 or reference_kw > pmax_kw + 1e-7:
        raise ValueError('P outside 0..Pmax')
    if count < 5:
        raise ValueError('At least 5 initial P points required')
    values=[pmax_kw*j/(count-1) for j in range(count)]
    values.append(max(0.,min(reference_kw,pmax_kw)))
    return sorted({round(v,10) for v in values})


def choose_corridor(samples: Iterable[tuple[float,bool]], reference_kw:float) -> Corridor | None:
    """Select connected feasible sample positions nearest prior P.

    No extrapolation beyond tested points. No interpolation guarantee.
    Any non-feasible sample splits a candidate band.
    """
    points=sorted((float(p),bool(ok)) for p,ok in samples)
    if not points:
        raise ValueError('No AC samples')
    if not math.isfinite(reference_kw) or reference_kw<0:
        raise ValueError('Invalid reference inverter P')
    if len(set(p for p,_ in points))!=len(points):
        raise ValueError('Duplicate P sample')
    if any(not math.isfinite(p) or p < 0 for p,_ in points):
        raise ValueError('Invalid P sample')
    groups=[];run=[]
    for p,ok in points:
        if ok:run.append(p)
        elif run:
            groups.append(run);run=[]
    if run:groups.append(run)
    if not groups:return None
    def key(g):
        lo,hi=g[0],g[-1]
        distance=max(lo-reference_kw,reference_kw-hi,0.)
        return (distance, -(hi-lo),abs((hi+lo)/2-reference_kw))
    picked=min(groups,key=key)
    return Corridor(picked[0],picked[-1],reference_kw,len(picked))


def q_ratio_at_hour(pv_dc_available_kw:float,day_q_ratio:float,night_q_allowed:bool,eps=1e-6)->float:
    """Conservative proxy: disable Q when PV DC availability is effectively zero.

    True night determination requires time/location and manufacturer operating mode.
    """
    if not all(math.isfinite(float(v)) for v in (pv_dc_available_kw,day_q_ratio)):
        raise ValueError('Invalid PV or Q ratio')
    if pv_dc_available_kw < 0 or not 0 <= day_q_ratio <= 1:
        raise ValueError('Invalid PV or Q capability')
    return day_q_ratio if (night_q_allowed or pv_dc_available_kw > eps) else 0.
