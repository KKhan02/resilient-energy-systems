"""Fast, causal, DC-coupled, shared PV+BESS screening model.

Purpose: broad candidate screening, NOT a split-phase feeder power-flow or
commissioning approval. Physical checks use transformer PCC P,Q kVA and
nominal DC inverter input ratings only. The independent pandapower port is
included unchanged under legacy/ for validation after shortlisting.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        return lambda func:func

# Single inverter family SUN-5/6/7.6/8/10/12K-SG02LP2-US-AM2/AM3.
# 20 and 24 kVA entries model TWO PARALLEL identical 10 or 12 kVA units.
# Parallel interface, BMS, current sharing, string wiring and EPM approval UNVERIFIED.
# nameplate PV input kWp, battery input current A; string voltage/current NOT checked.
INVERTERS={5.0:(7.5,120),6.0:(9.0,135),7.6:(11.4,190),8.0:(12.0,190),10.0:(15.0,220),12.0:(18.0,250),
           20.0:(30.0,440),24.0:(36.0,500)}
PANEL_KWP=.435
USABLE_KWH_MODULE=17.3/4
ETA_INV=.95
ETA_BAT=math.sqrt(.95)
PROJECT_Y=25
DISCOUNT=.06
# HOMER reference component split sum 11956, scale to quote subtotal 11974.79.
QUOTE_SUBTOTAL_USD=11974.79
QUOTE_TOTAL_USD=14250.00
QUOTE_SCALE=QUOTE_SUBTOTAL_USD/(3856+4770+3330)
PRICE_IMPORT=0.29
PRICE_EXPORT=0.275
PV_UNIT_COST=3856/12 * QUOTE_SCALE
BAT_UNIT_COST=4770/4 * QUOTE_SCALE
INV_UNIT_COST=3330/5 * QUOTE_SCALE
CRF=DISCOUNT*(1+DISCOUNT)**PROJECT_Y/((1+DISCOUNT)**PROJECT_Y-1)
# From the original HOMER XML and preserved independent reference model.
BATTERY_FLOAT_LIFE_Y=20.0
BATTERY_LIFETIME_THROUGHPUT_KWH_PER_MODULE=23660.0
INVERTER_LIFE_Y=15.0


def battery_replacement_life(modules,annual_battery_throughput_kwh):
    """HOMER float/throughput life, using annual 0.5*(charge+discharge)."""
    if modules<=0:
        return float('inf'),'no battery'
    if annual_battery_throughput_kwh<=0:
        return BATTERY_FLOAT_LIFE_Y,'float life (no cycling)'
    throughput_years=(modules*BATTERY_LIFETIME_THROUGHPUT_KWH_PER_MODULE
                      /annual_battery_throughput_kwh)
    if throughput_years<BATTERY_FLOAT_LIFE_Y:
        return throughput_years,'throughput limited'
    return BATTERY_FLOAT_LIFE_Y,'float life limited'


def replacement_npv(component_capex,component_lifetime_years):
    """Discount replacements strictly inside the study horizon (no end replacement)."""
    if component_capex<=0 or component_lifetime_years<=0:
        return 0.
    total=0.
    year=component_lifetime_years
    while year<PROJECT_Y-1e-9:
        total+=component_capex/(1+DISCOUNT)**year
        year+=component_lifetime_years
    return total

COLS=['pv_direct_ac','pv_charge_dc','battery_discharge_dc','grid_import','grid_export','curtailed_dc','soc_usable_kwh','load_served','ens','pcc_kva','pcc_p_kw','pcc_q_kvar','deferred_backlog_kwh','reserve_soc','critical_ens']

@njit(cache=True)
def _core(load,pv,grid_on,reserve_soc,local_hour,modules,inv_kva,bat_dc_power,trafo_allow_kva,pf,flex_frac,import_trigger,initial_stored):
    """1-hour causal dynamics. reserve_soc is already computed from past data only.
    All AC power in kW, PV/BESS in DC kW and energy in kWh.
    If demand cannot be served under 5 kVA constraint, record ENS, not feasibility.
    No grid charging. Surplus PV to battery first, then export within kVA envelope.
    """
    n=len(load); arr=np.zeros((n,15)); emax=modules*USABLE_KWH_MODULE
    e=min(max(initial_stored,0.),emax)
    qfac=math.sqrt(max(0.0,1./(pf*pf)-1.))
    backlog=0.; age=0
    for t in range(n):
        ld=load[t]; sun=pv[t]; on=grid_on[t]
        reserv=max(0.,(reserve_soc[t]-.1)/.9*emax) if on else 0.
        firm=ld*(1-flex_frac); new_flexible=ld*flex_frac
        due=age>=8 or local_hour[t]==23
        # Deferral is permitted only for a scenario-defined fraction of demand.
        # Account for overdue backlog explicitly; no energy disappears.
        if flex_frac>0:
            projected=max(0.,firm+new_flexible+backlog-min(sun*ETA_INV,inv_kva)-min(max(e-reserv,0)*ETA_BAT*ETA_INV,bat_dc_power*ETA_INV))
            if (on and (projected<=import_trigger or due)):
                flexible_now=new_flexible+backlog
            elif (not on and (sun*ETA_INV>firm)):
                flexible_now=min(new_flexible+backlog,max(0.,sun*ETA_INV-firm))
            elif due:
                flexible_now=new_flexible+backlog
            else:
                flexible_now=0.
            backlog=max(0.,backlog+new_flexible-flexible_now)
            if backlog>1e-10:age+=1
            else:age=0
        else:
            flexible_now=0.;backlog=0.
        request=firm+(flexible_now if flex_frac>0 else new_flexible)
        direct=min(sun*ETA_INV,request,inv_kva)
        remaining=max(0.,sun-direct/ETA_INV)
        charge=min(remaining,bat_dc_power,max(0.,(emax-e)/ETA_BAT)) if modules>0 else 0.
        e+=charge*ETA_BAT
        remaining-=charge
        deficit=max(0.,request-direct)
        discharge=min(deficit/ETA_INV,bat_dc_power,max(0.,e-reserv)*ETA_BAT,max(0.,inv_kva-direct)/ETA_INV) if modules>0 else 0.
        e-=discharge/ETA_BAT
        local=direct+discharge*ETA_INV
        # Apply the PCC apparent-power constraint to actually served load.
        # Import is positive only when local generation cannot supply demand.
        imp=max(0.,request-local) if on else 0.
        served=min(request,local+imp)
        if on and math.hypot(imp,served*qfac)>trafo_allow_kva+1e-8:
            if qfac>0. and local*qfac>=trafo_allow_kva:
                # Even with zero import, local generation would serve
                # too much reactive demand for the allowed PCC rating.
                served=min(request,trafo_allow_kva/qfac)
            else:
                # Solve (served-local)^2+(served*qfac)^2=limit^2
                # for the larger (physically admissible) served-load root.
                A=1.+qfac*qfac
                discr=max(0.,(2.*local)**2
                          -4.*A*(local*local-trafo_allow_kva**2))
                served=min(request,(2.*local+math.sqrt(discr))/(2.*A))
            served=max(0.,served)
            imp=max(0.,served-local)

        if local>served:
            # Local inverter output cannot exceed served demand. Back off
            # BESS discharge first, refunding its stored energy; then back
            # off PV direct supply and restore it to the surplus DC pool.
            excess_ac=local-served
            returned_dc=min(discharge,excess_ac/ETA_INV)
            discharge-=returned_dc
            e+=returned_dc/ETA_BAT
            excess_ac-=returned_dc*ETA_INV
            pv_released_ac=min(direct,max(0.,excess_ac))
            direct-=pv_released_ac
            remaining+=pv_released_ac/ETA_INV
            local=direct+discharge*ETA_INV
            imp=max(0.,served-local) if on else 0.

            # Preserve the agreed priority: PV surplus charges BESS before
            # any export or curtailment. Respect the total charge power
            # and the remaining stored-energy headroom.
            extra_charge=min(remaining,max(0.,bat_dc_power-charge),
                             max(0.,(emax-e)/ETA_BAT)) if modules>0 else 0.
            charge+=extra_charge
            e+=extra_charge*ETA_BAT
            remaining-=extra_charge

        # Use final served-load Q, not requested-load Q, for export envelope.
        q=served*qfac if on else 0.
        export_bound=math.sqrt(max(0.,trafo_allow_kva**2-q*q))
        export=min(remaining*ETA_INV,max(0.,inv_kva-local),
                   export_bound) if on else 0.
        curtailed=max(0.,remaining-export/ETA_INV)
        ens=max(0.,request-served)
        # More than 0.3 of load assumed noncritical; critical demand shed last.
        crit=.3*ld
        crit_ens=max(0.,crit-served)
        pcc=imp-export
        s=math.hypot(pcc,served*qfac) if on else 0.
        arr[t,0]=direct;arr[t,1]=charge;arr[t,2]=discharge
        arr[t,3]=imp;arr[t,4]=export;arr[t,5]=curtailed;arr[t,6]=e
        arr[t,7]=served;arr[t,8]=ens;arr[t,9]=s;arr[t,10]=pcc
        arr[t,11]=served*qfac if on else 0.;arr[t,12]=backlog
        arr[t,13]=reserve_soc[t] if on else .10;arr[t,14]=crit_ens
    return arr


def solar_history_index(pv_series:pd.Series,days=3):
    """Previous completed days only, using FULL input series history."""
    daily=pv_series.resample('D').sum()
    avg=daily.shift(1).rolling(days,min_periods=days).mean()
    base=daily.shift(1).expanding(min_periods=days).mean()
    idx=(avg/base).replace([np.inf,-np.inf],np.nan).fillna(1.).clip(0,3)
    return np.asarray(idx.reindex(pv_series.index.normalize()).to_numpy(),dtype=float)


def get_reserve(pv_series,policy='conventional',gain=.60,low=.30,high=.75):
    if policy=='conventional':return np.full(len(pv_series),.10)
    if policy=='fixed_reserve':return np.full(len(pv_series),.50)
    if policy in ('adaptive','adaptive_lm'):
        # USER-DEFINED HEURISTIC, not a published validated formula.
        i=solar_history_index(pv_series,3)
        return np.clip(low+gain*(1-i),low,high)
    raise ValueError(policy)


def dispatch(load:pd.Series,pv_dc:pd.Series,modules:int,inverter_kva:float,cap_pu=.9,pf=.98,
             policy='conventional',grid_on=None,initial_soc_pu=.55,charge_discharge_kw=None,
             flex_fraction=.15,reserve_override=None):
    if not load.index.equals(pv_dc.index):raise ValueError('time index mismatch')
    if inverter_kva not in INVERTERS:raise ValueError('unknown inverter')
    if not .1<=initial_soc_pu<=1:raise ValueError('bad initial SOC')
    if not 0<pf<=1:raise ValueError('bad PF')
    if modules<0:raise ValueError('bad modules')
    # Validate BEFORE get_reserve calls pandas resample('D').
    if policy=='adaptive_lm' and not isinstance(load.index,pd.DatetimeIndex):
        raise ValueError('adaptive_lm requires a DatetimeIndex for local-hour scheduling')
    on=np.ones(len(load),dtype=np.bool_) if grid_on is None else np.asarray(grid_on,dtype=np.bool_)
    # None uses datasheet battery port and module bank capabilities.
    # The annual research sweep explicitly supplies 5.0 kW for comparability.
    if charge_discharge_kw is not None and charge_discharge_kw<0:
        raise ValueError('battery charge/discharge power cannot be negative')
    physical_limit=min(48*INVERTERS[inverter_kva][1]/1000,4.8*modules)
    batlimit=physical_limit if charge_discharge_kw is None else min(charge_discharge_kw,physical_limit)
    pvfull=pd.Series(np.asarray(pv_dc),index=pv_dc.index)
    reserve=get_reserve(pvfull,policy) if reserve_override is None else np.asarray(reserve_override,dtype=float)
    if len(reserve)!=len(load):raise ValueError("reserve_override length mismatch")
    emax=modules*USABLE_KWH_MODULE
    e0=emax*(initial_soc_pu-.10)/.9
    flex=flex_fraction if policy=='adaptive_lm' else 0.
    if flex>0:
        local_hour=np.asarray(load.index.hour,dtype=np.int64)
    else:
        local_hour=np.zeros(len(load),dtype=np.int64)
    arr=_core(np.asarray(load,dtype=float),np.asarray(pv_dc,dtype=float),on,reserve,local_hour,modules,
              inverter_kva,batlimit,5*cap_pu,pf,flex,.8*5*cap_pu*.95,e0)
    return pd.DataFrame(arr,index=load.index,columns=COLS)


def soc_boundary_diagnostics(frame,modules,initial_soc_pu=.55,
                             tolerance_kwh=1e-3):
    """Report beginning/end usable DC energy; never silently erase drift.

    Nominal SOC 10% maps to zero usable energy, 100% to full usable bank.
    The result belongs to the specific simulated window, not the grid itself.
    """
    if frame.empty:
        raise ValueError('SOC boundary requires a nonempty dispatch')
    if modules<0 or not .1<=initial_soc_pu<=1.:
        raise ValueError('invalid battery modules or initial SOC')
    if tolerance_kwh<0:
        raise ValueError('SOC closure tolerance must be nonnegative')
    capacity=modules*USABLE_KWH_MODULE
    initial=capacity*(initial_soc_pu-.1)/.9
    ending=float(frame.soc_usable_kwh.iloc[-1])
    drift=ending-initial
    return dict(initial_soc_pu=float(initial_soc_pu),
                initial_stored_kwh=initial,
                end_stored_kwh=ending,
                soc_boundary_drift_kwh=drift,
                soc_boundary_drift_pct_usable=100*drift/capacity if capacity else 0.,
                soc_boundary_closed=abs(drift)<=tolerance_kwh)


def dispatch_cyclic(load,pv_dc,modules,inverter_kva,*,
                    soc_tolerance_kwh=1e-3,max_iterations=32,
                    **dispatch_kwargs):
    """Opt-in periodic full-day SOC sensitivity; NOT an outage initializer.

    Search for E_end=E_start with exactly the same weather/demand/dispatch
    policy over the repeated study window. No battery energy is fabricated:
    a candidate is accepted only when rerunning dispatch closes the residual.
    The ordinary annual sweep still starts at the documented 55% nominal SOC.
    """
    if 'initial_soc_pu' in dispatch_kwargs:
        raise ValueError('periodic SOC solves initial_soc_pu; do not set it')
    if not isinstance(load.index,pd.DatetimeIndex) or len(load)<24 or len(load)%24:
        raise ValueError('periodic SOC requires complete local days')
    if load.index[0].hour!=0 or load.index[-1].hour!=23 or (
            not np.all(np.diff(load.index.asi8)==3600*10**9)):
        raise ValueError('periodic SOC requires complete local days at hourly resolution')
    if 'grid_on' in dispatch_kwargs and dispatch_kwargs['grid_on'] is not None:
        if not bool(np.all(dispatch_kwargs['grid_on'])):
            raise ValueError('periodic SOC is only for grid-connected baseline windows')
    if soc_tolerance_kwh<=0 or max_iterations<1:
        raise ValueError('positive SOC tolerance and iteration count required')

    def candidate(soc):
        frame=dispatch(load,pv_dc,modules,inverter_kva,
                       initial_soc_pu=soc,**dispatch_kwargs)
        return frame,soc_boundary_diagnostics(frame,modules,soc,soc_tolerance_kwh)

    trial_frame,trial_info=candidate(.55)
    if abs(trial_info['soc_boundary_drift_kwh'])<=soc_tolerance_kwh:
        return trial_frame,dict(trial_info,method='periodic_window_soc',
                                solver_iterations=1)
    if modules==0:
        return trial_frame,dict(trial_info,method='not_applicable_no_battery',
                                solver_iterations=1)

    lo,hi=.1,1.
    frame_lo,diag_lo=candidate(lo)
    if abs(diag_lo['soc_boundary_drift_kwh'])<=soc_tolerance_kwh:
        return frame_lo,dict(diag_lo,method='periodic_window_soc',
                             solver_iterations=2)
    frame_hi,diag_hi=candidate(hi)
    if abs(diag_hi['soc_boundary_drift_kwh'])<=soc_tolerance_kwh:
        return frame_hi,dict(diag_hi,method='periodic_window_soc',
                             solver_iterations=3)
    if diag_lo['soc_boundary_drift_kwh']<0 or diag_hi['soc_boundary_drift_kwh']>0:
        raise RuntimeError('SOC periodic boundary is not bracketed')

    for iteration in range(1,max_iterations+1):
        mid=(lo+hi)/2
        frame,info=candidate(mid)
        drift=info['soc_boundary_drift_kwh']
        if abs(drift)<=soc_tolerance_kwh:
            return frame,dict(info,method='periodic_window_soc',
                              solver_iterations=iteration+3)
        if drift>0:
            lo=mid
        else:
            hi=mid
    raise RuntimeError('SOC periodic boundary did not close within tolerance')


def score(frame,load,pv,modules,panels,inv,houses,cap_pu,pf,initial_soc_pu=.55):
    """Energy+cost metrics; total cost includes purchased energy, not CAPEX alone."""
    available=float(pv.sum());imports=float(frame.grid_import.sum());exports=float(frame.grid_export.sum())
    ens=float(frame.ens.sum());served=float(frame.load_served.sum());demand=float(load.sum())
    pv_cap=PV_UNIT_COST*panels;bat_cap=BAT_UNIT_COST*modules;inv_cap=INV_UNIT_COST*inv
    capex=pv_cap+bat_cap+inv_cap
    # Match preserved independent HOMER convention: annual battery DC
    # throughput = 0.5 * (charge + discharge), no separate wear-cost charge.
    annual_battery_throughput=.5*(
        float(frame.pv_charge_dc.sum())+float(frame.battery_discharge_dc.sum()))
    battery_life,battery_basis=battery_replacement_life(
        modules,annual_battery_throughput)
    battery_rep=replacement_npv(bat_cap,battery_life)
    inverter_rep=replacement_npv(inv_cap,INVERTER_LIFE_Y)
    annual_equipment=(capex+battery_rep+inverter_rep)*CRF
    boundary=soc_boundary_diagnostics(frame,modules,initial_soc_pu)
    return dict(households=houses,panels=panels,pv_kwp=panels*PANEL_KWP,bess_modules=modules,
                bess_usable_kwh=USABLE_KWH_MODULE*modules,inverter_kva=inv,load_pf=pf,
                transformer_allow_kva=5*cap_pu,demand_kwh=float(load.sum()),served_kwh=served,
                grid_ens_kwh=ens,grid_import_kwh=imports,grid_export_kwh=exports,
                # The legacy field is retained for saved-CSV compatibility.
                self_sufficiency_pct=100*(served-imports)/max(served,1e-9),
                self_sufficiency_of_served_pct=100*(served-imports)/max(served,1e-9),
                one_minus_import_fraction_of_demand_pct=100*(1-imports/max(demand,1e-9)),
                locally_supplied_fraction_of_demand_pct=100*(served-imports)/max(demand,1e-9),
                pv_curtailment_pct=100*float(frame.curtailed_dc.sum())/max(available,1e-9),
                annualized_equipment_usd=annual_equipment,
                annual_battery_throughput_kwh=annual_battery_throughput,
                battery_life_years=battery_life if modules else 0.,
                battery_life_basis=battery_basis,
                battery_replacement_npv_usd=battery_rep,
                inverter_replacement_npv_usd=inverter_rep,
                annual_total_no_credit_usd=annual_equipment+PRICE_IMPORT*imports,
                annual_total_homer_credit_usd=annual_equipment+PRICE_IMPORT*imports-PRICE_EXPORT*exports,
                annual_total_no_credit_per_house_usd=(annual_equipment+PRICE_IMPORT*imports)/houses,
                max_trafo_kva=float(frame.pcc_kva.max()),
                hours_99pct_allow=int((frame.pcc_kva>=5*cap_pu*.99).sum()),
                charge_dc_kwh=float(frame.pv_charge_dc.sum()),
                discharge_dc_kwh=float(frame.battery_discharge_dc.sum()),
                capex_ex_vat_usd=capex,capex_incl_19pct_vat_usd=capex*(QUOTE_TOTAL_USD/QUOTE_SUBTOTAL_USD),
                available_pv_dc_kwh=available,
                **boundary,
                scenario_status='PCC_ONLY_NOT_SPLIT_PHASE_VERIFIED')
