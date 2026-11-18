#!/usr/bin/env python3
"""Nine-factor changed-hour B9 AC screen. NOT full-year or equipment certification.

Requires an independently generated, source-consistent B9 stress result that
passed at PF=0.95, length x1.6. Replays just six unique changed case-hours
(two for SS_B9, four for MC_B9), twice per hour, across nine factors.
Original signed 2025 sources remain untouched. All unchanged hours outside the
stress factor still require a full-year AC replay before annual feasibility.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

FACTORS = [(pf, length) for pf in (.95, .98, 1.00) for length in (1., 1.3, 1.6)]
NUM_CASE_HOURS = {'SS_B9': 2, 'MC_B9': 4}


def load_b9():
    file = Path(__file__).with_name('b9_soc_trial.py')
    spec = importlib.util.spec_from_file_location('b9_soc_trial_for_nine_factor', file)
    if spec is None or spec.loader is None:
        raise ImportError(f'Cannot load source B9 trial at {file}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def changed_timestamps(case_data):
    changes = case_data['changes']
    return sorted(set(pd.Timestamp(c[col]) for c in changes
                      for col in ('donor_timestamp', 'target_timestamp')))


def check_result_gate(root, stress_root, results, b9):
    """Read back *actual* successful stress evidence; never accept an unrun claim."""
    if not stress_root.is_dir():
        raise FileNotFoundError(f'User-run stress directory missing: {stress_root}')
    manifest_path = stress_root / 'TRIAL_MANIFEST.json'
    if not manifest_path.is_file():
        raise FileNotFoundError(f'Stress trial manifest missing: {manifest_path}')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('status') != 'STRESS_PASS_ONLY_ALL_NINE_PENDING':
        raise ValueError('Stress not verified as passing. Resolve stress violations first.')
    if manifest.get('factor_grid_tested') != [[.95, 1.6]] or manifest.get('all_nine_factors_validated') is not False:
        raise ValueError('Wrong stress factor provenance or ambiguous coverage')
    if set(manifest.get('cases', {})) != set(b9.CASES):
        raise ValueError('Unexpected or missing B9 stress cases')
    items = manifest.get('stress_ac_comparison')
    if not isinstance(items, list) or len(items) != len(b9.CASES):
        raise ValueError('Expected two recorded stress AC comparisons')
    summaries = {it['case_id']: it for it in items}
    if set(summaries) != set(b9.CASES):
        raise ValueError('Mismatched stress results')
    csv_path = stress_root / 'CHANGED_HOUR_AC_CHECKS.csv'
    if not csv_path.is_file():
        raise FileNotFoundError('Changed-hour AC source evidence missing')
    checks = pd.read_csv(csv_path, dtype={'case_id': str, 'phase': str}, parse_dates=['timestamp_lst'])
    if set(checks.case_id) != set(b9.CASES):
        raise ValueError('Wrong changed-hour case identities')
    if checks.duplicated(['case_id', 'phase', 'timestamp_lst']).any():
        raise ValueError('Duplicate saved AC result identity')
    for case in b9.CASES:
        item = results[case]
        entry = manifest['cases'][case]
        result = summaries[case]
        if entry.get('energy_manifest_sha256') != item['energy_manifest_sha']:
            raise ValueError(f'Energy manifest SHA changed for {case}')
        if entry.get('baseline_ac_sha256') != item['ac_meta']['ac_hourly_sha256']:
            raise ValueError(f'Original annual stress AC checksum changed: {case}')
        if result.get('baseline_ac_sha256') != item['ac_meta']['ac_hourly_sha256']:
            raise ValueError(f'Stress AC result source mismatch: {case}')
        if (result.get('candidate_fail_hours') != 0 or
                result.get('all_8760_snapshots_accounted_for') is not True or
                result.get('pf') != .95 or result.get('length_factor') != 1.6):
            raise ValueError(f'Stress AC feasibility not established: {case}')
        hours = changed_timestamps(item)
        if len(hours) != NUM_CASE_HOURS[case] or result.get('changed_hours_replayed') != len(hours):
            raise ValueError(f'Changed-hour count mismatch: {case}')
        matching = checks[checks.case_id == case]
        expected = {(phase, timestamp) for phase in ('original', 'candidate') for timestamp in hours}
        actual = {(row.phase, row.timestamp_lst) for row in matching.itertuples()}
        if expected != actual or len(matching) != len(expected):
            raise ValueError(f'Incomplete original/candidate stress hour comparisons: {case}')
        if not matching.converged.astype(bool).all():
            raise ValueError(f'Saved stress AC non-convergence: {case}')
        if not matching[matching.phase == 'candidate'].ac_feasible.astype(bool).all():
            raise ValueError(f'Saved stress candidate still violates AC limits: {case}')
        name = entry.get('candidate_energy_file')
        if not isinstance(name, str) or not name.startswith(case + '_candidate_energy_8760') or '/' in name or '\\' in name:
            raise ValueError(f'Unexpected candidate file path for {case}')
        saved = stress_root / name
        if not saved.is_file() or b9.sha(saved) != entry.get('candidate_energy_sha256'):
            raise ValueError(f'Candidate schedule file not source-consistent: {case}')
        frame = pd.read_csv(saved, parse_dates=['timestamp_lst']).set_index('timestamp_lst')
        original = item['candidate']
        if not frame.index.equals(original.index) or set(frame.columns) != set(original.columns):
            raise ValueError(f'Candidate schedule columns/index changed: {case}')
        for col in original.columns:
            if not np.allclose(frame[col].to_numpy(float), original[col].to_numpy(float),
                               rtol=0, atol=2e-7, equal_nan=False):
                raise ValueError(f'Candidate schedule changed: {case}/{col}')
    return manifest, checks


def ac_metrics(record):
    """Validate raw pandapower AC flags independently of solver-returned labels."""
    keys = ('min_v_pu', 'max_v_pu', 'max_trafo_pct', 'max_line_pct')
    converged = record.get('status') == 'CONVERGED'
    try:
        values = [float(record[key]) for key in keys]
    except (KeyError, TypeError, ValueError):
        values = [math.nan] * 4
    numerical_ok = all(math.isfinite(v) for v in values)
    pass_limits = (converged and numerical_ok and values[0] >= .95 - 1e-10 and
                   values[1] <= 1.05 + 1e-10 and values[2] <= 100 + 1e-9 and
                   values[3] <= 100 + 1e-9)
    if converged and numerical_ok and bool(record.get('ac_feasible')) != bool(pass_limits):
        raise ValueError('Original AC solver feasibility flag disagrees with limit screen')
    return dict(min_v_pu=values[0] if numerical_ok else None,
                max_v_pu=values[1] if numerical_ok else None,
                max_trafo_pct=values[2] if numerical_ok else None,
                max_line_pct=values[3] if numerical_ok else None,
                status=str(record.get('status')),
                ac_feasible=bool(pass_limits))


def compare_saved_stress(saved, case, phase, timestamp, metrics):
    sub = saved[(saved.case_id == case) & (saved.phase == phase) &
                (saved.timestamp_lst == timestamp)]
    if len(sub) != 1:
        raise ValueError(f'Signed stress comparison row missing {case}/{phase}/{timestamp}')
    prior = sub.iloc[0]
    for key in ('min_v_pu', 'max_v_pu', 'max_trafo_pct', 'max_line_pct'):
        if metrics[key] is None or abs(float(prior[key]) - metrics[key]) > 2e-4:
            raise ValueError(f'New stress AC replay does not match the verified {case}/{phase}/{timestamp}/{key}')
    if bool(prior['ac_feasible']) != metrics['ac_feasible']:
        raise ValueError('New stress AC pass/fail does not match saved result')


def run_screen(repo, stress_root, out, oct_dc, nov_dc):
    if out.exists():
        raise FileExistsError(f'Will not overwrite an earlier study: {out}')
    b9 = load_b9()
    frontier, ctx, prepared = b9.prepare(repo, oct_dc, nov_dc)
    manifest, stress_checks = check_result_gate(repo, stress_root, prepared, b9)
    ctx['v6'].repo_modules(repo)
    from run_epm_validation import build_net
    import pandapower as pp
    rows = []
    for case in b9.CASES:
        c = prepared[case]
        hours = changed_timestamps(c)
        for pf, length in FACTORS:
            territory = ctx['v6'].new_territory(repo, 'A1', '106039', ctx['houses'], length)
            net, nodes = build_net(territory, 'head')
            if set(nodes['loads']) != set(ctx['houses']):
                raise ValueError('The 11-house mapped network membership changed')
            for timestamp in hours:
                for phase, frame in (('original', c['frame']), ('candidate', c['candidate'])):
                    record = ctx['v6'].solve_ac_hour(
                        net, nodes, territory, timestamp, ctx['trace'].loc[timestamp], pf,
                        float(frame.loc[timestamp, 'inverter_ac_kw']),
                        float(c['hardware']['inverter_kva']),
                        float(frame.loc[timestamp, 'pv_dc_available_kw']),
                        .25, 9, 'pvbess', pp)
                    metrics = ac_metrics(record)
                    if pf == .95 and length == 1.6:
                        compare_saved_stress(stress_checks, case, phase, timestamp, metrics)
                    rows.append(dict(case_id=case, pf=pf, length_factor=length,
                                     phase=phase, timestamp_lst=str(timestamp),
                                     inverter_ac_kw=float(frame.loc[timestamp, 'inverter_ac_kw']),
                                     **metrics))
    out.mkdir(parents=True, exist_ok=False)
    df = pd.DataFrame(rows)
    df.to_csv(out / 'ALL_NINE_CHANGED_HOUR_AC.csv', index=False, float_format='%.10f')
    summary = []
    for (case, pf, length), group in df[df.phase == 'candidate'].groupby(['case_id', 'pf', 'length_factor']):
        summary.append({'case_id': case, 'pf': float(pf), 'length_factor': float(length),
                        'changed_case_hours': int(len(group)),
                        'changed_hours_ac_fail': int((~group.ac_feasible.astype(bool)).sum()),
                        'lowest_v_pu': group.min_v_pu.min(),
                        'highest_trafo_pct': group.max_trafo_pct.max(),
                        'highest_line_pct': group.max_line_pct.max(),
                        'coverage': 'ONLY_CHANGED_HOURS_NO_ANNUAL_FEASIBILITY'})
    aggregate = pd.DataFrame(summary).sort_values(['case_id', 'pf', 'length_factor'])
    if len(df) != 108 or len(aggregate) != 18:
        raise ValueError('Incorrect nine-factor by-hour coverage')
    aggregate.to_csv(out / 'NINE_FACTOR_CHANGED_HOUR_SUMMARY.csv', index=False, float_format='%.10f')
    passes = bool((aggregate.changed_hours_ac_fail == 0).all())
    review = {
        'status': 'NINE_FACTOR_CHANGED_HOURS_PASS_ONLY' if passes else 'NINE_FACTOR_CHANGED_HOURS_FAIL',
        'source_stress_sha256': b9.sha(stress_root / 'TRIAL_MANIFEST.json'),
        'baseline': str(stress_root),
        'source_energy_manifest_sha256': {case: prepared[case]['energy_manifest_sha'] for case in b9.CASES},
        '2025_hours_per_case': 8760, 'annual_pf_length_checks_completed': 0,
        'factors_tested': FACTORS, 'changed_case_hours_per_factor': 6,
        'AC_calls': len(df), 'factor_case_summaries': summary,
        'may_claim_full_year_feasibility': False,
        'next_gate': 'After changed-hour sensitivity passes, conduct signed 2025 8760-hour annual AC replays for every factor not yet verified',
    }
    (out / 'SCREEN_MANIFEST.json').write_text(json.dumps(review, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return {'status': review['status'], 'case_factors': 18,
            'changed_hour_AC_calls': len(df), 'output': str(out),
            'full_annual_AC_remaining': True}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root', type=Path, default=Path('.'))
    ap.add_argument('--stress-root', type=Path, default=Path('StudyA_A1_106039_B9_SOC_Trial_v2'))
    ap.add_argument('--out', type=Path, default=Path('StudyA_A1_106039_B9_NineFactor_ChangedHour_v1'))
    ap.add_argument('--oct-dc', type=float, default=.60)
    ap.add_argument('--nov-dc', type=float, default=.80)
    args = ap.parse_args()
    print(json.dumps(run_screen(args.repo_root.resolve(), args.stress_root.resolve(),
                                args.out.resolve(), args.oct_dc, args.nov_dc), indent=2))


if __name__ == '__main__':
    main()
