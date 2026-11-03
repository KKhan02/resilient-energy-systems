"""Reuse of the user's HIL Q(U) rule, adapted to a static, combined PV/BESS inverter.

positive Q = injection (pandapower sgen sign).  Q_RATIO multiplies the
installed AC active-power rating P_inst, NOT instantaneous P and NOT S by default.
Reactive capability circle is an additional, independent constraint.
Dynamics are available separately; hourly AC solves use steady-state targets.
"""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class HILParams:
    u1: float=.96
    u2: float=.99
    u3: float=1.01
    u4: float=1.04
    q_ratio: float=.48
    t95_s: float=10.
    def __post_init__(self):
        if not self.u1<self.u2<=self.u3<self.u4: raise ValueError('invalid U thresholds')
        if not 0<=self.q_ratio<=1 or self.t95_s<=0:raise ValueError('invalid Q ratio/T95')

def capability_kvar(p_kw,s_kva,p_inst_kw,params=HILParams()):
    """HIL Qmax=ratio*P_inst, with inverter sqrt(S^2-P^2) cap."""
    if s_kva<0 or p_inst_kw<0 or abs(p_kw)>s_kva+1e-9:raise ValueError('invalid inverter P/S rating')
    return min(params.q_ratio*p_inst_kw,math.sqrt(max(0.,s_kva*s_kva-p_kw*p_kw)))

def q_command(v_pu,p_kw,s_kva,p_inst_kw,mode='volt_var',inverter_pf=.98,
              fixed_direction='inject',params=HILParams()):
    cap=capability_kvar(p_kw,s_kva,p_inst_kw,params)
    if mode=='unity':return 0.
    if mode=='fixed_pf':
        if not 0<inverter_pf<=1 or fixed_direction not in ('inject','absorb'):
            raise ValueError('Invalid fixed-PF settings')
        q=abs(p_kw)*math.tan(math.acos(inverter_pf))
        return min(q,cap)*(1 if fixed_direction=='inject' else -1)
    if mode!='volt_var': raise ValueError('unknown control '+mode)
    if v_pu<=params.u1: return cap
    if v_pu<params.u2:return cap*(params.u2-v_pu)/(params.u2-params.u1)
    if v_pu<=params.u3:return 0.
    if v_pu<params.u4:return -cap*(v_pu-params.u3)/(params.u4-params.u3)
    return -cap

def pt1_step(q_old,q_target,dt_s,params=HILParams()):
    """Exact PT1 step from HIL, tau=T95/3 (95% approximately in T95)."""
    if dt_s<0:raise ValueError('negative timestep')
    alpha=1.-math.exp(-3.*dt_s/params.t95_s)
    return q_old+alpha*(q_target-q_old)

def solve_q(net,inv,bus,p_kw,s_kva,p_inst_kw,mode,params,root_factor=3.,
            inverter_pf=.98,fixed_direction='inject',max_iterations=50,
            damping=.35,tolerance_kvar=.003):
    """Fixed-point local Q(U) control. Returns solved Q, voltage and iterations.

    Rejects nonconvergent feedback; does not silently claim AC validity.
    """
    import pandapower as pp
    if not 0<damping<=1:raise ValueError('invalid damping')
    q=0.
    net.sgen.at[inv,'q_mvar']=0.
    for i in range(max_iterations):
        pp.runpp(net,algorithm='bfsw',init='flat',calculate_voltage_angles=False,
                 max_iteration=75,tolerance_mva=1e-8)
        v=float(net.res_bus.at[bus,'vm_pu'])
        target=q_command(v,p_kw,s_kva,p_inst_kw,mode,inverter_pf,fixed_direction,params)
        nxt=q+damping*(target-q)
        q=nxt
        net.sgen.at[inv,'q_mvar']=q*root_factor/1000.
        if abs(target-q)<=tolerance_kvar:
            pp.runpp(net,algorithm='bfsw',init='flat',calculate_voltage_angles=False,
                     max_iteration=75,tolerance_mva=1e-8)
            return q,float(net.res_bus.at[bus,'vm_pu']),i+1
    raise RuntimeError(f'Volt-Var solver failed to settle after {max_iterations} iterations')
