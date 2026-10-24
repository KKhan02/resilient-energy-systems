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

COLS=['pv_direct_ac','pv_charge_dc','battery_discharge_dc','grid_import','grid_export','curtailed_dc','soc_usable_kwh','load_served','ens','pcc_kva','pcc_p_kw','pcc_q_kvar','deferred_backlog_kwh','reserve_soc','critical_ens']

@njit(cache=True)
def _core(load,pv,grid_on,reserve_soc,modules,inv_kva,bat_dc_power,trafo_allow_kva,pf,flex_frac,import_trigger,initial_stored):
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
        due=age>=8 or (t%24)==23
        # Deferral is permitted only for a scenario-defined fraction of demand.
        # Account for overdue backlog explicitly; no energy disappears.
        if flex_frac>0:
            projected=max(0.,firm+new_flexible-backlog*.0-min(sun*ETA_INV,inv_kva)-min(max(e-reserv,0)*ETA_BAT*ETA_INV,bat_dc_power*ETA_INV))
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
             policy='conventional',grid_on=None,initial_soc_pu=.55,charge_discharge_kw=5.,
             flex_fraction=.15,reserve_override=None):
    if not load.index.equals(pv_dc.index):raise ValueError('time index mismatch')
    if inverter_kva not in INVERTERS:raise ValueError('unknown inverter')
    if not .1<=initial_soc_pu<=1:raise ValueError('bad initial SOC')
    if not 0<pf<=1:raise ValueError('bad PF')
    if modules<0:raise ValueError('bad modules')
    on=np.ones(len(load),dtype=np.bool_) if grid_on is None else np.asarray(grid_on,dtype=np.bool_)
    batlimit=min(charge_discharge_kw,48*INVERTERS[inverter_kva][1]/1000,4.8*modules)
    pvfull=pd.Series(np.asarray(pv_dc),index=pv_dc.index)
    reserve=get_reserve(pvfull,policy) if reserve_override is None else np.asarray(reserve_override,dtype=float)
    if len(reserve)!=len(load):raise ValueError("reserve_override length mismatch")
    emax=modules*USABLE_KWH_MODULE
    e0=emax*(initial_soc_pu-.10)/.9
    flex=flex_fraction if policy=='adaptive_lm' else 0.
    arr=_core(np.asarray(load,dtype=float),np.asarray(pv_dc,dtype=float),on,reserve,modules,
              inverter_kva,batlimit,5*cap_pu,pf,flex,.8*5*cap_pu*.95,e0)
    return pd.DataFrame(arr,index=load.index,columns=COLS)


def score(frame,load,pv,modules,panels,inv,houses,cap_pu,pf):
    """Energy+cost metrics; total cost includes purchased energy, not CAPEX alone."""
    available=float(pv.sum());imports=float(frame.grid_import.sum());exports=float(frame.grid_export.sum())
    ens=float(frame.ens.sum());served=float(frame.load_served.sum())
    pv_cap=PV_UNIT_COST*panels;bat_cap=BAT_UNIT_COST*modules;inv_cap=INV_UNIT_COST*inv
    capex=pv_cap+bat_cap+inv_cap
    # 15y inverter & battery replacements (provisional; throughput aging varies).
    replacement_npv=(inv_cap+bat_cap)/(1+DISCOUNT)**15 if modules else inv_cap/(1+DISCOUNT)**15
    annual_equipment=(capex+replacement_npv)*CRF
    return dict(households=houses,panels=panels,pv_kwp=panels*PANEL_KWP,bess_modules=modules,
                bess_usable_kwh=USABLE_KWH_MODULE*modules,inverter_kva=inv,load_pf=pf,
                transformer_allow_kva=5*cap_pu,demand_kwh=float(load.sum()),served_kwh=served,
                grid_ens_kwh=ens,grid_import_kwh=imports,grid_export_kwh=exports,
                self_sufficiency_pct=100*(served-imports)/max(served,1e-9),
                pv_curtailment_pct=100*float(frame.curtailed_dc.sum())/max(available,1e-9),
                annualized_equipment_usd=annual_equipment,
                annual_total_no_credit_usd=annual_equipment+PRICE_IMPORT*imports,
                annual_total_homer_credit_usd=annual_equipment+PRICE_IMPORT*imports-PRICE_EXPORT*exports,
                annual_total_no_credit_per_house_usd=(annual_equipment+PRICE_IMPORT*imports)/houses,
                max_trafo_kva=float(frame.pcc_kva.max()),
                hours_99pct_allow=int((frame.pcc_kva>=5*cap_pu*.99).sum()),
                charge_dc_kwh=float(frame.pv_charge_dc.sum()),
                discharge_dc_kwh=float(frame.battery_discharge_dc.sum()),
                capex_ex_vat_usd=capex,capex_incl_19pct_vat_usd=capex*(QUOTE_TOTAL_USD/QUOTE_SUBTOTAL_USD),
                available_pv_dc_kwh=available,scenario_status='PCC_ONLY_NOT_SPLIT_PHASE_VERIFIED')
