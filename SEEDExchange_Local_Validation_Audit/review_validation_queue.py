#!/usr/bin/env python3
"""Read-only SEEDExchange WP1 candidate/AC provenance audit.

Runs offline against an existing local checkout. Does NOT run optimization,
pandapower, change the repository, invent feeder networks, or accept archived
energy-only costs as network-feasible results.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path('case1/studies')
POOL = BASE / 'household_frontier_reuse_v1/outputs/archived_hardware_pool_5kva.csv'
ROUTING = BASE / 'household_frontier_reuse_v1/outputs/stage_a_50_network_routing.csv'
EQUIPMENT = BASE / 'ac_aware_redispatch_v1/outputs/campaign_reuse_index_v18_01/all_distinct_equipment_candidates.csv'
ENERGY = BASE / 'ac_aware_redispatch_v1/outputs/campaign_manufacturer_01'
AC = BASE / 'ac_aware_redispatch_v1/outputs/campaign_AC_01'


class SourceError(ValueError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SourceError(f'Required source not found: {path}')
    with path.open('r', newline='', encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def rows_count(path: Path) -> int:
    with path.open('r', newline='', encoding='utf-8-sig') as f:
        return sum(1 for _ in csv.reader(f)) - 1


def equipment_task_index(equipment: list[dict]) -> dict[str, dict]:
    indexed = {}
    for row in equipment:
        try:
            keys = json.loads(row['original_task_keys_json'])
        except (KeyError, json.JSONDecodeError) as exc:
            raise SourceError(f'Corrupt task key list: {row.get("equipment_id")}') from exc
        for key in keys:
            if key in indexed and indexed[key]['equipment_id'] != row['equipment_id']:
                raise SourceError(f'Original task key assigned to two equipment IDs: {key}')
            indexed[key] = row
    return indexed


def normalize_anchor(row: dict, equipment_by_task: dict[str, dict]) -> dict:
    key = row['archived_task_key']
    candidate = equipment_by_task.get(key)
    if candidate is None or candidate['equipment_id'] != row['equipment_id']:
        raise SourceError(f'Stage A routing source key mismatch: {key}')
    return {
        'case': row['case'], 'selection_tier': 'A_DEFINED_TARGET_ANCHOR',
        'selection_reasons': row['selection_reasons'], 'task_key': key,
        'equipment_id': candidate['equipment_id'], 'pv_panels': row['pv_panels'],
        'battery_modules': row['battery_modules'], 'battery_power_dc_kw': row['battery_power_dc_kw'],
        'inverter_kva': row['inverter_kva'], 'archived_annual_cost_usd': row['archived_annual_cost_usd'],
        'archived_self_sufficiency_pct': row['archived_self_sufficiency_pct'],
        'gis_runner_eligible': candidate['existing_fixed_hardware_runner_eligible'].lower() == 'true',
        'epm_transformer': candidate['transformer'],
    }


def normalize_pool(row: dict, equipment_by_task: dict[str, dict]) -> dict:
    key = row['task_key']
    candidate = equipment_by_task.get(key)
    if candidate is None:
        raise SourceError(f'No archived fixed hardware for task: {key}')
    return {
        'case': row['case'], 'selection_tier': row['selection_tier'],
        'selection_reasons': row['anchor_reasons'], 'task_key': key,
        'equipment_id': candidate['equipment_id'], 'pv_panels': row['pv_panels'],
        'battery_modules': row['battery_modules'], 'battery_power_dc_kw': row['battery_power_dc_kw'],
        'inverter_kva': row['inverter_kva'], 'archived_annual_cost_usd': row['annual_total_usd'],
        'archived_self_sufficiency_pct': row['self_sufficiency_pct'],
        'gis_runner_eligible': candidate['existing_fixed_hardware_runner_eligible'].lower() == 'true',
        'epm_transformer': candidate['transformer'],
    }


def load_local_energy(energy_dir: Path, eid: str) -> tuple[str, str | None]:
    meta_file = energy_dir / 'pilot_manifest.json'
    trajectory = energy_dir / 'fixed_hardware_manufacturer_soc_baseline.csv'
    if not energy_dir.exists():
        return 'NOT_IN_LOCAL_CHECKOUT', None
    if not meta_file.is_file() or not trajectory.is_file():
        return 'INCOMPLETE_LOCAL_ENERGY', None
    try:
        meta = json.loads(meta_file.read_text(encoding='utf-8'))
        expected = meta.get('source_trajectory_sha256')
        if meta.get('candidate_id') != eid or not expected:
            return 'ENERGY_ID_OR_PROVENANCE_MISMATCH', None
        if digest(trajectory) != expected:
            return 'ENERGY_HASH_MISMATCH', None
        if rows_count(trajectory) != 8760:
            return 'ENERGY_NOT_8760_ROWS', None
        if meta.get('manufacturer_min_soc_fraction') is not None and abs(float(meta['manufacturer_min_soc_fraction']) - 0.20) > 1e-8:
            return 'ENERGY_SOC_ASSUMPTION_DIFFERENT', None
        return 'LOCAL_TRAJECTORY_HASH_VERIFIED_8760', expected
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return f'ENERGY_READ_ERROR_{type(exc).__name__}', None


def load_local_ac(ac_dir: Path, eid: str, trajectory_hash: str | None,
                  pf: float = 0.98, service: float = 1.0) -> tuple[str, str]:
    case = ac_dir / eid / f'pf_{pf:.2f}_service_{service:.2f}'
    summary_file = case / 'annual_ac_summary.json'
    hourly_file = case / 'annual_ac_hours.csv'
    checkpoint = case / 'ac_checkpoint.json'
    if not case.exists():
        return 'NOT_IN_LOCAL_CHECKOUT', ''
    if not summary_file.is_file() or not hourly_file.is_file():
        return 'INCOMPLETE_AC_OUTPUT', ''
    try:
        summ = json.loads(summary_file.read_text(encoding='utf-8'))
        if (summ.get('candidate_id') != eid or
            abs(float(summ.get('load_pf', -1)) - pf) > 1e-8 or
            abs(float(summ.get('service_factor', -1)) - service) > 1e-8):
            return 'AC_ID_OR_SCENARIO_MISMATCH', ''
        if not trajectory_hash:
            return 'AC_RECORDED_BUT_LOCAL_SOURCE_TRAJECTORY_MISSING', ''
        if summ.get('source_trajectory_sha256') != trajectory_hash:
            return 'AC_SOURCE_TRAJECTORY_HASH_MISMATCH', ''
        if (int(summ.get('hours_checked', 0)) != 8760 or
            summ.get('all_8760_evaluated') is not True or rows_count(hourly_file) != 8760):
            return 'AC_NOT_FULL_YEAR', ''
        if checkpoint.is_file():
            ch = json.loads(checkpoint.read_text(encoding='utf-8'))
            if ch.get('status') != 'COMPLETE':
                return 'AC_CHECKPOINT_NOT_COMPLETE', ''
        if summ.get('field_certified') is True:
            return 'AC_UNEXPECTED_FIELD_CERTIFICATION_FLAG', ''
        if summ.get('ac_feasible_full_year') is True and int(summ.get('ac_violation_or_failure_hours', -1)) == 0:
            status = 'CONDITIONAL_ANNUAL_AC_PASS_PROVENANCE_MATCHED'
        else:
            status = 'CONDITIONAL_ANNUAL_AC_FAIL_OR_UNRESOLVED'
        return status, str(summ.get('ac_violation_or_failure_hours', ''))
    except (ValueError, OSError, TypeError) as exc:
        return f'AC_READ_ERROR_{type(exc).__name__}', ''


def audit(repo: Path, scope: str) -> tuple[list[dict], dict]:
    equipment = read_csv(repo / EQUIPMENT)
    index = equipment_task_index(equipment)
    if scope == 'anchors':
        source = read_csv(repo / ROUTING)
        candidates = [normalize_anchor(x, index) for x in source]
    else:
        source = read_csv(repo / POOL)
        candidates = [normalize_pool(x, index) for x in source]
    if len({(x['case'], x['equipment_id']) for x in candidates}) != len(candidates):
        raise SourceError('Duplicated equipment ID within a household case')
    if scope == 'anchors' and len(candidates) != 50:
        raise SourceError(f'Expected 50 selected Stage A designs, found {len(candidates)}')
    if scope == 'all' and len(candidates) != 1255:
        raise SourceError(f'Expected 1255 archived 5 kVA designs, found {len(candidates)}')
    for row in candidates:
        e_dir = repo / ENERGY / row['equipment_id']
        energy_status, hash_value = load_local_energy(e_dir, row['equipment_id'])
        row['manufacturer_SOC_status'] = energy_status
        row['source_trajectory_sha256_verified'] = hash_value or ''
        row['existing_epm_network_state'] = ('GIS_MODEL_ELIGIBLE_PROVISIONAL' if row['gis_runner_eligible']
                                              else 'NO_APPROVED_EXISTING_GIS_MEMBERSHIP')
        if row['gis_runner_eligible']:
            ac_status, ac_failed = load_local_ac(repo / AC, row['equipment_id'], hash_value)
        else:
            ac_status, ac_failed = 'NOT_APPLICABLE_NO_GIS_MEMBERSHIP', ''
        row['existing_epm_reference_ac_status'] = ac_status
        row['existing_epm_reference_ac_failed_hours'] = ac_failed
        row['proposed_generic_LV_AC_status'] = 'NOT_RUN_TOPOLOGY_NOT_DECIDED'
        row['proposed_site_A_AC_status'] = 'NOT_RUN_CONNECTION_LAYOUT_NOT_DECIDED'
    rank = {'A_DEFINED_TARGET_ANCHOR': 0, 'B_FULL_SAMPLED_PARETO_POOL': 1,
            'C_HARDWARE_TRANSITION_EXPANSION': 2, 'D_OTHER_ARCHIVED_HARDWARE': 3}
    candidates.sort(key=lambda x: (rank.get(x['selection_tier'], 9), int(x['case'].split('_')[0]),
                                   x['case'], float(x['archived_annual_cost_usd']), x['equipment_id']))
    tier = Counter(x['selection_tier'] for x in candidates)
    e_status = Counter(x['manufacturer_SOC_status'] for x in candidates)
    ac_status = Counter(x['existing_epm_reference_ac_status'] for x in candidates)
    by_case = defaultdict(lambda: {'designs': 0, 'GIS_eligible': 0})
    for row in candidates:
        by_case[row['case']]['designs'] += 1
        by_case[row['case']]['GIS_eligible'] += int(row['gis_runner_eligible'])
    summary = {
        'status': 'READ_ONLY_LOCAL_PROVENANCE_AUDIT_NO_NEW_OPTIMIZATION_OR_AC',
        'scope': scope, 'candidate_count': len(candidates), 'tier_counts': dict(tier),
        'GIS_eligible_count': sum(int(x['gis_runner_eligible']) for x in candidates),
        'manufacturer_SOC_status_counts': dict(e_status),
        'existing_EPM_reference_AC_status_counts': dict(ac_status),
        'by_household_case': dict(by_case),
        'source_files_sha256': {
            str(EQUIPMENT): digest(repo / EQUIPMENT),
            str(ROUTING if scope == 'anchors' else POOL): digest(repo / (ROUTING if scope == 'anchors' else POOL)),
        },
        'network_comparisons': {
            'A_existing_EPM_GIS': 'Only cases with eligible provisional GIS memberships; preserve other cases',
            'B_new_generic_LV': 'Topology, phase and feeder geometry unresolved. No AC results claimed',
            'C_Site_A': 'Separate shared PV BESS clearing-based connection study. No new transformer presumed',
        },
        'fixed_PF_references': [0.95, 0.98, 1.0], 'optional_stress_PF': 0.90,
        'source_plant_sizing_recomputed': 0, 'AC_simulations_performed': 0,
    }
    return candidates, summary


def export(outdir: Path, rows: list[dict], summary: dict) -> None:
    if outdir.exists():
        raise SourceError(f'Output directory already exists. Choose a fresh folder: {outdir}')
    outdir.mkdir(parents=True)
    with (outdir / 'candidate_validation_ledger.csv').open('w', encoding='utf-8', newline='') as f:
        dw = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        dw.writeheader()
        dw.writerows(rows)
    (outdir / 'validation_audit_summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    eligible = [x for x in rows if x['gis_runner_eligible']]
    lines = [
        '# Existing GIS annual run commands: REVIEW BEFORE EXECUTION',
        '# Default commands dry-run. They do NOT execute simulation without --execute.',
        '# These are only eligible provisional GIS scenarios. No new LV feeder is assumed.',
        '# Check git status, active local jobs and existing immutable outputs first.',
        '']
    for r in eligible:
        root = 'case1/studies/ac_aware_redispatch_v1/outputs/'
        common = ('python case1/studies/ac_aware_redispatch_v1/batch_archived_campaign.py'
                  ' --repo-root .'
                  f' --plan-dir {root}campaign_reuse_index_v18_01'
                  f' --energy-root {root}campaign_manufacturer_01'
                  f' --ac-root {root}campaign_AC_01'
                  f' --candidate-id {r["equipment_id"]}')
        lines.append(f'# {r["case"]}, {r["pv_panels"]} PV, {r["battery_modules"]} batteries, {r["inverter_kva"]} kVA inverter')
        lines.append(common + ' --stage energy')
        lines.append(common + ' --stage ac --scenario-set principal')
        lines.append('')
    (outdir / 'existing_GIS_dry_run_commands.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root', type=Path, required=True, help='Existing complete GitLab checkout')
    ap.add_argument('--output-dir', type=Path, required=True, help='New output directory, preferably outside repository')
    ap.add_argument('--scope', choices=['anchors', 'all'], default='anchors',
                    help='anchors: initial 50; all: complete 1255-design 5 kVA equipment archive')
    args = ap.parse_args(argv)
    try:
        rows, summary = audit(args.repo_root.resolve(), args.scope)
        export(args.output_dir.resolve(), rows, summary)
    except (SourceError, ValueError) as exc:
        ap.error(str(exc))
    print(json.dumps({'written_to': str(args.output_dir.resolve()), **summary}, indent=2))


if __name__ == '__main__':
    main()
