"""Joint PV+BESS investment and annual dispatch for provisional El Arenal groups.

PyPSA/Linopy model, NOT a replacement battery heuristic. Capacities on continuous
or discrete equipment sizes, and all 8760 operational hours are co-optimised.
Energy-only transformer P/Q proxy is NOT pandapower AC load-flow verification.
All in kW, kWh, USD, hourly intervals; no kW/MW mixing.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
import pandas as pd

PANEL_KW = 0.435
BATTERY_USABLE_KWH = 17.3 / 4  # HOMER's modelled usable energy, not 5.12 nameplate
ETA_INV = .95
ETA_BAT = math.sqrt(.95)
DISCOUNT = .06
YEARS = 25
IMPORT_USD_KWH = .29
HOMER_EXPORT_REFERENCE_USD_KWH = .275  # scenario ONLY, not a Colombian-approved tariff
# Historical quote subtotal normalized across original HOMER component allocation.
QUOTE_SCALE = 11974.79 / (3856 + 4770 + 3330)
PV_USD_KWP = (3856 / 5.22) * QUOTE_SCALE
BAT_USD_KWH = (4770 / 17.3) * QUOTE_SCALE
INV_USD_KW_AC = (3330 / 5) * QUOTE_SCALE
# Incremental battery-side power electronics cost is unsourced; do not invent one.
BAT_POWER_USD_KW = 0.0
INVERTER_CHOICES_KVA = (0., 5., 6., 7.6, 8., 10., 12., 20., 24.)
# Based on existing Deye inverter family; 20/24 two parallel units still require hardware approval.
INVERTER_BATTERY_PORT_KW = {0.:0.,5.:5.76,6.:6.48,7.6:9.12,8.:9.12,
                             10.:10.56,12.:12.,20.:21.12,24.:24.}

def crf(rate=DISCOUNT, years=YEARS):
    return rate*(1+rate)**years / ((1+rate)**years - 1) if rate else 1/years

def discounted_replacement_factor(lifetime_years, years=YEARS, rate=DISCOUNT):
    value = 1.0
    year = lifetime_years
    while year < years - 1e-9:
        value += (1+rate)**(-year)
        year += lifetime_years
    return value

def annualized_rate(unit_capex, lifetime_years, om_fraction=.02):
    return unit_capex*(crf()*discounted_replacement_factor(lifetime_years) + om_fraction)

@dataclass(frozen=True)
class Settings:
    transformer_kva: float = 5.0
    loading_pu: float = .90
    load_pf: float = .98
    max_panels: int = 64
    fixed_panels: int | None = None  # exact PV count for geometric screening
    fixed_battery_modules: int | None = None  # battery-size sensitivity, separate from PV scan
    max_battery_modules: int = 16
    max_battery_power_kw: float = 24.
    max_inverter_kva: float = 24.
    export_policy: str = 'zero'  # 'zero' or 'reference_credit'; NOT a verified tariff
    objective: str = 'economic'  # 'economic' / 'energy'
    capex_budget_usd: float | None = None
    min_self_sufficiency: float | None = None
    discrete: bool = True
    allow_unserved: bool = False
    allow_synthetic_profile: bool = True
    solver_name: str = 'highs'

    def __post_init__(self):
        if self.transformer_kva <= 0 or not (0 < self.loading_pu <= 1):
            raise ValueError('Invalid assumed transformer nameplate/margin')
        if not 0 < self.load_pf <= 1 or not 0 <= self.max_panels <= 500 or not 0 <= self.max_battery_modules <= 200:
            raise ValueError('Invalid PF or equipment bounds')
        if self.export_policy not in ('zero', 'reference_credit') or self.objective not in ('economic','energy'):
            raise ValueError('Invalid export policy/objective')
        if self.objective == 'energy' and self.capex_budget_usd is None:
            raise ValueError('Energy maximization requires investment budget')
        if self.capex_budget_usd is not None and self.capex_budget_usd < 0:
            raise ValueError('Negative capital budget')
        if self.fixed_panels is not None and (not isinstance(self.fixed_panels,int) or not 0 <= self.fixed_panels <= self.max_panels):
            raise ValueError('fixed_panels must be an integer from zero through max_panels')
        if self.fixed_battery_modules is not None and (not isinstance(self.fixed_battery_modules,int) or not 0 <= self.fixed_battery_modules <= self.max_battery_modules):
            raise ValueError('fixed_battery_modules must be an integer within module capacity')
        if self.min_self_sufficiency is not None and not 0 <= self.min_self_sufficiency <= 1:
            raise ValueError('Self-sufficiency target outside 0..1')

def transformer_active_bound_kw(load_kw, rating_kva, loading_pu, power_factor):
    """Conservative scalar |S| check; no inverter Q compensation and no feeder impedances.

    Reactive power at the PCC is approximated from gross served demand at fixed PF.
    With no ENS this equals requested demand. Negative-export is checked against
    the same envelope. This is a screening constraint, NOT AC network validation.
    """
    d=np.asarray(load_kw,dtype=float)
    if np.any(~np.isfinite(d)) or np.any(d < -1e-9):
        raise ValueError('Invalid load')
    q=np.maximum(d,0)*math.sqrt(1/power_factor**2-1)
    cap=rating_kva*loading_pu
    if np.any(q>cap + 1e-8):
        return np.sqrt(np.maximum(0,cap**2-q**2)), False
    return np.sqrt(np.maximum(0,cap**2-q**2)), True


def make_network(demand_kw:pd.Series, pv_dc_pu:pd.Series, settings: Settings):
    """DC-coupled PV -> inverter -> AC load. DC PV charges battery directly.

    Store and two distinct battery links enable independent battery energy and
    power sizing, distinct from a StorageUnit's fixed max_hours assumption.
    """
    import pypsa  # intentionally imported only when actually solving
    if not demand_kw.index.equals(pv_dc_pu.index):
        raise ValueError('Timestamp mismatch')
    if not isinstance(demand_kw.index,pd.DatetimeIndex) or len(demand_kw)==0:
        raise ValueError('Requires hourly DatetimeIndex')
    if not (np.diff(demand_kw.index.asi8)==3600_000_000_000).all():
        raise ValueError('Requires consecutive hourly snapshots; no snapshot weighting shortcuts')
    if (demand_kw<0).any() or (pv_dc_pu<0).any() or (pv_dc_pu>1.00001).any():
        raise ValueError('Invalid load/PV availability')
    demand_kw=demand_kw.astype(float)
    pv_dc_pu=pv_dc_pu.astype(float).clip(0,1)
    bound,reactive_ok=transformer_active_bound_kw(demand_kw, settings.transformer_kva,
                                                  settings.loading_pu, settings.load_pf)
    if not reactive_ok:
        raise ValueError('Reactive demand alone breaches assumed transformer S limit; no-export/no-ENS LP inappropriate')
    n=pypsa.Network()
    n.set_snapshots(demand_kw.index)
    n.add('Bus','AC');n.add('Bus','SOLAR_DC');n.add('Bus','BATTERY_DC')
    n.add('Load','HOUSEHOLDS',bus='AC',p_set=demand_kw)
    cap=settings.transformer_kva*settings.loading_pu
    n.add('Generator','GRID_IMPORT',bus='AC',p_nom=cap,
          p_max_pu=pd.Series(bound/cap,index=demand_kw.index),marginal_cost=IMPORT_USD_KWH)
    # Generator export is negative injection (power consumption at AC bus);
    # positive marginal cost yields a negative objective contribution for export.
    if settings.export_policy=='reference_credit':
        n.add('Generator','GRID_EXPORT',bus='AC',p_nom=cap,
              p_min_pu=pd.Series(-bound/cap,index=demand_kw.index),
              p_max_pu=0.,marginal_cost=HOMER_EXPORT_REFERENCE_USD_KWH)
    n.add('Generator','PV_DC',bus='SOLAR_DC',p_nom_extendable=True,
          p_nom_max=settings.max_panels*PANEL_KW,capital_cost=annualized_rate(PV_USD_KWP,25),
          p_max_pu=pv_dc_pu,marginal_cost=0.)
    # Link p_nom is input DC power. AC inverter nameplate = ETA_INV * p_nom.
    n.add('Link','PV_INVERTER',bus0='SOLAR_DC',bus1='AC',p_nom_extendable=True,
          p_nom_max=settings.max_inverter_kva/ETA_INV,efficiency=ETA_INV,
          capital_cost=ETA_INV*annualized_rate(INV_USD_KW_AC,15))
    n.add('Store','BATTERY',bus='BATTERY_DC',e_nom_extendable=True,
          e_nom_max=settings.max_battery_modules*BATTERY_USABLE_KWH,
          e_cyclic=True,capital_cost=annualized_rate(BAT_USD_KWH,20))
    n.add('Link','BAT_CHARGE',bus0='SOLAR_DC',bus1='BATTERY_DC',
          p_nom_extendable=True,p_nom_max=settings.max_battery_power_kw,
          efficiency=ETA_BAT,marginal_cost=.00001)
    n.add('Link','BAT_DISCHARGE',bus0='BATTERY_DC',bus1='SOLAR_DC',
          p_nom_extendable=True,p_nom_max=settings.max_battery_power_kw,
          efficiency=ETA_BAT,marginal_cost=.00001,
          capital_cost=annualized_rate(BAT_POWER_USD_KW,20))
    if settings.allow_unserved:
        n.add('Generator','UNSERVED',bus='AC',p_nom=max(1.,demand_kw.max()*2),
              marginal_cost=1000.)
    n.meta={"model":"DC-coupled PV+BESS annual investment/dispatch PyPSA LP/MILP",
            "power_units":"kW, kWh", "cost_units":"USD/year",
            "transformer_screen":"P and fixed assumed Q upper-envelope; NO AC feeder power flow",
            "assumed_trafo_kva":settings.transformer_kva,"loading_pu":settings.loading_pu,
            "export_policy":settings.export_policy,"source":"2025 NASA and fixed-seed stochastic HOMER load"}
    return n


def add_investment_constraints(n, settings:Settings):
    """Couple battery/inverter/DC PV nameplates; optionally enforce integer hardware."""
    m=n.model
    pgen=m.variables['Generator-p_nom'].sel(name='PV_DC')
    inv=m.variables['Link-p_nom'].sel(name='PV_INVERTER')
    ch=m.variables['Link-p_nom'].sel(name='BAT_CHARGE')
    dis=m.variables['Link-p_nom'].sel(name='BAT_DISCHARGE')
    energy=m.variables['Store-e_nom'].sel(name='BATTERY')
    inv_ac=ETA_INV*inv
    if settings.fixed_panels is not None:
        # Fix installed PV, not its upper bound. Otherwise solutions merely plateau
        # beyond the economic optimum and there is no PV-size sensitivity curve.
        m.add_constraints(pgen == PANEL_KW * settings.fixed_panels, name='fixed_exact_panel_count')
    if settings.fixed_battery_modules is not None:
        m.add_constraints(energy == BATTERY_USABLE_KWH * settings.fixed_battery_modules, name='fixed_exact_battery_module_count')
    m.add_constraints(ch == dis,name='one_battery_power_rating')
    m.add_constraints(pgen <= 1.5*inv_ac,name='inverter_max_PV_DC_input_ratio')
    m.add_constraints(dis <= (4.8/BATTERY_USABLE_KWH)*energy,name='battery_bank_current_limit')
    m.add_constraints(dis <= 1.152*inv_ac,name='inverter_battery_port_proxy')
    if settings.discrete:
        num_panels=m.add_variables(lower=0,upper=settings.max_panels,integer=True,
                                   name='PV_panel_count')
        num_batts=m.add_variables(lower=0,upper=settings.max_battery_modules,integer=True,
                                  name='BESS_module_count')
        m.add_constraints(pgen==PANEL_KW*num_panels,name='panel_modules_integer')
        m.add_constraints(energy==BATTERY_USABLE_KWH*num_batts,name='battery_modules_integer')
        choices=[x for x in INVERTER_CHOICES_KVA if x<=settings.max_inverter_kva]
        inv_sel=m.add_variables(binary=True,
               coords=[pd.Index([str(c) for c in choices],name='inverter_variant')],
               name='inverter_selection')
        import xarray as xr
        options=xr.DataArray(choices,coords={'inverter_variant':[str(c) for c in choices]},dims=['inverter_variant'])
        ports=xr.DataArray([INVERTER_BATTERY_PORT_KW[c] for c in choices],
                            coords={'inverter_variant':[str(c) for c in choices]},dims=['inverter_variant'])
        m.add_constraints(inv_sel.sum()==1,name='choose_one_inverter_family')
        m.add_constraints(inv_ac==(inv_sel*options).sum(),name='discrete_inverter_rating')
        m.add_constraints(dis <= (inv_sel*ports).sum(),name='device_port_current_limit')
    # First-cost budget, distinct from 25-year NPC and annual grid bills.
    capex=(pgen*PV_USD_KWP + energy*BAT_USD_KWH + inv_ac*INV_USD_KW_AC
           + dis*BAT_POWER_USD_KW)
    if settings.capex_budget_usd is not None:
        m.add_constraints(capex <= settings.capex_budget_usd,name='investment_budget_USD')
    imported=m.variables['Generator-p'].sel(name='GRID_IMPORT')
    if settings.min_self_sufficiency is not None:
        demand=float(n.loads_t.p_set['HOUSEHOLDS'].sum())
        m.add_constraints(imported.sum() <= demand*(1-settings.min_self_sufficiency),
                          name='min_local_supply_target_no_ENS')
    if settings.objective=='energy':
        # Minimize annual imports at a fixed capex budget; small capital tie-breaker
        # avoids arbitrary oversized hardware among equivalently self-sufficient designs.
        m.add_objective(imported.sum() + 1.e-7*capex,overwrite=True)
    return n


def solve(demand_kw,pv_dc_pu,settings:Settings):
    n=make_network(demand_kw,pv_dc_pu,settings)
    n.optimize.create_model()
    add_investment_constraints(n,settings)
    status,condition=n.optimize.solve_model(solver_name=settings.solver_name)
    if status != 'ok' or condition != 'optimal':
        raise RuntimeError(f'PyPSA solve was {status}/{condition}; no feasible optimum claimed')
    return n


def extract(n, settings:Settings, demand_kw, ghi_wh_m2=None):
    """Solution -> one single hourly trajectory; no new dispatch algorithm."""
    idx=n.snapshots
    t=pd.DataFrame(index=idx);t.index.name='timestamp_lst'
    t['demand_kw']=np.asarray(demand_kw,float)
    t['pv_dc_generated_kw']=n.generators_t.p['PV_DC'].to_numpy(float)
    t['pv_dc_available_kw']=(float(n.generators.at['PV_DC','p_nom_opt'])*
                               n.generators_t.p_max_pu['PV_DC'].to_numpy(float))
    t['battery_charge_dc_kw']=n.links_t.p0['BAT_CHARGE'].to_numpy(float)
    t['battery_discharge_dc_kw']=(-n.links_t.p1['BAT_DISCHARGE']).to_numpy(float)
    t['inverter_ac_kw']=(-n.links_t.p1['PV_INVERTER']).to_numpy(float)
    t['battery_soc_usable_kwh']=n.stores_t.e['BATTERY'].to_numpy(float)
    t['grid_import_kw']=n.generators_t.p['GRID_IMPORT'].to_numpy(float)
    t['grid_export_kw']=(-n.generators_t.p['GRID_EXPORT'].to_numpy(float)
                         if 'GRID_EXPORT' in n.generators.index else 0.)
    t['unserved_kw']=(n.generators_t.p['UNSERVED'].to_numpy(float)
                       if 'UNSERVED' in n.generators.index else 0.)
    t['curtailed_pv_dc_kw']=(t['pv_dc_available_kw']-t['pv_dc_generated_kw']).clip(lower=0)
    if ghi_wh_m2 is not None:
        t['ghi_wh_m2']=np.asarray(ghi_wh_m2,float)
    q=t.demand_kw*math.sqrt(1/settings.load_pf**2-1)
    t['pcc_q_kvar_proxy']=q
    t['pcc_p_kw']=t.grid_import_kw-t.grid_export_kw
    t['pcc_kva_proxy']=np.hypot(t.pcc_p_kw,t.pcc_q_kvar_proxy)
    # Device/model energy closure tests; this is not physical feeder validation.
    r=t.inverter_ac_kw+t.grid_import_kw+t.unserved_kw-t.grid_export_kw-t.demand_kw
    if r.abs().max()>5e-4:
        raise AssertionError('Energy balance residual '+str(float(r.abs().max())))
    if (t.pcc_kva_proxy>settings.transformer_kva*settings.loading_pu+1e-3).any():
        raise AssertionError('Transformer screening envelope exceeded')
    return t


def summarize(n, hourly, settings, case):
    pv=float(n.generators.at['PV_DC','p_nom_opt'])
    energy=float(n.stores.at['BATTERY','e_nom_opt'])
    inverter=ETA_INV*float(n.links.at['PV_INVERTER','p_nom_opt'])
    battery_power=float(n.links.at['BAT_DISCHARGE','p_nom_opt'])
    demand=float(hourly.demand_kw.sum());imports=float(hourly.grid_import_kw.sum())
    exports=float(hourly.grid_export_kw.sum());ens=float(hourly.unserved_kw.sum())
    capex=pv*PV_USD_KWP+energy*BAT_USD_KWH+inverter*INV_USD_KW_AC
    equipment_annual=(pv*annualized_rate(PV_USD_KWP,25)+
                      energy*annualized_rate(BAT_USD_KWH,20)+
                      inverter*annualized_rate(INV_USD_KW_AC,15))
    grid_annual=imports*IMPORT_USD_KWH
    credit=exports*HOMER_EXPORT_REFERENCE_USD_KWH if settings.export_policy=='reference_credit' else 0
    annual=equipment_annual+grid_annual-credit
    return dict(case=case, objective=settings.objective, export_policy=settings.export_policy,
       status='OPTIMAL_ENERGY_ONLY_NO_AC_VALIDATION',
       transformer_assumed_kva=settings.transformer_kva,
       transformer_loading_screen_pu=settings.loading_pu,
       households=case, panels_equivalent=pv/PANEL_KW,pv_kwp=pv,
       battery_modules_equivalent=energy/BATTERY_USABLE_KWH,
       battery_usable_kwh=energy,battery_power_dc_kw=battery_power,
       inverter_ac_kva_assumed_unity_pf=inverter,
       demand_kwh=demand,grid_import_kwh=imports,grid_export_kwh=exports,
       unserved_kwh=ens, self_sufficiency_of_demand_pct=100*(demand-imports-ens)/demand,
       max_pcc_kva_proxy=float(hourly.pcc_kva_proxy.max()),
       capex_usd_ex_vat=capex,annual_equipment_usd=equipment_annual,
       annual_grid_import_usd=grid_annual,annual_export_credit_usd=credit,
       annual_total_usd=annual,total_25yr_NPC_usd=annual/crf(),
       battery_float_replacement_assumed_year=20,
       pandapower_status='NOT_RUN')
