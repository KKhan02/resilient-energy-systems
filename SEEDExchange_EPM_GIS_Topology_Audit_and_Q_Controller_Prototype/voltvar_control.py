"""Optional PV+BESS inverter reactive-power control for conditional pandapower tests.

Conventions: positive q_kvar is reactive injection into the LV bus (pandapower sgen).
The user must supply the installed inverter apparent-power rating. Constraints are
|Q| <= min(Q_fraction*S, sqrt(max(S**2-P**2,0))). P dispatch is unchanged.
Voltage breakpoints are illustrative project assumptions, not EPM requirements.
"""
import math


def q_cap_kvar(p_kw, s_kva, q_fraction=0.48):
    if s_kva < 0 or p_kw < -1e-9 or not 0 <= q_fraction <= 1:
        raise ValueError('Invalid inverter powers or q_fraction')
    if p_kw > s_kva + 1e-7:
        raise ValueError(f'Active power {p_kw:g} kW exceeds inverter rating {s_kva:g} kVA')
    return min(q_fraction * s_kva, math.sqrt(max(0.0, s_kva*s_kva-p_kw*p_kw)))


def q_target_kvar(v_pu, p_kw, s_kva, mode='unity', fixed_pf=.98,
                  fixed_direction='inject', q_fraction=.48,
                  u1=.96, u2=.99, u3=1.01, u4=1.04):
    """Compute Q command in kVAr from measured local voltage, subject to S limit."""
    if not 0 < fixed_pf <= 1 or fixed_direction not in ('inject','absorb'):
        raise ValueError('Invalid fixed inverter PF or Q direction')
    if not u1 < u2 <= u3 < u4:
        raise ValueError('Volt-Var breakpoints must increase')
    cap=q_cap_kvar(p_kw,s_kva,q_fraction)
    if mode=='unity' or cap==0: return 0.
    if mode=='fixed_pf':
        q=abs(p_kw)*math.tan(math.acos(fixed_pf))
        return min(q,cap)*(1 if fixed_direction=='inject' else -1)
    if mode!='volt_var':raise ValueError('Unknown Q-control mode: '+str(mode))
    if v_pu <= u1:return cap
    if v_pu < u2:return cap*(u2-v_pu)/(u2-u1)
    if v_pu <= u3:return 0.
    if v_pu < u4:return -cap*(v_pu-u3)/(u4-u3)
    return -cap


def solve_inverter_q(network, inverter_index, inverter_bus, p_kw, s_kva,
                     mode='unity', fixed_pf=.98, fixed_direction='inject',
                     q_fraction=.48, root_factor=3., max_iterations=25,
                     damping=.5, tolerance_kvar=.005):
    """Iteratively adjust sgen Q using solved local bus voltage. Requires pandapower.

    Returns info. Raises if not converged, with no false voltage-control success.
    Model's one-phase-to-balanced x3 ROOT_FACTOR applies to both P and Q.
    Only AC power flow changes; active dispatch and equipment sizes remain fixed.
    """
    import pandapower as pp
    if not 0 < damping <= 1 or max_iterations < 1 or root_factor <= 0:
        raise ValueError('Invalid solver controls')
    # Reset to avoid previous-hour Q leaking into the next AC case.
    network.sgen.at[inverter_index,'q_mvar']=0.
    q=0.
    converged=False
    steps=0
    for steps in range(1,max_iterations+1):
        pp.runpp(network,algorithm='bfsw',init='flat',calculate_voltage_angles=False,
                 max_iteration=75,tolerance_mva=1e-8)
        v=float(network.res_bus.at[inverter_bus,'vm_pu'])
        target=q_target_kvar(v,p_kw,s_kva,mode=mode,fixed_pf=fixed_pf,
                            fixed_direction=fixed_direction,q_fraction=q_fraction)
        update=q+damping*(target-q)
        if abs(update-q) <= tolerance_kvar:
            q=update
            network.sgen.at[inverter_index,'q_mvar']=q*root_factor/1000.
            pp.runpp(network,algorithm='bfsw',init='flat',calculate_voltage_angles=False,
                     max_iteration=75,tolerance_mva=1e-8)
            converged=True
            break
        q=update
        network.sgen.at[inverter_index,'q_mvar']=q*root_factor/1000.
    if not converged:raise RuntimeError(f'Inverter Q controller not settled in {max_iterations} iterations')
    return dict(q_kvar=q,v_inverter_pu=float(network.res_bus.at[inverter_bus,'vm_pu']),
                iterations=steps,q_cap_kvar=q_cap_kvar(p_kw,s_kva,q_fraction),
                s_kva_rating=s_kva,control=mode)
