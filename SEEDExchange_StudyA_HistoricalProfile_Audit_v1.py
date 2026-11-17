#!/usr/bin/env python3
"""Read-only Study A audit of the historical PyPSA household streams.

Checks GitLab source-byte identity (including a Windows CRLF alternative) and
independently compares the original 20 HOMER stochastic household streams to
the generated 35-stream HOMER preflight. Changes no source files or models.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HISTORICAL_REL = Path('Energy Community - San Rafael') / 'pandapower_results_nasa' / 'nasa_hourly_pv_and_load_inputs.csv'
GENERATED_REL = Path('case1') / 'studies' / 'SEEDExchange_StudyA_LocalPreflight_v4' / 'outputs' / 'run_02' / 'household_profiles_2025_homer_35.csv'
EXPECTED_ORIGINAL_SHA256 = '276d3d782e3610196463704899c1026abc568a35cdbc32117a34367cd0c4b265'
N_COMPARABLE = 20
EXPECTED_HOURS = 8760
TOL_KW = 1e-12


def checksum(p: Path) -> str:
    digest = hashlib.sha256()
    with p.open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(part)
    return digest.hexdigest()


def byte_diagnostics(p: Path, expected: str) -> dict:
    raw = p.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    lf = raw.replace(b'\r\n', b'\n')
    sha_lf = hashlib.sha256(lf).hexdigest()
    bom = lf.startswith(b'\xef\xbb\xbf')
    sha_lf_without_bom = hashlib.sha256(lf[3:] if bom else lf).hexdigest()
    status = ('EXACT_BYTES' if sha == expected else
              'CRLF_ONLY' if sha_lf == expected else
              'EOL_AND_UTF8_BOM_ONLY' if bom and sha_lf_without_bom == expected else
              'BYTE_DIFFERENCE_UNRESOLVED')
    return {
        'status': status,
        'expected_gitlab_sha256': expected,
        'local_raw_sha256': sha,
        'lf_normalized_sha256': sha_lf,
        'lf_without_utf8_bom_sha256': sha_lf_without_bom,
        'bytes': len(raw),
        'crlf_count': raw.count(b'\r\n'),
        'lf_count': raw.count(b'\n'),
        'bare_cr_count': raw.count(b'\r') - raw.count(b'\r\n'),
        'has_utf8_bom': raw.startswith(b'\xef\xbb\xbf'),
    }


def compare_profiles(original: Path, generated: Path, n: int = N_COMPARABLE,
                     max_expected_hours: int = EXPECTED_HOURS, tolerance_kw: float = TOL_KW) -> dict:
    names = [f'house_{i}_kw' for i in range(1, n + 1)]
    stats = dict(
        compared_profiles=n, expected_hours=max_expected_hours,
        timestamps_compared=0, timestamp_mismatches=0,
        value_pairs_compared=0, value_mismatches=0,
        non_finite_or_missing_cells=0, max_abs_diff_kw=0.0,
        original_energy_kwh=[0.0] * n,
        generated_energy_kwh=[0.0] * n,
        samples=[],
    )
    with original.open('r', encoding='utf-8-sig', newline='') as a, generated.open('r', encoding='utf-8-sig', newline='') as b:
        orig = csv.DictReader(a)
        gen = csv.DictReader(b)
        for label, reader in [('historical', orig), ('generated', gen)]:
            missing = [col for col in ['timestamp'] + names if col not in (reader.fieldnames or [])]
            if missing:
                stats['status'] = 'MISSING_REQUIRED_COLUMNS'
                stats['missing_columns_in_' + label] = missing
                return stats
        count_orig = count_gen = 0
        # zip_longest also detects differing row counts without loading annual CSVs into memory.
        for rownum, (r1, r2) in enumerate(itertools.zip_longest(orig, gen), start=1):
            if r1 is None:
                count_gen += 1
                continue
            if r2 is None:
                count_orig += 1
                continue
            count_orig += 1
            count_gen += 1
            if r1['timestamp'] != r2['timestamp']:
                stats['timestamp_mismatches'] += 1
                if len(stats['samples']) < 8:
                    stats['samples'].append({'hour': rownum, 'error': 'timestamp_mismatch',
                                             'original': r1['timestamp'], 'generated': r2['timestamp']})
            stats['timestamps_compared'] += 1
            for i, col in enumerate(names):
                try:
                    x, y = float(r1[col]), float(r2[col])
                    if not math.isfinite(x) or not math.isfinite(y):
                        raise ValueError('nonfinite')
                except (TypeError, ValueError):
                    stats['non_finite_or_missing_cells'] += 1
                    if len(stats['samples']) < 8:
                        stats['samples'].append({'hour': rownum, 'column': col, 'error': 'nonfinite_or_missing'})
                    continue
                stats['original_energy_kwh'][i] += x
                stats['generated_energy_kwh'][i] += y
                stats['value_pairs_compared'] += 1
                delta = abs(x - y)
                stats['max_abs_diff_kw'] = max(stats['max_abs_diff_kw'], delta)
                if delta > tolerance_kw:
                    stats['value_mismatches'] += 1
                    if len(stats['samples']) < 8:
                        stats['samples'].append({'hour': rownum, 'column': col,
                                                 'original_kw': x, 'generated_kw': y,
                                                 'abs_diff_kw': delta})
    stats['historical_hours'] = count_orig
    stats['generated_hours'] = count_gen
    stats['tolerance_kw'] = tolerance_kw
    stats['max_household_annual_energy_diff_kwh'] = max(
        abs(x-y) for x, y in zip(stats['original_energy_kwh'], stats['generated_energy_kwh'])
    )
    if count_orig != max_expected_hours or count_gen != max_expected_hours:
        stats['status'] = 'LENGTH_MISMATCH'
    elif stats['timestamp_mismatches'] or stats['non_finite_or_missing_cells'] or stats['value_mismatches']:
        stats['status'] = 'NUMERIC_OR_TIMESTAMP_MISMATCH'
    else:
        stats['status'] = 'HOURLY_FIRST_20_PROFILES_MATCH_WITHIN_TOLERANCE'
    return stats


def repo_path(root: Path, candidate: Path) -> Path:
    location = (root / candidate).resolve()
    if not location.is_relative_to(root):
        raise ValueError('All source and output paths must remain within repository root')
    return location


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', default='.', help='Local repository root (default: current directory)')
    parser.add_argument('--historical', default=str(HISTORICAL_REL), help='Repo-relative original source CSV')
    parser.add_argument('--generated', default=str(GENERATED_REL), help='Repo-relative generated HOMER CSV')
    parser.add_argument('--out', help='Optional repo-relative JSON report path. Must not already exist.')
    args = parser.parse_args()
    root = Path(args.repo_root).expanduser().resolve()
    if not root.is_dir():
        parser.error(f'Not a directory: {root}')
    try:
        historical = repo_path(root, Path(args.historical))
        generated = repo_path(root, Path(args.generated))
        report_path = repo_path(root, Path(args.out)) if args.out else None
    except ValueError as exc:
        parser.error(str(exc))
    for p in (historical, generated):
        if not p.is_file():
            parser.error(f'Missing required source: {p}')
    if report_path:
        if report_path.exists():
            parser.error(f'Report already exists, choose a new output filename: {report_path}')
        if not report_path.parent.is_dir():
            parser.error(f'Report parent folder does not exist: {report_path.parent}')
    output = {
        'audit': 'READ_ONLY_HISTORICAL_PROFILE_SOURCE_AND_NUMERIC_COMPARISON',
        'utc_run': datetime.now(timezone.utc).isoformat(),
        'historical_file': str(historical),
        'generated_file': str(generated),
        'historical_byte_diagnostics': byte_diagnostics(historical, EXPECTED_ORIGINAL_SHA256),
        'generated_sha256': checksum(generated),
        'first_20_profile_comparison': compare_profiles(historical, generated),
        'source_files_modified': False,
    }
    byte_status = output['historical_byte_diagnostics']['status']
    numeric_status = output['first_20_profile_comparison']['status']
    output['interpretation'] = (
        'Archive source verified byte-identical' if byte_status == 'EXACT_BYTES' else
        'Only newline encoding differs from GitLab source' if byte_status == 'CRLF_ONLY' else
        'Only newline/BOM encoding differs from GitLab source' if byte_status == 'EOL_AND_UTF8_BOM_ONLY' else
        'Historical file byte difference not explained by newline/BOM conversion'
    )
    print('Historical original raw/normalized:', byte_status)
    print('Historical 20-profile numeric reproduction:', numeric_status)
    print('Maximum absolute household hourly difference (kW):',
          output['first_20_profile_comparison'].get('max_abs_diff_kw', 'N/A'))
    print('No source file was changed.')
    if report_path:
        with report_path.open('x', encoding='utf-8', newline='\n') as fp:
            json.dump(output, fp, indent=2, allow_nan=False)
            fp.write('\n')
        print('Wrote report:', report_path)
    else:
        print(json.dumps(output, indent=2, allow_nan=False))
    return 0 if numeric_status == 'HOURLY_FIRST_20_PROFILES_MATCH_WITHIN_TOLERANCE' else 2


if __name__ == '__main__':
    sys.exit(main())
