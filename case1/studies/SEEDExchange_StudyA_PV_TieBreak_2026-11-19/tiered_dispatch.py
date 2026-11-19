#!/usr/bin/env python3
"""Source-signed, two-stage fixed-hardware PyPSA dispatch comparison for 106039.

Stage 1: reproduce the original full-year economic LP with manufacturer SOC.
Stage 2: cap its annual grid imports and DC battery throughput, then prefer
using available PV in earlier daily hours. This is a perfect-foresight
lexicographic tie-break, NOT a causal controller or pandapower AC validation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import traceback

import numpy as np
import pandas as pd

AUDIT_DIR = Path('case1/studies/SEEDExchange_StudyA_PV_Priority_Audit_2026-11-19')
FIXED_DIR = Path('case1/studies/ac_aware_redispatch_v1')
STATUS = 'TWO_STAGE_DISPATCH_ENERGY_ONLY_NO_AC_CERTIFICATION'


def modules(repo):
    sys.path.insert(0, str(repo / AUDIT_DIR))
    sys.path.insert(0, str(repo / FIXED_DIR))
    import audit_pv_first_priority as audit
    import fixed_hardware as fixed
    return audit, fixed


def morning_weight(index):
    """Positive, bounded daily rank; earlier hours carry greater PV use weight."""
    hours = pd.DatetimeIndex(index).hour.to_numpy(dtype=float)
    return 1.0 + (23.0 - hours) / 24.0

def objective_snapshot_weights(snapshots, pv_variable):
    """Align hourly preference weights to the Linopy variable's 'snapshot' dimension.

    PyPSA input timestamps arrive as an index named 'timestamp_lst', while
    Linopy variables use 'snapshot'. Passing that named pandas index to
    xarray directly creates a mismatched coordinate dimension.
    Use the LP variable's own coordinate values instead.
    """
    import xarray as xr
    stamps = pd.DatetimeIndex(snapshots)
    if 'snapshot' not in pv_variable.coords:
        raise ValueError('PV objective variable has no snapshot coordinate')
    coord = np.asarray(pv_variable.coords['snapshot'].values)
    if coord.shape != (len(stamps),) or not np.array_equal(coord, stamps.to_numpy()):
        raise ValueError('PV objective snapshots do not match 2025 source chronology')
    return xr.DataArray(morning_weight(stamps),
                        coords={'snapshot': coord}, dims=('snapshot',))


def annual_metrics(hourly, audit):
    curtail = hourly['curtailed_pv_dc_kw'].to_numpy(float)
    grid = hourly['grid_import_kw'].to_numpy(float)
    charge = hourly['battery_charge_dc_kw'].to_numpy(float)
    discharge = hourly['battery_discharge_dc_kw'].to_numpy(float)
    soc = hourly['battery_soc_usable_kwh'].to_numpy(float)
    limit = audit.grid_bound(hourly['demand_kw'].to_numpy(float))
    return {
        'annual_grid_import_ac_kwh': float(grid.sum()),
        'annual_curtailment_dc_kwh': float(curtail.sum()),
        'weighted_daily_early_curtailment_score': float((morning_weight(hourly.index) * curtail).sum()),
        'annual_battery_dc_throughput_kwh': float((charge + discharge).sum()),
        'annual_charge_dc_kwh': float(charge.sum()),
        'annual_discharge_dc_kwh': float(discharge.sum()),
        'soc_end_usable_kwh': float(soc[-1]),
        'grid_proxy_failure_hours': int((grid > limit + 1e-5).sum()),
        'simultaneous_battery_charge_discharge_hours': int(((charge > 1e-5) & (discharge > 1e-5)).sum()),
        'simultaneous_grid_import_curtailment_hours': int(((grid > 1e-5) & (curtail > 1e-5)).sum()),
    }


def assert_physics(frame, hw, audit, model):
    arr = frame[['demand_kw', 'pv_dc_generated_kw', 'pv_dc_available_kw',
                 'battery_charge_dc_kw', 'battery_discharge_dc_kw',
                 'battery_soc_usable_kwh', 'inverter_ac_kw', 'grid_import_kw',
                 'grid_export_kw', 'unserved_kw', 'curtailed_pv_dc_kw']].to_numpy(float)
    if len(frame) != 8760 or not np.isfinite(arr).all():
        raise AssertionError('Full-year/finite result gate failed')
    if frame['grid_export_kw'].abs().max() > 1e-5 or frame['unserved_kw'].abs().max() > 1e-5:
        raise AssertionError('Zero export or zero unserved requirement violated')
    if (frame['inverter_ac_kw'] + frame['grid_import_kw'] - frame['demand_kw']).abs().max() > 2e-4:
        raise AssertionError('AC-bus energy closure failed')
    if (frame['pv_dc_generated_kw'] + frame['battery_discharge_dc_kw'] -
            frame['battery_charge_dc_kw'] - frame['inverter_ac_kw'] / model.ETA_INV).abs().max() > 2e-4:
        raise AssertionError('DC-bus energy closure failed')
    n = int(hw['battery_modules'])
    soc = frame['battery_soc_usable_kwh'].to_numpy(float)
    c = frame['battery_charge_dc_kw'].to_numpy(float)
    d = frame['battery_discharge_dc_kw'].to_numpy(float)
    if soc.min() < n * .229 - 1e-5 or soc.max() > n * 4.325 + 1e-5:
        raise AssertionError('20%-physical SOC floor or Store ceiling failed')
    if np.max(np.abs(soc-np.roll(soc,1)-model.ETA_BAT*c+d/model.ETA_BAT)) > 1e-3:
        raise AssertionError('Chronological/cyclic battery energy balance failed')
    if ((c > 1e-5) & (d > 1e-5)).any():
        raise AssertionError('Simultaneous battery charge/discharge detected')
    if (frame['grid_import_kw'].to_numpy(float) > audit.grid_bound(frame['demand_kw'])+1e-4).any():
        raise AssertionError('Assumed grid P/Q transformer proxy violated')


def build_problem(repo, source, hardware, fixed, audit):
    model = fixed.load_existing_pypsa_model(repo)
    hw = fixed.Hardware(
        panels=int(hardware['pv_panels']), battery_modules=int(hardware['battery_modules']),
        battery_power_dc_kw=float(hardware['battery_power_dc_kw']),
        inverter_kva=float(hardware['inverter_kva']), transformer_kva=5.,
        loading_pu=1., load_pf=.98, export_policy='zero',
        annual_equipment_usd=0., annual_total_usd=0.)
    if hw.battery_power_dc_kw > hw.battery_modules * 44.8 * 50. / 1000. + 1e-6:
        raise ValueError('Battery continuous current manufacturer screen exceeded')
    settings = fixed.fixed_settings(model, hw)
    pv_pu = source['pv_dc_available_kw'] / (hw.panels * model.PANEL_KW)
    if ((pv_pu < -1e-8) | (pv_pu > 1.000001)).any():
        raise ValueError('Source-derived PV per-unit profile outside 0..1')
    n = model.make_network(source['demand_kw'], pv_pu.clip(0,1), settings)
    n.optimize.create_model()
    model.add_investment_constraints(n, settings)
    m = n.model
    m.add_constraints(model.ETA_INV * m.variables['Link-p_nom'].sel(name='PV_INVERTER') == hw.inverter_kva,
                      name='fixed_reference_inverter_kva')
    m.add_constraints(m.variables['Link-p_nom'].sel(name='BAT_DISCHARGE') == hw.battery_power_dc_kw,
                      name='fixed_reference_battery_dc_kw')
    floor = fixed.physical_soc_floor_usable_kwh(hw.battery_modules, .20)
    m.add_constraints(m.variables['Store-e'].sel(name='BATTERY') >= floor,
                      name='manufacturer_physical_SOC_floor')
    return model, settings, n


def solve_checked(n, label):
    status, condition = n.optimize.solve_model(solver_name='highs')
    if status != 'ok' or condition != 'optimal':
        raise RuntimeError(f'{label}: solver outcome {status}/{condition}')


def run_case(repo, case, audit, fixed, import_tolerance, throughput_tolerance):
    source, hw, provenance = audit.read_signed(repo, case)
    model, settings, n = build_problem(repo, source, hw, fixed, audit)
    solve_checked(n, case + ' primary economic')
    primary = model.extract(n, settings, source['demand_kw'])
    assert_physics(primary, hw, audit, model)
    signed = annual_metrics(source, audit)
    original = annual_metrics(primary, audit)
    if abs(original['annual_grid_import_ac_kwh'] - signed['annual_grid_import_ac_kwh']) > .05:
        raise AssertionError('Original signed economic optimum NOT reproduced within 0.05 kWh')
    # Keep objective primary: this is a cap on the actual Stage-1 optimum,
    # not an arbitrary annual import target from a separate hardware case.
    m = n.model
    grid = m.variables['Generator-p'].sel(name='GRID_IMPORT')
    charge = m.variables['Link-p'].sel(name='BAT_CHARGE')
    discharge_dc = model.ETA_BAT * m.variables['Link-p'].sel(name='BAT_DISCHARGE')
    m.add_constraints(grid.sum() <= original['annual_grid_import_ac_kwh'] + import_tolerance,
                      name='stage2_preserve_primary_annual_grid_import')
    m.add_constraints((charge + discharge_dc).sum() <=
                      original['annual_battery_dc_throughput_kwh'] + throughput_tolerance,
                      name='stage2_limit_annual_battery_dc_throughput')
    pvgen = m.variables['Generator-p'].sel(name='PV_DC')
    weights = objective_snapshot_weights(n.snapshots, pvgen)
    # Minimize early curtailment = maximize earlier generation at fixed PV availability.
    # This does NOT force strict real-time priority, nor does it guarantee AC feasibility.
    m.add_objective(-(weights * pvgen).sum(), overwrite=True)
    solve_checked(n, case + ' secondary early PV preference')
    secondary = model.extract(n, settings, source['demand_kw'])
    assert_physics(secondary, hw, audit, model)
    new = annual_metrics(secondary, audit)
    if new['annual_grid_import_ac_kwh'] > original['annual_grid_import_ac_kwh'] + import_tolerance + 1e-4:
        raise AssertionError('Second stage exceeded primary annual grid-import budget')
    if new['annual_battery_dc_throughput_kwh'] > original['annual_battery_dc_throughput_kwh'] + throughput_tolerance + 1e-4:
        raise AssertionError('Second stage exceeded battery-throughput budget')
    if new['weighted_daily_early_curtailment_score'] > original['weighted_daily_early_curtailment_score'] + 1e-4:
        raise AssertionError('Early curtailment objective did not improve')
    changed = int(((secondary['curtailed_pv_dc_kw'] - source['curtailed_pv_dc_kw']).abs() > 1e-5).sum())
    return {
        'case_id': case, 'source_provenance': provenance,
        'source_annual': signed, 'stage1_reproduced_economic': original,
        'stage2_tiebreak': new,
        'changed_source_curtailment_hours': changed,
        'stage2_grid_import_delta_to_signed_kwh': new['annual_grid_import_ac_kwh']-signed['annual_grid_import_ac_kwh'],
        'stage2_curtailment_delta_to_signed_dc_kwh': new['annual_curtailment_dc_kwh']-signed['annual_curtailment_dc_kwh'],
        'stage2_early_curtail_score_improvement': original['weighted_daily_early_curtailment_score']-new['weighted_daily_early_curtailment_score'],
        'status': STATUS,
        'not_a_rolling_horizon_controller': True,
        'not_pandapower_ac_validated': True,
    }, primary, secondary


def run(repo, out=None, selected='both', import_tolerance=.01, throughput_tolerance=.1,
        preflight_only=False):
    repo = Path(repo).resolve()
    if import_tolerance < 0 or throughput_tolerance < 0:
        raise ValueError('Tolerance cannot be negative')
    audit, fixed = modules(repo)
    cases = ['MC_REF','MC_P33'] if selected == 'both' else [selected]
    source_checks = {}
    for c in cases:
        original, hw, evidence = audit.read_signed(repo, c)
        source_checks[c] = {'signature': evidence, 'hours': len(original), 'hardware': hw,
                            'annual': annual_metrics(original,audit)}
    if preflight_only:
        return {'status':'SIGNED_SOURCE_PREFLIGHT_ONLY', 'checks':source_checks}
    if out is None:
        raise ValueError('Provide --out for a new, non-overwriting results directory')
    out = Path(out).resolve()
    if out.exists():
        raise FileExistsError('Refusing to overwrite existing folder: ' + str(out))
    out.mkdir(parents=True)
    report={'status':'INCOMPLETE_OR_FAILURES_NOT_AC_VALIDATED', 'source_checks':source_checks,
            'stage2_import_tolerance_kwh':import_tolerance,
            'stage2_throughput_tolerance_dc_kwh':throughput_tolerance,
            'cases':{},'errors':{}}
    for c in cases:
        try:
            result, stage1, stage2 = run_case(repo,c,audit,fixed,import_tolerance,throughput_tolerance)
            for stage,frame in (('STAGE1',stage1),('STAGE2',stage2)):
                fp=out/(c+'_'+stage+'_8760.csv')
                frame.to_csv(fp,index_label='timestamp_lst',float_format='%.10f')
                result[stage+'_csv_sha256']=hashlib.sha256(fp.read_bytes()).hexdigest()
            report['cases'][c]=result
        except Exception as exc:
            report['errors'][c]={'type':type(exc).__name__,'message':str(exc),
                                 'traceback':traceback.format_exc()}
        (out/'RUN_MANIFEST.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    if not report['errors']:
        report['status']='COMPLETE_TWO_STAGE_ENERGY_ONLY_NOT_AC_VALIDATED'
        (out/'RUN_MANIFEST.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,default=Path.cwd())
    parser.add_argument('--out',type=Path)
    parser.add_argument('--case',choices=['both','MC_REF','MC_P33'],default='both')
    parser.add_argument('--preflight-only',action='store_true')
    parser.add_argument('--import-tolerance-kwh',type=float,default=.01)
    parser.add_argument('--throughput-tolerance-dc-kwh',type=float,default=.1)
    args=parser.parse_args()
    result=run(args.repo_root,args.out,args.case,args.import_tolerance_kwh,
               args.throughput_tolerance_dc_kwh,args.preflight_only)
    if args.preflight_only:
        # Preflight has a different report schema: status/checks, no errors.
        # Once its signed-source checks pass, exit successfully without
        # invoking any full-year optimizer or indexing result['errors'].
        print(json.dumps(result, indent=2, allow_nan=False))
        return
    print(json.dumps({
        'status':result['status'],
        'cases':{c:v['stage2_tiebreak'] for c,v in result['cases'].items()},
        'errors':result['errors'],'output':str(args.out)},indent=2,allow_nan=False))
    if result['errors']:
        raise SystemExit(2)


if __name__=='__main__':
    main()
