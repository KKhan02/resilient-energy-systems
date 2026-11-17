#!/usr/bin/env python3
"""Source-signed, SOC-neutral B9 stress-case feasibility trial, NOT a new optimum.

Run on user's local SEEDExchange checkout. Original signed 2025 energy and AC
replays remain immutable. At PF 0.95 and length x1.6, re-run ONLY changed
hours with the original balanced pandapower solver and reuse all unchanged
source-verified annual AC snapshots. All-nine coverage remains pending.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ETA_INV = .95
ETA_BAT = math.sqrt(.95)
CASES = ('SS_B9', 'MC_B9')
PLANS = {
    'SS_B9': [('2025-11-27 18:00:00', '2025-11-27 20:00:00', 'nov')],
    'MC_B9': [('2025-10-13 17:00:00', '2025-10-13 20:00:00', 'oct'),
              ('2025-11-27 18:00:00', '2025-11-27 20:00:00', 'nov')],
}
FAIL_HOURS = {
    'SS_B9': {'2025-11-27 20:00:00'},
    'MC_B9': {'2025-10-13 20:00:00', '2025-11-27 20:00:00'},
}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def add_frontier_module(repo):
    path = repo / 'case1/studies/SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17'
    sys.path.insert(0, str(path))
    import validate_frontier_ac as frontier
    return frontier


def check_dispatch(frame, hardware):
    modules = int(hardware['battery_modules'])
    rating = float(hardware['battery_power_dc_kw'])
    inverter = float(hardware['inverter_kva'])
    floor, ceiling = modules * .229, modules * 4.325
    cols = ['demand_kw', 'pv_dc_generated_kw', 'pv_dc_available_kw',
            'battery_charge_dc_kw', 'battery_discharge_dc_kw',
            'inverter_ac_kw', 'battery_soc_usable_kwh', 'grid_import_kw',
            'grid_export_kw', 'unserved_kw', 'curtailed_pv_dc_kw']
    if len(frame) != 8760 or not frame.index.equals(pd.date_range('2025-01-01', periods=8760, freq='h')):
        raise ValueError('Not exact 2025 hourly chronology')
    if not np.isfinite(frame[cols].to_numpy(float)).all():
        raise ValueError('Non-finite dispatch')
    def arr(key): return frame[key].to_numpy(float)
    inv, imp = arr('inverter_ac_kw'), arr('grid_import_kw')
    ch, dis, soc = arr('battery_charge_dc_kw'), arr('battery_discharge_dc_kw'), arr('battery_soc_usable_kwh')
    if min(dis.min(), ch.min(), inv.min(), imp.min()) < -5e-5:
        raise ValueError('Negative power or import')
    if max(dis.max(), ch.max()) > rating + 5e-5 or inv.max() > inverter + 5e-5:
        raise ValueError('Bank or inverter power exceeded')
    if soc.min() < floor - 5e-5 or soc.max() > ceiling + 5e-5:
        raise ValueError('SOC outside manufacturer-constrained model')
    if max(abs(arr('grid_export_kw'))) > 5e-5 or max(abs(arr('unserved_kw'))) > 5e-5:
        raise ValueError('Zero export or zero ENS violated')
    if max(abs(inv + imp - arr('demand_kw'))) > 5e-5:
        raise ValueError('AC demand not conserved')
    if max(abs(arr('pv_dc_generated_kw') + dis - ch - inv / ETA_INV)) > 5e-5:
        raise ValueError('DC link balance failure')
    soc_delta = ETA_BAT * ch - dis / ETA_BAT
    if max(abs(soc[1:] - soc[:-1] - soc_delta[1:])) > 5e-5:
        raise ValueError('Hourly SOC recurrence failure')
    if abs(soc[0] - soc[-1] - soc_delta[0]) > 5e-5:
        raise ValueError('Cyclic year boundary failure')
    return {'min_usable_soc_kwh': float(soc.min()),
            'max_usable_soc_kwh': float(soc.max()),
            'annual_grid_import_kwh': float(imp.sum()),
            'annual_discharge_dc_kwh': float(dis.sum()),
            'year_end_usable_soc_kwh': float(soc[-1])}


def shift(frame, hardware, case_id, oct_dc=.60, nov_dc=.80):
    """Exactly energy-neutral, same-day shifts; no physical feasibility assumed."""
    trial = frame.copy(deep=True)
    register = []
    for source, target, label in PLANS[case_id]:
        move = float(oct_dc if label == 'oct' else nov_dc)
        src, dst = pd.Timestamp(source), pd.Timestamp(target)
        if not (0 < move <= 2.0 and src in trial.index and dst in trial.index):
            raise ValueError('Invalid candidate power or timestamps')
        if not (src.date() == dst.date() and src < dst):
            raise ValueError('Moves must be same day and forward')
        if trial.loc[src, 'battery_discharge_dc_kw'] < move + 1e-5:
            raise ValueError('Source has insufficient discharge capacity')
        if trial.loc[dst, 'battery_charge_dc_kw'] > 1e-8 or trial.loc[dst, 'pv_dc_available_kw'] > 1e-8:
            raise ValueError('Destination is not a night-time discharge hour')
        if trial.loc[dst, 'grid_import_kw'] < ETA_INV * move + 1e-5:
            raise ValueError('Destination would export')
        trial.loc[src, 'battery_discharge_dc_kw'] -= move
        trial.loc[dst, 'battery_discharge_dc_kw'] += move
        trial.loc[src, 'inverter_ac_kw'] -= ETA_INV * move
        trial.loc[dst, 'inverter_ac_kw'] += ETA_INV * move
        trial.loc[src, 'grid_import_kw'] += ETA_INV * move
        trial.loc[dst, 'grid_import_kw'] -= ETA_INV * move
        trial.loc[(trial.index >= src) & (trial.index < dst), 'battery_soc_usable_kwh'] += move / ETA_BAT
        if 'pcc_p_kw' in trial.columns:
            for t in (src, dst):
                trial.loc[t, 'pcc_p_kw'] = trial.loc[t, 'grid_import_kw'] - trial.loc[t, 'grid_export_kw']
                trial.loc[t, 'pcc_kva_proxy'] = math.hypot(float(trial.loc[t, 'pcc_p_kw']), float(trial.loc[t, 'pcc_q_kvar_proxy']))
        register.append({'case_id': case_id, 'donor_timestamp': source,
                         'target_timestamp': target, 'dc_transfer_kw': move,
                         'target_added_ac_kw': ETA_INV * move,
                         'temporary_soc_increase_kwh': move / ETA_BAT})
    original = check_dispatch(frame, hardware)
    corrected = check_dispatch(trial, hardware)
    for key in ('annual_grid_import_kwh', 'annual_discharge_dc_kwh', 'year_end_usable_soc_kwh'):
        if abs(original[key] - corrected[key]) > 5e-5:
            raise ValueError('SOC/energy-neutral invariant failed: '+key)
    for col in ('curtailed_pv_dc_kw', 'pv_dc_available_kw', 'pv_dc_generated_kw',
                'battery_charge_dc_kw', 'grid_export_kw', 'unserved_kw'):
        if not np.allclose(trial[col].values, frame[col].values, atol=1e-9, rtol=0):
            raise ValueError('Protected series altered: '+col)
    return trial, register, {'original': original, 'candidate': corrected}


def source_ac(repo, frontier, case_id, frame, manifest_sha, ctx, source_manifest):
    folder = repo / 'StudyA_A1_106039_Frontier_AC_v1' / f'{case_id}_pf095_l16'
    provenance = {
        'case_id': case_id, 'scenario': 'A1', 'transformer': '106039',
        'pf': .95, 'length_factor': 1.6, '2025_hours': 8760,
        'new_energy_manifest_sha256': manifest_sha,
        'source_v6_2_sha256': frontier.sha(repo / source_manifest),
        'input_manifest_sha256': frontier.sha(ctx['mp']),
        'q_ratio_daylight': .25, 'night_q_disabled': True,
        'method': 'independent_hourly_balanced_pandapower_replay'
    }
    meta = frontier.check_saved(folder, provenance)
    if not meta:
        raise FileNotFoundError(f'Original signed stress result missing: {folder}')
    ac = pd.read_csv(frontier.xp(folder / 'ac_hourly.csv'), parse_dates=['timestamp_lst']).set_index('timestamp_lst')
    if not ac.index.equals(frame.index):
        raise ValueError('Baseline stress AC and new energy timestamps differ')
    if not np.allclose(ac.inverter_ac_kw.to_numpy(float), frame.inverter_ac_kw.to_numpy(float), atol=5e-6, rtol=0):
        raise ValueError('Baseline AC inverter injections differ from signed energy')
    if not np.allclose(ac.gross_demand_kw.to_numpy(float), ctx['trace'].sum(axis=1).to_numpy(float), atol=5e-6, rtol=0):
        raise ValueError('Baseline AC household demand differs from original mapping')
    bad = set(ac.index[~ac.ac_feasible.astype(bool)].strftime('%Y-%m-%d %H:%M:%S'))
    if bad != FAIL_HOURS[case_id]:
        raise ValueError(f'Unexpected stress violations: {case_id}: {bad}')
    return ac, meta


def prepare(repo, oct_dc, nov_dc):
    frontier = add_frontier_module(repo)
    st, ctx = frontier.make_context(repo)
    results = {}
    for case in CASES:
        frame, man, man_sha = frontier.signed_energy(repo, repo / 'StudyA_A1_106039_Utilization_v1', case, st, ctx)
        original_ac, ac_meta = source_ac(repo, frontier, case, frame, man_sha, ctx, st.RUNNER_REL)
        candidate, changes, review = shift(frame, man['hardware'], case, oct_dc, nov_dc)
        results[case] = dict(frame=frame, hardware=man['hardware'], candidate=candidate,
                             original_ac=original_ac, ac_meta=ac_meta, changes=changes,
                             energy_review=review, energy_manifest_sha=man_sha)
    return frontier, ctx, results


def solve_changed(repo, frontier, ctx, results):
    ctx['v6'].repo_modules(repo)
    from run_epm_validation import build_net
    import pandapower as pp
    checks, summary = [], []
    for case, d in results.items():
        territory = ctx['v6'].new_territory(repo, 'A1', '106039', ctx['houses'], 1.6)
        net, nodes = build_net(territory, 'head')
        if set(nodes['loads']) != set(ctx['houses']):
            raise ValueError('Different mapped household connections')
        old_ac = d['original_ac']
        new_ac = old_ac.copy(deep=True)
        changed = sorted(set(pd.Timestamp(r[key]) for r in d['changes']
                             for key in ('donor_timestamp', 'target_timestamp')))
        for t in changed:
            for label, frame in (('original', d['frame']), ('candidate', d['candidate'])):
                record = ctx['v6'].solve_ac_hour(net, nodes, territory, t, ctx['trace'].loc[t], .95,
                    float(frame.loc[t, 'inverter_ac_kw']), float(d['hardware']['inverter_kva']),
                    float(frame.loc[t, 'pv_dc_available_kw']), .25, 9, 'pvbess', pp)
                if record['status'] != 'CONVERGED':
                    raise RuntimeError(f'Changed-hour AC did not converge: {case}/{t}/{label}')
                if label == 'original':
                    prior = old_ac.loc[t]
                    for metric in ('min_v_pu', 'max_v_pu', 'max_trafo_pct', 'max_line_pct', 'pcc_kva'):
                        if abs(float(record[metric]) - float(prior[metric])) > 2e-4:
                            raise ValueError(f'Original AC reproduction failed: {case}/{t}/{metric}')
                else:
                    for key, val in record.items():
                        if key in new_ac.columns:
                            new_ac.loc[t, key] = val
                checks.append(dict(case_id=case, phase=label, timestamp_lst=str(t),
                                   min_v_pu=float(record['min_v_pu']), max_v_pu=float(record['max_v_pu']),
                                   max_trafo_pct=float(record['max_trafo_pct']),
                                   max_line_pct=float(record['max_line_pct']),
                                   converged=record['status'] == 'CONVERGED',
                                   ac_feasible=bool(record['ac_feasible']),
                                   inverter_ac_kw=float(frame.loc[t, 'inverter_ac_kw'])))
        corrected_feasible = frontier.valid_ac(new_ac)
        if not corrected_feasible.equals(new_ac.ac_feasible.astype(bool)):
            raise ValueError('Corrected AC violation flags inconsistent')
        bad = new_ac.index[~corrected_feasible]
        summary.append({'case_id': case, 'pf': .95, 'length_factor': 1.6,
                        'original_fail_hours': len(FAIL_HOURS[case]),
                        'candidate_fail_hours': int((~corrected_feasible).sum()),
                        'candidate_fail_timestamps': ';'.join(map(str, bad)),
                        'original_max_trafo_pct': float(old_ac.max_trafo_pct.max()),
                        'candidate_max_trafo_pct': float(new_ac.max_trafo_pct.max()),
                        'candidate_min_v_pu': float(new_ac.min_v_pu.min()),
                        'candidate_max_line_pct': float(new_ac.max_line_pct.max()),
                        'changed_hours_replayed': len(changed),
                        'baseline_ac_sha256': d['ac_meta']['ac_hourly_sha256'],
                        'all_8760_snapshots_accounted_for': len(new_ac) == 8760})
    return checks, summary


def execute(repo, out, oct_dc, nov_dc, preflight=False):
    repo = repo.resolve()
    if not preflight and out.exists():
        raise FileExistsError(f'Refusing to overwrite original result: {out}')
    frontier, ctx, results = prepare(repo, oct_dc, nov_dc)
    overview = {'study': 'A1 106039 nine-module fixed-hardware B9 AC trial',
        'status': 'PREFLIGHT_SOURCE_SOC_PASS_NO_AC' if preflight else 'UNTESTED',
        'baseline': '2025 signed stress AC and new fixed-hardware annual energy',
        'year_hours': 8760, 'factor_grid_tested': [[.95, 1.6]],
        'all_nine_factors_validated': False,
        'cases': {case: {'energy_manifest_sha256': d['energy_manifest_sha'],
                         'baseline_ac_sha256': d['ac_meta']['ac_hourly_sha256'],
                         'hardware': d['hardware'], 'energy': d['energy_review'],
                         'proposed_transfers': d['changes']} for case, d in results.items()},
        'scope': 'Research-only stress trial. No new optimum, policy approval or field certification'}
    if preflight:
        return overview
    checks, summary = solve_changed(repo, frontier, ctx, results)
    overall = all(s['candidate_fail_hours'] == 0 for s in summary)
    overview['status'] = 'STRESS_PASS_ONLY_ALL_NINE_PENDING' if overall else 'STRESS_FAILED_RETAIN_EVIDENCE'
    overview['stress_ac_comparison'] = summary
    out.mkdir(parents=True, exist_ok=False)
    pd.DataFrame(checks).to_csv(out / 'CHANGED_HOUR_AC_CHECKS.csv', index=False)
    pd.DataFrame(summary).to_csv(out / 'STRESS_CASE_COMPARISON.csv', index=False)
    pd.DataFrame([x for d in results.values() for x in d['changes']]).to_csv(out / 'CANDIDATE_SHIFT_REGISTER.csv', index=False)
    for case, d in results.items():
        filename = f'{case}_candidate_energy_8760.csv'
        d['candidate'].to_csv(out / filename, float_format='%.10f', index_label='timestamp_lst')
        overview['cases'][case]['candidate_energy_file'] = filename
        overview['cases'][case]['candidate_energy_sha256'] = sha(out / filename)
    (out / 'TRIAL_MANIFEST.json').write_text(json.dumps(overview, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return {'status': overview['status'], 'cases': summary,
            'output': str(out), 'all_nine_pending': True,
            'changed_hour_ac_calls': len(checks)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root', type=Path, default=Path.cwd())
    ap.add_argument('--out', type=Path, default=Path('StudyA_A1_106039_B9_SOC_Trial_v1'))
    ap.add_argument('--oct-dc', type=float, default=.60)
    ap.add_argument('--nov-dc', type=float, default=.80)
    ap.add_argument('--preflight', action='store_true')
    args = ap.parse_args(argv)
    print(json.dumps(execute(args.repo_root, args.out, args.oct_dc, args.nov_dc, args.preflight), indent=2))


if __name__ == '__main__':
    main()
