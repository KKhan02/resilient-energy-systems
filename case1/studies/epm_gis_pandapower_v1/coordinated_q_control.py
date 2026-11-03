"""AC-feedback coordination of local HIL Volt-Var and feeder operational limits.

This is an hourly steady-state Q-only feasibility/search layer. It never edits
load P, inverter P, network assets or energy state. All electrical results must
come from converged pandapower solves. Feasibility is conditional on the assumed
balanced EPM GIS network and selected screening limits.
"""
from dataclasses import dataclass
import math
from typing import Callable, Any


@dataclass(frozen=True)
class ACLimits:
    min_v: float = .97
    max_v: float = 1.03
    max_trafo_pct: float = 100.
    max_line_pct: float = 100.
    def __post_init__(self):
        if not (0 < self.min_v < 1 < self.max_v) or self.max_trafo_pct <= 0 or self.max_line_pct <= 0:
            raise ValueError('Invalid AC operating limits')


@dataclass(frozen=True)
class ACPoint:
    q_kvar: float
    v_min: float
    v_max: float
    trafo_pct: float
    line_pct: float
    loss_kw: float
    pcc_kva: float
    def __post_init__(self):
        for val in (self.q_kvar,self.v_min,self.v_max,self.trafo_pct,self.line_pct,self.loss_kw,self.pcc_kva):
            if not math.isfinite(val):raise ValueError('Non-finite AC solution')
        if self.trafo_pct<0 or self.line_pct<0:raise ValueError('Negative AC loading')


@dataclass(frozen=True)
class Choice:
    point: ACPoint
    feasible: bool
    status: str
    requested_kvar: float
    evaluations: int
    voltage_margin_pu: float
    trafo_margin_pct: float
    score: float


def margin(pt: ACPoint, lim: ACLimits):
    return min(pt.v_min-lim.min_v,lim.max_v-pt.v_max),lim.max_trafo_pct-pt.trafo_pct


def feasible(pt: ACPoint, lim: ACLimits, voltage_tol=1e-6, loading_tol=1e-4):
    return (pt.v_min >= lim.min_v-voltage_tol and pt.v_max <= lim.max_v+voltage_tol
            and pt.trafo_pct <= lim.max_trafo_pct+loading_tol
            and pt.line_pct <= lim.max_line_pct+loading_tol)


def violations(pt: ACPoint, lim: ACLimits):
    """Dimensionless vector with meaningful engineering scales."""
    return (max(0.,lim.min_v-pt.v_min)/.01,
            max(0.,pt.v_max-lim.max_v)/.01,
            max(0.,pt.trafo_pct-lim.max_trafo_pct)/5.,
            max(0.,pt.line_pct-lim.max_line_pct)/5.)


def score(pt: ACPoint, lim: ACLimits, q_request:float, cap:float):
    """Preference among feasible or similarly violating AC points.

    Hard constraints are imposed by sorting feasible before infeasible; this
    scalar is NEVER used to declare an infeasible point feasible.
    """
    scale=max(cap,.01)
    v=violations(pt,lim)
    penalty=100.*sum(x*x for x in v)+15.*max(v)
    tracking=abs(pt.q_kvar-q_request)/scale
    q_effort=abs(pt.q_kvar)/scale
    losses=max(0.,pt.loss_kw)
    return penalty + tracking + .04*q_effort + .002*losses


def choose_q(evaluate:Callable[[float],ACPoint], cap_kvar:float,
             q_request_kvar:float,lim:ACLimits=ACLimits(), grid_points:int=21,
             refine:int=2) -> Choice:
    """Search both signs of Q for a best fully feasible AC point, if one exists.

    Sample full inverter reactive capability, include original Q(U) request,
    Q=0, and locally refine good candidates. Feasibility is evaluated with
    AC power flow, not an approximate linear predictor.
    """
    if not math.isfinite(cap_kvar) or cap_kvar<0 or not math.isfinite(q_request_kvar):
        raise ValueError('Invalid Q capability/request')
    if grid_points<5 or refine<0 or refine>6:raise ValueError('Invalid sampling')
    cap=float(cap_kvar)
    req=max(-cap,min(cap,float(q_request_kvar)))
    samples={}
    def add(q):
        q=max(-cap,min(cap,float(q)))
        key=round(q,11)
        if key not in samples:
            pt=evaluate(q)
            if not isinstance(pt,ACPoint):raise TypeError('AC evaluator must return ACPoint')
            if abs(pt.q_kvar-q)>1e-6:raise ValueError('AC evaluator returned different Q')
            samples[key]=pt
    if cap<1e-9:
        add(0.)
    else:
        for i in range(grid_points):add(-cap+2*cap*i/(grid_points-1))
        add(0.);add(req)
        step=2*cap/(grid_points-1)
        # Refine around several strong candidates on both feasible and infeasible frontiers.
        for _ in range(refine):
            ranked=sorted(samples.values(),key=lambda p:(not feasible(p,lim),score(p,lim,req,cap)))
            for pt in ranked[:min(5,len(ranked))]:
                add(pt.q_kvar-step/2.);add(pt.q_kvar+step/2.)
            step/=2.
    # First find a fully feasible point. Only then consider economics/controller tracking.
    values=sorted(samples.values(),key=lambda p:(not feasible(p,lim),score(p,lim,req,cap)))
    winner=values[0]
    ok=feasible(winner,lim)
    v_margin,t_margin=margin(winner,lim)
    status='AC_FEASIBLE_Q' if ok else 'NO_SAMPLED_AC_FEASIBLE_Q_AT_FIXED_P'
    return Choice(winner,ok,status,req,len(samples),v_margin,t_margin,score(winner,lim,req,cap))


def build_ratio_grid(start:float=0.,stop:float=.60,step:float=.10,
                     references=(.25,.48)):
    if not (0<=start<=stop<=1) or not 0<step<=1:raise ValueError('Bad Q ratio grid')
    count=int(math.floor((stop-start)/step+1e-8))
    result={round(start+step*i,8) for i in range(count+1)}
    result.add(round(stop,8))
    for x in references:
        if not 0<=float(x)<=1:raise ValueError('Invalid Q reference')
        if start<=float(x)<=stop:result.add(round(float(x),8))
    return sorted(result)
