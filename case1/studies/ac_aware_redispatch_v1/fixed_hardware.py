"""Call the EXISTING PyPSA joint model with EXACT hardware and P-band constraints.

This module does not replace the existing battery energy equations. It fixes the
previously saved equipment, then lets PyPSA reoptimize all 8760 hourly decisions.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from pathlib import Path
import sys
import pandas as pd


@dataclass(frozen=True)
class Hardware:
    panels: int
    battery_modules: int
    battery_power_dc_kw: float
    inverter_kva: float
    transformer_kva: float
    loading_pu: float
    load_pf: float
    export_policy: str
    annual_equipment_usd: float
    annual_total_usd: float

    @classmethod
    def from_manifest(cls, manifest):
        s=manifest['settings']; x=manifest['summary']
        pan=round(float(x['panels_equivalent']))
        modules=round(float(x['battery_modules_equivalent']))
        inv=float(x['inverter_ac_kva_assumed_unity_pf'])
        power=float(x['battery_power_dc_kw'])
        if abs(pan-float(x['panels_equivalent']))>1e-5 or abs(modules-float(x['battery_modules_equivalent']))>1e-5:
            raise ValueError('Selected reference hardware is not discrete')
        if min(pan,modules,inv,power)<0 or inv<=0:
            raise ValueError('Invalid selected hardware')
        if abs(float(x.get('unserved_kwh',0)))>1e-6:
            raise ValueError('Reference has unserved energy')
        return cls(pan,modules,power,inv,float(s['transformer_kva']),
                   float(s['loading_pu']),float(s['load_pf']),str(s['export_policy']),
                   float(x['annual_equipment_usd']),float(x['annual_total_usd']))


def physical_soc_floor_usable_kwh(modules:int, min_soc:float, nominal_module_kwh=5.12, reference_usable_module_kwh=17.3/4):
    """Translate manufacturer physical-SOC floor into ORIGINAL usable Store coordinates.

    Original e=0 corresponds to historical implicit physical SOC of
    (5.12 - 4.325)/5.12 = 15.53% if the rated 5.12kWh is available at 100% SOC.
    DO NOT cap Store.e upper bound by 80% while leaving e=0 unchanged, because
    that would shift the operating window rather than enforce >=20% physical SOC.
    """
    if not isinstance(modules,int) or modules<0 or not 0<=min_soc<1:
        raise ValueError("Invalid module count or physical minimum SOC")
    if not 0 < reference_usable_module_kwh <= nominal_module_kwh:
        raise ValueError("Inconsistent historical usable and nominal battery energy")
    floor_per_module=max(0., reference_usable_module_kwh-(1-min_soc)*nominal_module_kwh)
    return modules*floor_per_module



def load_existing_pypsa_model(repo_root: Path):
    model_dir=repo_root/'case1/studies/pypsa_joint_optimization_v1'
    if not (model_dir/'model.py').exists():
        raise FileNotFoundError(f'Existing joint PyPSA model not found: {model_dir}')
    sys.path.insert(0,str(model_dir))
    import model
    return model


def fixed_settings(model, hardware: Hardware):
    return model.Settings(transformer_kva=hardware.transformer_kva,
        loading_pu=hardware.loading_pu,load_pf=hardware.load_pf,
        max_panels=hardware.panels,fixed_panels=hardware.panels,
        max_battery_modules=hardware.battery_modules,
        fixed_battery_modules=hardware.battery_modules,
        max_battery_power_kw=max(hardware.battery_power_dc_kw,0.001),
        max_inverter_kva=hardware.inverter_kva,
        export_policy=hardware.export_policy,objective='economic',
        discrete=False,allow_unserved=False)


def solve_fixed(repo_root: Path, hardware: Hardware, demand:pd.Series,
                pv_pu:pd.Series, corridors=None, min_physical_soc:float | None=.20):
    """Solve full-year fixed equipment; corridors: {pd.Timestamp: (minP,maxP)}.

    Link-p is inverter DC input; multiply by ETA_INV for AC output.
    The legacy battery's Store e_cyclic=True and charge/discharge efficiencies
    remain intact. A corridor cannot give the battery free energy.
    """
    # Manufacturer-sourced: Deye SE-G5.1 recommends 80% DoD and 50A continuous
    # charge/discharge current per 5.12kWh unit. For this screening bound, use
    # the published minimum operating voltage 44.8V to avoid assuming constant
    # nominal 51.2V at low SOC; exact BMS/current sharing require review.
    continuous_kw_per_module=44.8*50./1000.
    if hardware.battery_power_dc_kw > hardware.battery_modules*continuous_kw_per_module + 1e-6:
        raise ValueError('Saved battery kW exceeds SE-G5.1 nominal bank continuous current screen; do not silently derate.')
    model=load_existing_pypsa_model(repo_root)
    settings=fixed_settings(model,hardware)
    n=model.make_network(demand,pv_pu,settings)
    n.optimize.create_model()
    model.add_investment_constraints(n,settings)
    lp=n.model
    inv_nom=lp.variables['Link-p_nom'].sel(name='PV_INVERTER')
    bat_power=lp.variables['Link-p_nom'].sel(name='BAT_DISCHARGE')
    lp.add_constraints(model.ETA_INV*inv_nom==hardware.inverter_kva,
                       name='fixed_reference_inverter_kva')
    lp.add_constraints(bat_power==hardware.battery_power_dc_kw,
                       name='fixed_reference_battery_dc_kw')
    if min_physical_soc is not None:
        min_energy=physical_soc_floor_usable_kwh(hardware.battery_modules, float(min_physical_soc))
        e_hour=lp.variables['Store-e'].sel(name='BATTERY')
        lp.add_constraints(e_hour >= min_energy,name='manufacturer_physical_SOC_floor')
    if corridors:
        inv_hour=lp.variables['Link-p'].sel(name='PV_INVERTER')
        for i,(timestamp,(lo,hi)) in enumerate(sorted(corridors.items())):
            ts=pd.Timestamp(timestamp)
            if ts not in n.snapshots:
                raise ValueError('Corridor timestamp missing from full-year model: '+str(ts))
            if lo<0 or hi<lo or hi>hardware.inverter_kva+1e-6:
                raise ValueError('Invalid corridor P limits')
            p=model.ETA_INV*inv_hour.sel(snapshot=ts)
            lp.add_constraints(p >= lo, name=f'AC_P_LO_{i:05d}')
            lp.add_constraints(p <= hi, name=f'AC_P_HI_{i:05d}')
    status,condition=n.optimize.solve_model(solver_name=settings.solver_name)
    if status!='ok' or condition!='optimal':
        raise RuntimeError(f'Fixed hardware P corridor solve: {status}/{condition}')
    hourly=model.extract(n,settings,demand)
    summary=model.summarize(n,hourly,settings,'AC_AWARE_FIXED_HARDWARE')
    if hourly.unserved_kw.abs().max()>1e-6:
        raise AssertionError('ENS must be zero')
    if hardware.export_policy=='zero' and hourly.grid_export_kw.abs().max()>1e-6:
        raise AssertionError('Export policy violated')
    if not (n.stores.at['BATTERY','e_cyclic']):
        raise AssertionError('Lost annual cyclic SOC boundary')
    if min_physical_soc is not None:
        limit=physical_soc_floor_usable_kwh(hardware.battery_modules,float(min_physical_soc))
        if float(hourly.battery_soc_usable_kwh.min()) < limit-1e-5:
            raise AssertionError('SE-G5.1 physical SOC / DOD floor violated')
    # End-to-end hourly energy balance; e_t includes current-hour charge/discharge.
    soc=hourly.battery_soc_usable_kwh.to_numpy(float)
    charge=hourly.battery_charge_dc_kw.to_numpy(float)
    discharge=hourly.battery_discharge_dc_kw.to_numpy(float)
    import numpy as np
    residue=soc-np.roll(soc,1)-model.ETA_BAT*charge+discharge/model.ETA_BAT
    if np.max(np.abs(residue))>1e-3:
        raise AssertionError('Hourly SOC energy balance failed')
    return hourly,summary
