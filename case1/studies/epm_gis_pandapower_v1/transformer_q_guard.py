"""Transformer-aware limitation of settled inverter reactive-power commands.

The function retains the sign and the 0..|Q_requested| range of the chosen
inverter control. It NEVER changes P, demand, nominal transformer rating,
or the network. When the chosen control direction cannot satisfy loading,
it reports that explicitly rather than falsely claiming compliance.

Actual loading must be supplied by a converged pandapower AC evaluation;
no approximation from |P| or |Q| is used to enforce the constraint.
"""
from dataclasses import dataclass
import math
from typing import Callable

@dataclass(frozen=True)
class GuardResult:
    q_kvar: float
    pre_loading_pct: float
    post_loading_pct: float
    unity_loading_pct: float
    minimum_sampled_loading_pct: float
    can_enforce: bool
    status: str
    evaluations: int


def enforce_transformer_limit(
    q_requested_kvar: float,
    evaluate_loading_pct: Callable[[float], float],
    max_loading_pct: float = 100.0,
    sample_points: int = 33,
    refinement_steps: int = 24,
    loading_tolerance_pct: float = 1e-5,
) -> GuardResult:
    """Return closest thermally feasible Q on [0, Q_requested].

    Sampling handles non-monotone loading vs Q. A boundary refinement
    follows the highest feasible point towards the requested command.
    No feasibility beyond the chosen control's sign/range is claimed.
    The callback is allowed to solve a full AC power flow each time.
    """
    if not math.isfinite(q_requested_kvar):
        raise ValueError('Non-finite reactive request')
    if not 0 < max_loading_pct <= 200 or sample_points < 5 or refinement_steps < 0:
        raise ValueError('Invalid transformer guard settings')
    cache: dict[float, float] = {}

    def evaluate(q: float) -> float:
        key = round(float(q), 12)
        if key not in cache:
            loading = float(evaluate_loading_pct(q))
            if not math.isfinite(loading) or loading < 0:
                raise ValueError('Invalid AC transformer loading result')
            cache[key] = loading
        return cache[key]

    requested = float(q_requested_kvar)
    pre = evaluate(requested)
    zero = evaluate(0.) if requested else pre
    feasible = lambda value: value <= max_loading_pct + loading_tolerance_pct
    if feasible(pre):
        return GuardResult(requested,pre,pre,zero,min(pre,zero),True,
                           'REQUEST_ACCEPTED',len(cache))
    if abs(requested) < 1e-9:
        return GuardResult(0.,pre,pre,zero,pre,False,
                           'NO_REACTIVE_ACTION_AND_OVERLOAD',len(cache))

    samples = [(i/(sample_points-1), evaluate(requested*i/(sample_points-1)))
               for i in range(sample_points)]
    feasible_samples = [(t,v) for t,v in samples if feasible(v)]
    if not feasible_samples:
        # Report remaining physical overload, rather than claiming a fix.
        best_t,best_v = min(samples,key=lambda z:z[1])
        return GuardResult(requested*best_t,pre,best_v,zero,best_v,False,
                           'NO_FEASIBLE_Q_ON_CONTROL_RAY',len(cache))

    best_t,best_v = max(feasible_samples,key=lambda z:z[0])
    # Next larger sampled Q is infeasible since requested Q was infeasible.
    next_t = min((t for t,v in samples if t>best_t),default=1.)
    low,high = best_t,next_t
    for _ in range(refinement_steps):
        if (high-low)*abs(requested) < 1e-4:
            break
        mid=(low+high)/2.
        measured=evaluate(requested*mid)
        if feasible(measured):
            low=mid;best_t=mid;best_v=measured
        else:
            high=mid
    return GuardResult(requested*best_t,pre,best_v,zero,
                       min(v for _,v in samples),True,
                       'Q_REDUCED_TO_HOLD_TRAFO_LIMIT',len(cache))
