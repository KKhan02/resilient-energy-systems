#!/usr/bin/env python3
"""Read-only archiver for two existing 12-house annual EPM AC candidate runs.

Writes a comparison and a self-contained ZIP inside a fresh project-local folder.
No solver, no source changes, no overwrites, no Git operations.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pathlib
import sys
import zipfile

CANDIDATES = (
    'EC-ae0eed011a95698df0af',  # 54 PV, 9 battery, 20 kVA
    'EC-70d86432647ba0b77603',  # 56 PV, 10 battery, 20 kVA
)
STUDY = pathlib.Path('case1/studies/ac_aware_redispatch_v1')
SOURCE_ENERGY = STUDY / 'outputs/campaign_manufacturer_01'
SOURCE_AC = STUDY / 'outputs/campaign_AC_01'
SCENARIO = 'pf_0.98_service_1.00'
AC_FILES = (
    'ac_checkpoint.json', 'annual_ac_summary.json', 'annual_ac_hours.csv',
    'annual_ac_violating_hours.csv', 'annual_ac_worst_voltage_hours.csv',
    'voltage_band_comparison.csv',
)
ENERGY_FILES = ('pilot_manifest.json', 'fixed_hardware_manufacturer_soc_baseline.csv')
SUMMARY_COLS = (
    'candidate_id', 'status', 'source_integrity', 'hours_checked', 'converged_hours',
    'ac_feasible_hours', 'ac_feasible_full_year', 'min_voltage_pu',
    'max_voltage_pu', 'max_trafo_loading_pct', 'max_line_loading_pct',
    'sum_modelled_ac_losses_kwh', 'manufacturer_soc_baseline_annual_total_usd',
    'manufacturer_soc_baseline_grid_import_kwh', 'source_trajectory_sha256',
    'missing_files', 'issues',
)


def sha256(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_json(path: pathlib.Path, issues: list[str]):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError) as error:
        issues.append(f'Invalid JSON: {path.name}: {error}')
        return None


def inspect_candidate(repo: pathlib.Path, candidate: str):
    ac_dir = repo / SOURCE_AC / candidate / SCENARIO
    energy_dir = repo / SOURCE_ENERGY / candidate
    files = []
    missing = []
    issues = []
    row = {k: '' for k in SUMMARY_COLS}
    row['candidate_id'] = candidate
    for dirname, selected in ((ac_dir, AC_FILES), (energy_dir, ENERGY_FILES)):
        for filename in selected:
            file = dirname / filename
            if file.is_file():
                files.append(file)
            else:
                missing.append(str(file.relative_to(repo)))
    summary = load_json(ac_dir / 'annual_ac_summary.json', issues)
    checkpoint = load_json(ac_dir / 'ac_checkpoint.json', issues)
    energy = load_json(energy_dir / 'pilot_manifest.json', issues)
    for field in (
        'hours_checked', 'converged_hours', 'ac_feasible_hours',
        'ac_feasible_full_year', 'min_voltage_pu', 'max_voltage_pu',
        'max_trafo_loading_pct', 'max_line_loading_pct',
        'sum_modelled_ac_losses_kwh', 'source_trajectory_sha256',
    ):
        if summary is not None:
            row[field] = summary.get(field, '')
    for field in ('manufacturer_soc_baseline_annual_total_usd',
                  'manufacturer_soc_baseline_grid_import_kwh'):
        if energy is not None:
            row[field] = energy.get(field, '')
    ac_hours_path = ac_dir / 'annual_ac_hours.csv'
    trajectory_path = energy_dir / 'fixed_hardware_manufacturer_soc_baseline.csv'
    integrity = True
    if not (summary and checkpoint and ac_hours_path.is_file()):
        integrity = False
        issues.append('AC summary, checkpoint or annual hour CSV missing')
    if summary:
        if summary.get('candidate_id') != candidate:
            integrity = False
            issues.append('Summary candidate ID does not match folder')
        if summary.get('load_pf') is not None and abs(float(summary['load_pf']) - .98) > 1e-9:
            integrity = False
            issues.append('Unexpected reference load PF')
        if summary.get('service_factor') is not None and abs(float(summary['service_factor']) - 1) > 1e-9:
            integrity = False
            issues.append('Unexpected service factor')
        if summary.get('hours_checked') != 8760 or summary.get('all_8760_evaluated') is not True:
            integrity = False
            issues.append('AC summary does not attest all 8760 hours')
    if checkpoint:
        if checkpoint.get('status') != 'COMPLETE' or checkpoint.get('hours_saved') != 8760:
            integrity = False
            issues.append('Annual AC checkpoint is not COMPLETE with 8760 hours')
        sign = checkpoint.get('signature') or {}
        if sign.get('candidate_id') != candidate:
            integrity = False
            issues.append('AC checkpoint candidate signature differs')
        if ac_hours_path.is_file() and sha256(ac_hours_path) != checkpoint.get('annual_ac_hours_sha256'):
            integrity = False
            issues.append('Annual AC hourly CSV SHA256 mismatch')
    if ac_hours_path.is_file():
        with ac_hours_path.open('r', encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            count = 0
            ordered = True
            for count, hour in enumerate(reader, start=1):
                if 'hour_index' in (reader.fieldnames or ()):
                    try:
                        if int(hour['hour_index']) != count - 1:
                            ordered = False
                    except (ValueError, TypeError):
                        ordered = False
        if count != 8760 or not ordered:
            integrity = False
            issues.append(f'Annual AC CSV expected ordered 8760 hours; found {count} rows, order_valid={ordered}')
    if not (energy and trajectory_path.is_file()):
        integrity = False
        issues.append('Manufacturer SOC manifest or source trajectory missing')
    else:
        energy_hash = sha256(trajectory_path)
        if energy.get('candidate_id') != candidate:
            integrity = False
            issues.append('Energy manifest candidate ID differs')
        if energy.get('source_trajectory_sha256') != energy_hash:
            integrity = False
            issues.append('Manufacturer SOC source trajectory SHA256 mismatch')
        if summary and summary.get('source_trajectory_sha256') != energy_hash:
            integrity = False
            issues.append('Annual AC summary source trajectory hash mismatch')
        if checkpoint and checkpoint.get('signature', {}).get('trajectory_sha256') != energy_hash:
            integrity = False
            issues.append('Annual AC checkpoint source trajectory hash mismatch')
    if summary and checkpoint and not issues:
        row['status'] = ('COMPLETE_AC_FEASIBLE' if summary.get('ac_feasible_full_year') is True
                         else 'COMPLETE_AC_VIOLATIONS')
    elif not ac_dir.is_dir():
        row['status'] = 'AC_NOT_FOUND'
    else:
        row['status'] = 'INCOMPLETE_OR_PROVENANCE_UNVERIFIED'
    row['source_integrity'] = 'VERIFIED' if integrity else 'NOT_VERIFIED'
    row['missing_files'] = '; '.join(missing)
    row['issues'] = '; '.join(issues)
    return row, files


def build_export(repo: pathlib.Path, out: pathlib.Path, candidates=CANDIDATES):
    repo = repo.resolve()
    out = out.resolve()
    if not out.is_relative_to(repo):
        raise ValueError('Export output must be inside the project repository')
    if out.exists():
        raise FileExistsError(f'Output exists; use a new study-local folder: {out}')
    if not (repo / SOURCE_AC).is_dir():
        raise FileNotFoundError(f'Annual AC campaign not found: {repo / SOURCE_AC}')
    rows = []
    source_files = []
    for candidate in candidates:
        row, files = inspect_candidate(repo, candidate)
        rows.append(row)
        source_files.extend(files)
    out.mkdir(parents=True, exist_ok=False)
    output_csv = out / 'comparison.csv'
    with output_csv.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLS)
        writer.writeheader()
        writer.writerows(rows)
    hashes = {str(path.relative_to(repo)).replace('\\', '/'): sha256(path)
              for path in sorted(set(source_files))}
    output_json = out / 'export_manifest.json'
    output_json.write_text(json.dumps({
        'purpose': 'Evidence package only; read-only; no new optimization or AC',
        'scenario': SCENARIO, 'candidate_count': len(candidates),
        'candidates': rows, 'source_file_sha256': hashes,
        'source_repo_file_paths_relative_to_project': sorted(hashes),
        'all_candidates_verified': all(r['source_integrity'] == 'VERIFIED' for r in rows),
    }, indent=2, default=str) + '\n', encoding='utf-8')
    readme = out / 'README.md'
    readme.write_text(
        '# SEEDExchange two-candidate annual AC export\n\n'
        'This is a read-only snapshot of saved PF=0.98, service=1.0 runs. '
        'No new AC or PyPSA simulation was executed. See comparison.csv and '
        'export_manifest.json for checks and missing files. The ZIP embeds all '
        'found source CSVs and manifests, retaining repository-relative paths. '
        'Not all absent supplemental figure/CSV files indicate failed annual AC.\n',
        encoding='utf-8',
    )
    zip_path = out / 'SEEDExchange_two_12house_annual_AC.zip'
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as archive:
        for p in (output_csv, output_json, readme):
            archive.write(p, arcname=p.name)
        for p in sorted(set(source_files)):
            archive.write(p, arcname='repo_sources/' + p.relative_to(repo).as_posix())
    return {'comparison': str(output_csv), 'manifest': str(output_json),
            'zip': str(zip_path), 'candidates': rows}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root', type=pathlib.Path, default=pathlib.Path('.'))
    p.add_argument('--output-dir', type=pathlib.Path, required=True)
    args = p.parse_args(argv)
    try:
        result = build_export(args.repo_root, args.output_dir)
    except (ValueError, FileNotFoundError, FileExistsError) as error:
        p.error(str(error))
    print(json.dumps(result, indent=2, default=str))
    if any(r['source_integrity'] != 'VERIFIED' for r in result['candidates']):
        print('Some candidate evidence is missing or incomplete; inspect manifest before interpreting.',
              file=sys.stderr)


if __name__ == '__main__':
    main()
