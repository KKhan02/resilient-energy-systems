from pathlib import Path
import csv
import hashlib
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import review_validation_queue as rq


def put_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_source_task_linkage_catches_collision():
    rows = [{'equipment_id': 'A', 'original_task_keys_json': '["k"]'},
            {'equipment_id': 'B', 'original_task_keys_json': '["k"]'}]
    with pytest.raises(rq.SourceError, match='two equipment'):
        rq.equipment_task_index(rows)


def test_anchor_audit_keeps_50_and_rejects_ac_with_missing_source(tmp_path):
    eq = []
    anchors = []
    for i in range(50):
        key = f'k{i}'
        eligible = i < 10
        eid = f'EC-{i:03d}'
        eq.append({'equipment_id': eid, 'original_task_keys_json': json.dumps([key]),
                   'existing_fixed_hardware_runner_eligible': str(eligible),
                   'transformer': '94022' if eligible else ''})
        anchors.append({'archived_task_key': key, 'equipment_id': eid,
                        'case': f'{5 + i%11}_homes', 'selection_reasons': 'min_cost',
                        'pv_panels': '17', 'battery_modules': '3', 'battery_power_dc_kw': '5',
                        'inverter_kva': '5', 'archived_annual_cost_usd': str(i+100),
                        'archived_self_sufficiency_pct': '75'})
    # Ensure uniqueness of (case, equipment_id) even when a case occurs again.
    put_csv(tmp_path / rq.EQUIPMENT, eq)
    put_csv(tmp_path / rq.ROUTING, anchors)
    ac = tmp_path / rq.AC / 'EC-000' / 'pf_0.98_service_1.00'
    ac.mkdir(parents=True)
    (ac / 'annual_ac_summary.json').write_text(json.dumps({
        'candidate_id': 'EC-000', 'load_pf': 0.98, 'service_factor': 1,
        'source_trajectory_sha256': 'other', 'hours_checked': 8760,
        'all_8760_evaluated': True, 'ac_feasible_full_year': True,
        'ac_violation_or_failure_hours': 0}))
    (ac / 'annual_ac_hours.csv').write_text('hour_index\n0\n')
    rows, summary = rq.audit(tmp_path, 'anchors')
    assert len(rows) == 50
    assert summary['GIS_eligible_count'] == 10
    found = {x['equipment_id']: x for x in rows}
    assert found['EC-000']['existing_epm_reference_ac_status'] == 'AC_RECORDED_BUT_LOCAL_SOURCE_TRAJECTORY_MISSING'
    assert found['EC-049']['existing_epm_reference_ac_status'] == 'NOT_APPLICABLE_NO_GIS_MEMBERSHIP'
    out = tmp_path / 'new_outputs'
    rq.export(out, rows, summary)
    assert len(list(csv.DictReader((out / 'candidate_validation_ledger.csv').open()))) == 50
    assert all('--execute' not in line for line in (out / 'existing_GIS_dry_run_commands.txt').read_text().splitlines() if line.startswith('python '))
    with pytest.raises(rq.SourceError, match='already exists'):
        rq.export(out, rows, summary)


def test_ac_pass_requires_matching_source_and_full_year(tmp_path):
    eid = 'EC-001'
    energy = tmp_path / 'energy'
    energy.mkdir()
    trace = energy / 'fixed_hardware_manufacturer_soc_baseline.csv'
    trace.write_text('hour,load_kw\n' + ''.join(f'{i},1.5\n' for i in range(8760)))
    source_hash = hashlib.sha256(trace.read_bytes()).hexdigest()
    (energy / 'pilot_manifest.json').write_text(json.dumps({
        'candidate_id': eid, 'source_trajectory_sha256': source_hash,
        'manufacturer_min_soc_fraction': 0.2}))
    status, h = rq.load_local_energy(energy, eid)
    assert status == 'LOCAL_TRAJECTORY_HASH_VERIFIED_8760'
    assert h == source_hash
    ac = tmp_path / 'ac' / eid / 'pf_0.98_service_1.00'
    ac.mkdir(parents=True)
    (ac / 'annual_ac_hours.csv').write_text('hour_index\n' + ''.join(f'{i}\n' for i in range(8760)))
    (ac / 'annual_ac_summary.json').write_text(json.dumps({
        'candidate_id': eid, 'load_pf': 0.98, 'service_factor': 1.0,
        'hours_checked': 8760, 'all_8760_evaluated': True,
        'source_trajectory_sha256': source_hash, 'field_certified': False,
        'ac_feasible_full_year': True, 'ac_violation_or_failure_hours': 0}))
    (ac / 'ac_checkpoint.json').write_text('{"status":"COMPLETE"}')
    assert rq.load_local_ac(tmp_path / 'ac', eid, h)[0] == 'CONDITIONAL_ANNUAL_AC_PASS_PROVENANCE_MATCHED'
    assert rq.load_local_ac(tmp_path / 'ac', eid, 'wrong')[0] == 'AC_SOURCE_TRAJECTORY_HASH_MISMATCH'
    trace.write_text('hour,load_kw\n0,1.5\n')
    assert rq.load_local_energy(energy, eid)[0] == 'ENERGY_HASH_MISMATCH'


def test_all_scope_retains_all_tiers_and_no_arbitrary_six_design_limit(tmp_path):
    eq = []
    pool = []
    names = ['A_DEFINED_TARGET_ANCHOR']*50 + ['B_FULL_SAMPLED_PARETO_POOL']*337 + [
        'C_HARDWARE_TRANSITION_EXPANSION']*247 + ['D_OTHER_ARCHIVED_HARDWARE']*621
    assert len(names) == 1255
    for i, t in enumerate(names):
        eq.append({'original_task_keys_json': json.dumps([str(i)]),
                   'equipment_id': f'EC-{i}', 'existing_fixed_hardware_runner_eligible': 'False',
                   'transformer': ''})
        pool.append({'task_key': str(i), 'case': f'{5 + i%11}_homes',
                     'selection_tier': t, 'anchor_reasons': '', 'pv_panels': '17',
                     'battery_modules': '3', 'battery_power_dc_kw': '5',
                     'inverter_kva': '5', 'annual_total_usd': str(i + 1),
                     'self_sufficiency_pct': '80'})
    put_csv(tmp_path / rq.EQUIPMENT, eq)
    put_csv(tmp_path / rq.POOL, pool)
    rows, summary = rq.audit(tmp_path, 'all')
    assert len(rows) == 1255
    assert summary['tier_counts']['A_DEFINED_TARGET_ANCHOR'] == 50
    assert summary['tier_counts']['B_FULL_SAMPLED_PARETO_POOL'] == 337
    assert summary['tier_counts']['C_HARDWARE_TRANSITION_EXPANSION'] == 247
    assert summary['tier_counts']['D_OTHER_ARCHIVED_HARDWARE'] == 621
