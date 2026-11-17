#!/usr/bin/env python3
"""LOCAL-ONLY Study A A0/A1 household-specific inputs, fixed-hardware energy, AC replay.

This is not the archived 7/9/12 equal-load runner. Does not write GitLab or
modify original model/data. Each numerical stage requires explicit CLI invocation.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import pandas as pd

EXPECTED_COUNTS = {
    'A0': {'94022': 10, '106039': 12, '113699': 4, '85398': 4, '92395': 4, '98380': 1},
    'A1': {'94022': 8, '106039': 11, '113699': 6, '85398': 5, '92395': 4, '98380': 1},
}
ELIGIBLE = {'94022', '106039', '113699', '85398'}
RATINGS = {'94022': 5.0, '106039': 5.0, '113699': 3.0, '85398': 5.0, '92395': 5.0, '98380': 3.0}
# The A1 assignment is NEAREST TRANSFORMER POSITION among the SIX original
# v4 EPM territories. It does NOT search for the nearest LV line to choose
# transformer ownership. Additional 113306 is screened separately and is not
# silently added to the controlled A0/A1 comparison.
ASSIGNMENT_POLICY = {'A0': 'source_association', 'A1': 'nearest_transformer_position_six_territories'}
# Historical v4 source evidence is used as a regression expectation, never
# as an instruction to hard-code household reassignment.
A1_MOVE_TARGETS = {'H03': '113699', 'H06': '113699', 'H13': '85398'}
EXPECTED_CHANGE = set(A1_MOVE_TARGETS)
ROOT = Path(__file__).resolve().parent
# Explicit source-selected starting references, not optimized for the new cohorts.
# Four-home proxies borrow an archived five-home tuple only as a first engineering stress test.
ANCHORS = {
    ('A0', '94022'): ('EC-15b88923cb73d21f1a36', 34, 6, 9.433197111218815, 10.0, 'ARCHIVED_MIN_COST_REFERENCE'),
    ('A1', '94022'): ('EC-6d76adf92550edae4988', 27, 5, 8.610383666211986, 8.0, 'ARCHIVED_8_SYNTHETIC_H01_VARIANT_REFERENCE'),
    ('A0', '106039'): ('EC-84f6a468f79bf545e863', 41, 8, 12.0, 12.0, 'ARCHIVED_MIN_COST_REFERENCE'),
    ('A1', '106039'): ('EC-2913bea9aef249adbc44', 41, 8, 12.0, 12.0, 'ARCHIVED_MIN_COST_REFERENCE'),
    ('A0', '113699'): ('EC-18f85cfb1c7c7d0d19a2', 17, 3, 5.386094220839077, 5.0, 'BORROWED_5_HOME_PROXY_4_HOME_NOT_OPTIMAL'),
    ('A1', '113699'): ('EC-37a59c6f9e0dea1b3fbc', 20, 4, 6.439699033049508, 6.0, 'ARCHIVED_5KVA_REF_ON_3KVA_TRAFO'),
    ('A0', '85398'): ('EC-18f85cfb1c7c7d0d19a2', 17, 3, 5.386094220839077, 5.0, 'BORROWED_5_HOME_PROXY_4_HOME_NOT_OPTIMAL'),
    ('A1', '85398'): ('EC-18f85cfb1c7c7d0d19a2', 17, 3, 5.386094220839077, 5.0, 'ARCHIVED_MIN_COST_REFERENCE'),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def new_output(path):
    path = Path(path).resolve()
    if path.exists():
        raise ValueError(f'Refusing to overwrite existing path: {path}')
    if not path.parent.exists():
        raise ValueError(f'Create output parent before running: {path.parent}')
    return path


def dump(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False, default=str) + '\n', encoding='utf-8')


def repo_modules(repo):
    epm = repo / 'case1/studies/epm_gis_pandapower_v1'
    ac = repo / 'case1/studies/ac_aware_redispatch_v1'
    pypsa = repo / 'case1/studies/pypsa_joint_optimization_v1'
    for p, file in [(epm, 'epm_topology.py'), (epm, 'run_epm_validation.py'),
                    (ac, 'fixed_hardware.py'), (pypsa, 'model.py')]:
        if not (p / file).is_file():
            raise FileNotFoundError(f'Missing existing original repo module: {p / file}')
    for p in (epm, ac, pypsa):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    from epm_topology import read_data, infer_assignments, build_territory, Territory
    return read_data, infer_assignments, build_territory, Territory


def recognize_column(names, candidates, kind):
    found = [name for name in names if name.lower().strip() in candidates]
    if len(found) != 1:
        raise ValueError(f'{kind}: expected exactly one of {sorted(candidates)}, got {found}. Available: {list(names)}')
    return found[0]


def load_house_map(path):
    table = pd.read_csv(path, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    house = recognize_column(table.columns, {'house_id', 'house', 'household_id', 'mapped_house_id', 'property_id'}, 'house ID')
    index = recognize_column(table.columns, {'profile_index', 'profile_id', 'profile_number', 'source_profile_index', 'assigned_profile_index', 'profile_idx'}, 'profile index')
    pairs = {}
    for _, row in table.iterrows():
        hid = str(row[house]).strip().upper()
        if not re.fullmatch(r'H\d{2}', hid) or hid in pairs:
            raise ValueError(f'Invalid or duplicate mapped house: {hid}')
        raw = str(row[index]).strip()
        m = re.fullmatch(r'(?:house|profile|load|h)[_ -]*0*(\d+)(?:_kw)?', raw, re.I)
        try:
            number = int(m.group(1) if m else raw)
        except ValueError as e:
            raise ValueError(f'Invalid source profile index {raw} for {hid}') from e
        if number < 1 or number > 35:
            raise ValueError(f'Out-of-bounds profile {number} for {hid}')
        pairs[hid] = number
    if len(pairs) != 35 or set(pairs.values()) != set(range(1, 36)):
        raise ValueError('Mapping must contain 35 unique house IDs and each profile 1..35 once')
    return pairs


def profile_number(column):
    key = column.strip().lower()
    for pat in (r'(?:house|profile|load)[_ -]*0*(\d+)(?:_kw)?',
                r'h[_ -]*0*(\d+)(?:_kw)?', r'(?:p|kw)[_ -]*0*(\d+)'):
        matched = re.fullmatch(pat, key)
        if matched:
            return int(matched.group(1))
    return None


def load_profiles(path):
    frame = pd.read_csv(path, encoding='utf-8-sig')
    stamp = recognize_column(frame.columns,
        {'timestamp_lst', 'timestamp', 'datetime', 'date_time', 'date', 'time'}, 'hourly timestamp')
    parsed = pd.to_datetime(frame[stamp], errors='coerce')
    expected = pd.date_range('2025-01-01', periods=8760, freq='h')
    if len(frame) != 8760 or parsed.isna().any() or not pd.DatetimeIndex(parsed).equals(expected):
        raise ValueError('Require 8760 exact chronological local-standard-time 2025 hours')
    columns = {}
    for column in frame.columns:
        if column == stamp:
            continue
        n = profile_number(column)
        if n is None:
            continue
        if n in columns:
            raise ValueError(f'Ambiguous duplicate profile index {n}: {columns[n]}, {column}')
        columns[n] = column
    if set(columns) != set(range(1, 36)):
        raise ValueError('Expected 35 recognizable profile columns (house_1_kw, profile_01, H01, etc). '
                         f'Found profile indices: {sorted(columns)}; columns: {list(frame.columns)}')
    # Use arrays to avoid inadvertent pandas label alignment with the new timestamp index.
    data = pd.DataFrame({i: pd.to_numeric(frame[columns[i]], errors='coerce').to_numpy(float)
                         for i in range(1, 36)}, index=expected)
    if not np.isfinite(data.to_numpy()).all() or (data.to_numpy() < -1e-12).any():
        raise ValueError('Missing, non-finite or negative household loads')
    totals = data.sum(axis=0)
    if not np.allclose(totals.to_numpy(), 1898., rtol=0, atol=.01):
        raise ValueError(f'Household energy is not 1898 kWh each: min {totals.min()}, max {totals.max()}')
    if abs(float(data.to_numpy().sum()) - 66430.) > .1:
        raise ValueError('Not 66430 kWh annual 35-house demand')
    return data


def transformer_distance_ranking(house, trafos):
    """Rank original EPM transformer POSITIONS, not mapped LV-line geometry.

    x/y must come from the original WGS84 -> UTM 18N source projection in
    epm_topology.read_data(). This is a *proximity hypothesis*, not evidence
    of connected customers, spare nameplate, phases or protection.
    """
    if set(trafos) != set(RATINGS):
        raise ValueError('A0/A1 requires the original SIX EPM transformer territories; '
                         'additional 113306 is a separate proposed sensitivity, not an automatic move')
    px, py = float(house['x']), float(house['y'])
    if not all(map(math.isfinite, (px, py))):
        raise ValueError('Invalid projected house coordinate')
    distances = []
    for tid, trafo in trafos.items():
        tx,ty = float(trafo['x']),float(trafo['y'])
        if not all(map(math.isfinite,(tx,ty))):
            raise ValueError(f'Invalid transformer position: {tid}')
        distances.append((str(tid),float(math.hypot(tx-px,ty-py))))
    return sorted(distances, key=lambda item: (item[1],item[0]))


def resolve_v4_assignments(houses, trafos, lv, infer, variant):
    """Source A0 vs transformer-POSITION nearest A1, with separate LV tap stage.

    A0 retains source household -> transformer associations. For A1 the
    selected transformer is determined ONLY by house-to-transformer projected
    distance over the six historical territories. Missing LV sections do NOT
    disqualify a transformer or imply no LV service exists. Once selected,
    house service attachment for an AC-eligible territory is a DISTINCT,
    provisional inference to an LV segment belonging to that transformer.
    No LV geometry means AC replay is currently blocked, not that the house
    must be moved to another transformer.
    """
    if variant not in EXPECTED_COUNTS:
        raise ValueError(f'Unknown Study A assignment variant: {variant}')
    original = infer(houses, trafos, lv, 'base')
    if len(original) != len(houses) or len(set(a['house'] for a in original)) != len(houses):
        raise ValueError('Original EPM source assignment is missing or duplicating houses')
    if variant == 'A0':
        return original
    from shapely.geometry import Point
    # Compute transformer membership FIRST; LV taps are not consulted at this stage.
    nearest = {hid: transformer_distance_ranking(h, trafos) for hid,h in houses.items()}
    movements = {hid: ranking[0][0] for hid,ranking in nearest.items()
                 if ranking[0][0] != str(next(a['transformer'] for a in original if a['house']==hid))}
    if movements != A1_MOVE_TARGETS:
        raise ValueError(f'Historical six-transformer proximity outcome changed: {movements}. '
                         'Do not force old counts or silently assign households.')
    updated=[]
    for source in original:
        record=dict(source)
        hid=record['house']
        target, nearest_dist_m = nearest[hid][0]
        if target != str(source['transformer']):
            # AC geometry only, AFTER transformer was selected by proximity.
            node=str(trafos[target]['epm_node'])
            candidates=[seg for seg in lv if str(seg['node']) == node]
            if not candidates:
                raise ValueError(f'Cannot create provisional AC LV tap for selected transformer '
                                 f'{target}, house {hid}; this is missing GIS geometry, '
                                 'not evidence of absent electrical service')
            pt=Point(float(houses[hid]['x']),float(houses[hid]['y']))
            candidate=min(candidates,key=lambda seg: (pt.distance(seg['geom']),str(seg['fid'])))
            tap_dist_m=float(pt.distance(candidate['geom']))
            if not math.isfinite(tap_dist_m) or tap_dist_m<0:
                raise ValueError(f'Invalid inferred LV tap geometry for {hid}')
            record.update(transformer=target,segment_id=str(candidate['fid']),
                          gis_proximity_m=round(tap_dist_m,2),changed=True,
                          status='PROVISIONAL_TRANSFORMER_NEAREST_LV_TAP_GEOMETRY',
                          nearest_transformer_distance_m=round(nearest_dist_m,2),
                          next_transformer=str(nearest[hid][1][0]),
                          next_transformer_distance_m=round(nearest[hid][1][1],2))
        updated.append(record)
    return updated


def all_memberships(repo, mapping):
    read_data, infer, _, _ = repo_modules(repo)
    houses, trafos, lv = read_data()
    if set(mapping) != set(houses):
        raise ValueError(f'Mapped houses differ from EPM GIS houses: missing {sorted(set(houses)-set(mapping))}, extra {sorted(set(mapping)-set(houses))}')
    groups = {}
    allocations = {}
    for variant in ASSIGNMENT_POLICY:
        ass = resolve_v4_assignments(houses, trafos, lv, infer, variant)
        by_house = {row['house']: row for row in ass}
        if len(ass) != len(houses) or set(by_house) != set(houses):
            raise ValueError('GIS assignment did not account for 35 unique households')
        group = {t: sorted([hid for hid, rec in by_house.items() if str(rec['transformer']) == t])
                 for t in EXPECTED_COUNTS[variant]}
        counts = {t: len(v) for t, v in group.items()}
        if counts != EXPECTED_COUNTS[variant] or sum(map(len, group.values())) != 35:
            raise ValueError(f'{variant}: incorrect provisional cohort assignment {counts}')
        groups[variant] = group
        allocations[variant] = by_house
    actual_moves = {hid: str(allocations['A1'][hid]['transformer'])
                    for hid in houses if allocations['A0'][hid]['transformer'] != allocations['A1'][hid]['transformer']}
    if actual_moves != A1_MOVE_TARGETS:
        raise ValueError(f'Unexpected A0->A1 transformer moves: {actual_moves}, expected {A1_MOVE_TARGETS}')
    for hid in set(houses)-EXPECTED_CHANGE:
        orig, updated = allocations['A0'][hid], allocations['A1'][hid]
        if (orig['transformer'], orig['segment_id']) != (updated['transformer'], updated['segment_id']):
            raise ValueError(f'Unapproved transformer or LV tap changed for {hid}')
    return groups, allocations

def validated_sources(repo, input_dir, want_manifest=None):
    mapping_path = input_dir / 'fixed_house_to_profile_map.csv'
    profiles_path = input_dir / 'household_profiles_2025_excel_35.csv'
    for p in (mapping_path, profiles_path):
        if not p.is_file():
            raise FileNotFoundError(f'Required v4 run_02 input not present: {p}')
    if want_manifest is not None:
        for p, key in ((mapping_path, 'mapping_sha256'), (profiles_path, 'profiles_sha256')):
            if sha(p) != want_manifest[key]:
                raise ValueError(f'Source input hash changed after manifest preparation: {p}')
    mapping = load_house_map(mapping_path)
    profiles = load_profiles(profiles_path)
    groups, assignments = all_memberships(repo, mapping)
    return mapping_path, profiles_path, mapping, profiles, groups, assignments


def command_prepare(args):
    repo = args.repo_root.resolve(); inp = args.v4_run_dir.resolve()
    if not (repo / '.git').exists():
        raise ValueError('Require full local GitLab checkout for provenance')
    mp, pp, mapping, profiles, groups, allocations = validated_sources(repo, inp)
    manifest_path = new_output(args.out)
    source = repo / 'case1/studies/epm_gis_pandapower_v1/data/epm_network_relevant_sanitized.geojson'
    associated = repo / 'case1/studies/epm_gis_pandapower_v1/data/houses_candidate_associations.csv'
    _read,_,_,_ = repo_modules(repo)
    _houses,_trafos,_ = _read()
    proximity_audit = {hid: [{'transformer':t,'distance_m':round(d,2)}
                   for t,d in transformer_distance_ranking(h,_trafos)]
                   for hid,h in _houses.items()}
    payload = {
        'status': 'PREPARED_INPUTS_NO_ANNUAL_ENERGY_OR_AC_RUN', 'study': 'A', 'source_assumptions': 'A0 original associations; A1 closest transformer positions among six source EPM territories. LV geometry used ONLY for provisional AC taps; 113306 separate sensitivity.',
        'repo_root': str(repo), 'v4_run_dir': str(inp), 'mapping_sha256': sha(mp), 'profiles_sha256': sha(pp),
        'gis_geojson_sha256': sha(source), 'gis_house_sha256': sha(associated),
        'script_sha256': sha(Path(__file__)),
        'model_source_hashes': {name:sha(repo/name) for name in [
             'case1/studies/ac_aware_redispatch_v1/fixed_hardware.py',
             'case1/studies/pypsa_joint_optimization_v1/model.py',
             'case1/studies/epm_gis_pandapower_v1/run_epm_validation.py',
             'case1/studies/epm_gis_pandapower_v1/epm_topology.py',
             'case1/studies/epm_gis_pandapower_v1/hil_voltvar.py',
             'case1/studies/epm_gis_pandapower_v1/coordinated_q_control.py']},
        '2025_hours': len(profiles),
        'population_houses': len(mapping), 'population_annual_kwh': float(profiles.to_numpy().sum()),
        'transformer_selection_policy': ASSIGNMENT_POLICY,
        'source_transformer_proximity_m': proximity_audit,
        'mapping': mapping, 'groups': groups,
        'changed_houses': {hid: {'from': allocations['A0'][hid]['transformer'],
                                  'to': allocations['A1'][hid]['transformer'],
                                  'target_segment_id': allocations['A1'][hid]['segment_id'],
                                  'target_service_straight_line_m': allocations['A1'][hid]['gis_proximity_m'],
                                  'evidence': 'v4 provisional cohort move; not a field-verified cable'}
                          for hid in sorted(EXPECTED_CHANGE)},
        'AC_graph_blocked_transformer_missing_extracted_LV_sections_not_service_absent': '92395', 'support_only_transformer': '98380',
        'technology_basis': 'archived hardware anchor for NEW cohort, economic results not transferable',
        'nameplate_assumptions_kva': RATINGS, 'physical_service_status': 'PROVISIONAL_UNSURVEYED',
        'git_head_local': subprocess.run(['git','rev-parse','HEAD'],cwd=repo,capture_output=True,text=True).stdout.strip(),
    }
    dump(manifest_path, payload)
    print(json.dumps({'status': payload['status'], 'manifest': str(manifest_path),
                      'groups': {k: {t: len(ids) for t, ids in v.items()} for k, v in groups.items()}}, indent=2))


def data_for_case(args):
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['status'] != 'PREPARED_INPUTS_NO_ANNUAL_ENERGY_OR_AC_RUN':
        raise ValueError('Wrong input manifest state')
    repo = Path(manifest['repo_root']); inp = Path(manifest['v4_run_dir'])
    if sha(Path(__file__)) != manifest['script_sha256']:
        raise ValueError('Local Study A v6 runner changed after input manifest preparation')
    for filename, expected in manifest.get('model_source_hashes',{}).items():
        if sha(repo/filename)!=expected:
            raise ValueError(f'Original model source changed since v6 input preparation: {filename}')
    _, _, mapping, profiles, groups, _ = validated_sources(repo, inp, manifest)
    for src, key in [('epm_network_relevant_sanitized.geojson','gis_geojson_sha256'),
                      ('houses_candidate_associations.csv','gis_house_sha256')]:
        p = repo/'case1/studies/epm_gis_pandapower_v1/data'/src
        if sha(p) != manifest[key]:
            raise ValueError(f'EPM GIS source changed since preparation: {p}')
    if groups != manifest['groups'] or mapping != manifest['mapping']:
        raise ValueError('GIS assignment/profile mapping changed since preflight')
    variant = args.assignment
    trafo = args.transformer
    if trafo not in ELIGIBLE:
        raise ValueError(f'Transformer {trafo} is not AC eligible in this runner. 92395 lacks extracted LV graph (service not disproven); 98380 support only; north excluded.')
    house_ids = groups[variant][trafo]
    trace = pd.DataFrame({hid: profiles[mapping[hid]].to_numpy() for hid in house_ids}, index=profiles.index)
    if abs(float(trace.to_numpy().sum())-len(house_ids)*1898)>0.1:
        raise ValueError('Selected cohort demand no longer matches its declared annual energy')
    return repo, manifest, house_ids, trace


def archived_hardware_selection(repo, variant, trafo, tier):
    """Return source hardware only; archived cost and SS NEVER transfer to new loads."""
    key=(variant,trafo)
    if key not in ANCHORS:raise ValueError('No cohort hardware reference')
    if tier=='min_cost':
        source_id,panels,modules,bat_power,kva_inv,provenance=ANCHORS[key]
        return source_id,panels,modules,bat_power,kva_inv,provenance
    if tier!='ss90':raise ValueError('Unrecognized hardware selection tier')
    count=EXPECTED_COUNTS[variant][trafo]
    source_case='5_homes' if count==4 else ('8_homes_H01' if count==8 else f'{count}_homes')
    table=repo/'case1/studies/household_frontier_reuse_v1/outputs/stage_a_50_network_routing.csv'
    if not table.is_file():raise FileNotFoundError(f'Archived equipment source missing: {table}')
    refs=pd.read_csv(table,low_memory=False)
    needed={'case','equipment_id','selection_reasons','pv_panels','battery_modules','battery_power_dc_kw',
            'inverter_kva','archived_self_sufficiency_pct','archived_annual_cost_usd'}
    if not needed.issubset(refs.columns):
        raise ValueError('Archive equipment routing CSV lacks required source columns')
    selected=refs[refs['case'].eq(source_case)].copy()
    selected=selected[selected['selection_reasons'].str.contains('LOWEST_COST_SS_AT_LEAST_90_PCT',regex=False,na=False)]
    selected=selected[pd.to_numeric(selected.archived_self_sufficiency_pct,errors='coerce')>=90.0-1e-5]
    if selected.empty:raise ValueError('No source 90% SS anchor available in archived Stage A routing for '+source_case)
    selected=selected.sort_values(['archived_annual_cost_usd','equipment_id'])
    row=selected.iloc[0]
    return (str(row.equipment_id),int(row.pv_panels),int(row.battery_modules),
            float(row.battery_power_dc_kw),float(row.inverter_kva),
            'ARCHIVED_90PCT_SS_REFERENCE_IN_ORIGINAL_SYNTHETIC_CASE_'+source_case+
            ('_BORROWED_NOT_OPTIMAL_FOR_4_HOUSES' if count==4 else ''))


def selected_hardware(repo, variant, trafo, tier='min_cost'):
    from fixed_hardware import Hardware
    source_id, panels, modules, bat_power, kva_inv, provenance = archived_hardware_selection(repo,variant,trafo,tier)
    if min(panels,modules,bat_power,kva_inv)<=0:
        raise ValueError('Invalid source hardware')
    if bat_power>modules*2.24+1e-6:
        raise ValueError('Archived power exceeds manufacturer module continuous current limit')
    hw=Hardware(panels=panels, battery_modules=modules, battery_power_dc_kw=bat_power,
                inverter_kva=kva_inv, transformer_kva=RATINGS[trafo], loading_pu=1., load_pf=.98,
                export_policy='zero', annual_equipment_usd=float('nan'), annual_total_usd=float('nan'))
    return hw,source_id,provenance


def metrics_for_dispatch(hourly, modules):
    needed = ('pv_dc_available_kw','pv_dc_generated_kw','curtailed_pv_dc_kw',
              'battery_charge_dc_kw','battery_discharge_dc_kw','battery_soc_usable_kwh',
              'grid_import_kw','grid_export_kw','unserved_kw','demand_kw')
    if any(col not in hourly for col in needed):
        raise ValueError('Existing PyPSA output is missing required battery/PV hourly fields')
    numeric = hourly[list(needed)].astype(float)
    if not np.isfinite(numeric.to_numpy()).all():
        raise ValueError('Nonfinite energy trajectory')
    demand = float(numeric.demand_kw.sum()); grid = float(numeric.grid_import_kw.sum())
    charge = float(numeric.battery_charge_dc_kw.sum()); discharge = float(numeric.battery_discharge_dc_kw.sum())
    avail = float(numeric.pv_dc_available_kw.sum()); curtail = float(numeric.curtailed_pv_dc_kw.sum())
    effective_usable = modules * 5.12 * .80
    return dict(demand_kwh=demand, grid_import_kwh=grid, grid_export_kwh=float(numeric.grid_export_kw.sum()),
        unmet_load_kwh=float(numeric.unserved_kw.sum()), self_sufficiency_pct=100*(demand-grid)/demand if demand else None,
        available_pv_dc_kwh=avail, generated_pv_dc_kwh=float(numeric.pv_dc_generated_kw.sum()),
        curtailed_pv_dc_kwh=curtail, curtailed_pv_fraction=curtail/avail if avail else None,
        battery_charge_dc_kwh=charge, battery_discharge_dc_kwh=discharge,
        battery_charge_active_hours=int((numeric.battery_charge_dc_kw>1e-6).sum()),
        battery_discharge_active_hours=int((numeric.battery_discharge_dc_kw>1e-6).sum()),
        max_battery_charge_dc_kw=float(numeric.battery_charge_dc_kw.max()),
        max_battery_discharge_dc_kw=float(numeric.battery_discharge_dc_kw.max()),
        approx_equivalent_full_discharge_cycles=discharge/effective_usable if effective_usable else None,
        battery_soc_usable_min_kwh=float(numeric.battery_soc_usable_kwh.min()),
        battery_soc_usable_max_kwh=float(numeric.battery_soc_usable_kwh.max()),
        effective_physical_SOC_window_kwh=effective_usable,
        interpretation='Perfect foresight source PyPSA baseline, not causal controller, not AC feasibility; no transfer of historic costs')


def command_energy(args):
    repo, manifest, houses, trace = data_for_case(args)
    out = new_output(args.outdir)
    hw, src_id, status = selected_hardware(repo,args.assignment,args.transformer,args.anchor_tier)
    from fixed_hardware import solve_fixed
    # Preserve original archived NASA/pvlib solar profile, replace ONLY cohort demand.
    orig = repo/'Energy Community - San Rafael/pandapower_results_nasa/nasa_hourly_pv_and_load_inputs.csv'
    orig_df = pd.read_csv(orig, parse_dates=['timestamp']).set_index('timestamp')
    if len(orig_df)!=8760 or not orig_df.index.equals(trace.index):
        raise ValueError('Solar resource time alignment differs from 2025 A0/A1 demand')
    if not orig_df.nasa_pv_dc_kw.notna().all() or (orig_df.nasa_pv_dc_kw<0).any():
        raise ValueError('Invalid original solar source')
    pv_pu = orig_df.nasa_pv_dc_kw.astype(float)/5.22
    if pv_pu.max()>1.00001:
        raise ValueError('NASA solar capacity factor >1')
    hourly, summary = solve_fixed(repo, hw, trace.sum(axis=1), pv_pu, min_physical_soc=.20)
    hourly.index.name='timestamp_lst'
    if len(hourly)!=8760 or not hourly.index.equals(trace.index):
        raise ValueError('PyPSA hourly output missing or shifted')
    if np.max(np.abs(hourly.demand_kw.to_numpy(float)-trace.sum(axis=1).to_numpy(float)))>1e-5:
        raise ValueError('PyPSA output no longer matches requested cohort demand')
    if hourly.grid_export_kw.abs().max()>1e-5 or hourly.unserved_kw.abs().max()>1e-5:
        raise ValueError('Zero export/zero ENS baseline violated')
    result = metrics_for_dispatch(hourly, hw.battery_modules)
    # No filenames created until complete successful solve and full verification.
    out.mkdir(parents=False, exist_ok=False)
    path=out/'energy_hourly_2025.csv'; hourly.to_csv(path, float_format='%.10f')
    if 'timestamp_lst' not in pd.read_csv(path,nrows=1).columns:
        raise ValueError('CSV timestamp index missing')
    description = {'status':'FULL_8760H_PYPSA_FIXED_HARDWARE_NOT_AC_VALIDATED',
        'scenario':args.assignment, 'transformer':args.transformer, 'source_anchor_id':src_id,
        'source_anchor_provenance':status, 'hardware_selection_tier':args.anchor_tier, 'physical_customer_connections':'PROVISIONAL',
        'selected_house_ids': houses, 'hardware': {'pv_panels':hw.panels,'battery_modules':hw.battery_modules,
        'battery_power_dc_kw':hw.battery_power_dc_kw,'inverter_kva':hw.inverter_kva,
        'transformer_kva_assumed_or_evidenced':hw.transformer_kva},
        'assumptions': {'soc_min_physical':.20,'export_policy':'zero','PF_dispatch_screen':.98,
                        'inverter_site':'head_provisional', 'tariff_reuse_source':True},
        'input_manifest_sha256':sha(args.manifest), 'original_pv_source_sha256':sha(orig),
        'energy_csv_sha256':sha(path),'metrics':result,
        'economic_reoptimized_for_new_households':True, 'hardware_reoptimized':False,
        'archived_source_costs_transferred':False, 'source_model_summary':summary}
    dump(out/'energy_manifest.json',description)
    print(json.dumps({'status':description['status'],'output':str(out),'metrics':result},indent=2))


def read_energy_checked(path, manifest_path, houses, trace, variant, trafo):
    meta_path=path/'energy_manifest.json'; csv_path=path/'energy_hourly_2025.csv'
    meta=json.loads(meta_path.read_text(encoding='utf-8'))
    if meta['scenario']!=variant or meta['transformer']!=trafo or meta['selected_house_ids']!=houses:
        raise ValueError('Energy output belongs to different cohort')
    if meta['status']!='FULL_8760H_PYPSA_FIXED_HARDWARE_NOT_AC_VALIDATED':
        raise ValueError('Energy output not full-year fixed hardware')
    if meta['input_manifest_sha256']!=sha(manifest_path) or meta['energy_csv_sha256']!=sha(csv_path):
        raise ValueError('Energy provenance/hash mismatch')
    df=pd.read_csv(csv_path,parse_dates=['timestamp_lst']).set_index('timestamp_lst')
    if len(df)!=8760 or not df.index.equals(trace.index):
        raise ValueError('Energy series missing hours or timestamps')
    if np.max(np.abs(df.demand_kw.to_numpy(float)-trace.sum(axis=1).to_numpy(float)))>1e-5:
        raise ValueError('Energy series demand does not match named individual households')
    if df.grid_export_kw.abs().max()>1e-5 or df.unserved_kw.abs().max()>1e-5:
        raise ValueError('Energy baseline has export or ENS')
    return df, meta




def causal_pv_first_dispatch(demand_kw, available_pv_dc_kw, initial_store_kwh,
                             panels, modules, inverter_kva, battery_dc_power_kw):
    """Causal rule-based sensitivity, PV feeds live load then charges BESS.

    Store coordinates/efficiencies follow the archived PyPSA source model.
    Unlike the annual LP, this controller has NO future information and its
    final SOC is not forced equal to the starting SOC. Compare terminal SOC.
    No price/cost, Q, powerflow, meter, or backup capability is claimed.
    """
    if not modules or inverter_kva<=0 or battery_dc_power_kw<=0 or panels<=0:
        raise ValueError('Positive source-approved hardware required')
    eta_inv=.95; eta_bat=math.sqrt(.95)
    max_e=modules*(17.3/4)
    min_e=max(0.,modules*((17.3/4)-(.8*5.12)))
    max_ch_dc=min(battery_dc_power_kw,modules*2.24)
    max_dis_dc=min(battery_dc_power_kw,modules*2.24)
    soc=float(initial_store_kwh)
    if soc<min_e-1e-6 or soc>max_e+1e-6:
        raise ValueError('Initial PyPSA Store energy violates physical minimum SOC window')
    if len(demand_kw)!=len(available_pv_dc_kw):
        raise ValueError('Load and PV lengths do not match')
    results=[]
    for load0,pv0 in zip(demand_kw, available_pv_dc_kw):
        load=float(load0);pv=float(pv0)
        if min(load,pv)<-1e-9 or not math.isfinite(load+pv):
            raise ValueError('Invalid DC PV availability or AC load')
        load=max(0.,load);pv=max(0.,pv)
        inv_supply_limit=min(load,inverter_kva)
        dc_load_need=inv_supply_limit/eta_inv
        dc_direct=min(pv,dc_load_need)
        unmet_dc=max(0.,dc_load_need-dc_direct)
        discharge=min(unmet_dc,max_dis_dc,max(0.,(soc-min_e)*eta_bat))
        soc-=discharge/eta_bat
        ac_from_inv=(dc_direct+discharge)*eta_inv
        grid=max(0.,load-ac_from_inv)
        unused_dc=max(0.,pv-dc_direct)
        charge=min(unused_dc,max_ch_dc,max(0.,(max_e-soc)/eta_bat))
        soc+=charge*eta_bat
        curtailed=max(0.,unused_dc-charge)
        if soc<min_e-1e-7 or soc>max_e+1e-7:
            raise AssertionError('Causal battery state exceeds original usable capacity or 20% physical floor')
        if abs(pv-(dc_direct+charge+curtailed))>1e-6:
            raise AssertionError('PV energy balance violated')
        if abs(load-(grid+ac_from_inv))>1e-6:
            raise AssertionError('AC load energy balance violated')
        results.append(dict(demand_kw=load,pv_dc_available_kw=pv,
            pv_dc_direct_to_inverter_kw=dc_direct, pv_dc_battery_charge_kw=charge,
            curtailed_pv_dc_kw=curtailed,battery_charge_dc_kw=charge,
            battery_discharge_dc_kw=discharge,battery_soc_usable_kwh=soc,
            inverter_ac_kw=ac_from_inv,grid_import_kw=grid,grid_export_kw=0.,unserved_kw=0.))
    return pd.DataFrame(results)


def command_causal(args):
    repo, _, houses, trace = data_for_case(args)
    if args.energy_dir is None:
        raise ValueError('Causal sensitivity must reference identical full-year PyPSA baseline')
    hourly, ref=read_energy_checked(args.energy_dir.resolve(),args.manifest.resolve(),houses,trace,
                                    args.assignment,args.transformer)
    hw,src_id,provenance=selected_hardware(repo,args.assignment,args.transformer,args.anchor_tier)
    if ref.get('hardware_selection_tier')!=args.anchor_tier:
        raise ValueError('Causal hardware tier differs from PyPSA reference')
    initial=float(hourly.battery_soc_usable_kwh.iloc[-1])
    compare=causal_pv_first_dispatch(trace.sum(axis=1).to_numpy(),
         hourly.pv_dc_available_kw.to_numpy(),initial,hw.panels,hw.battery_modules,
         hw.inverter_kva,hw.battery_power_dc_kw)
    compare.index=trace.index
    compare.index.name='timestamp_lst'
    output=new_output(args.outdir)
    metrics=metrics_for_dispatch(compare.assign(pv_dc_generated_kw=
        compare.pv_dc_available_kw-compare.curtailed_pv_dc_kw), hw.battery_modules)
    metrics['initial_battery_soc_usable_kwh']=initial
    metrics['terminal_battery_soc_usable_kwh']=float(compare.battery_soc_usable_kwh.iloc[-1])
    metrics['terminal_minus_initial_store_kwh']=metrics['terminal_battery_soc_usable_kwh']-initial
    if abs(metrics['terminal_minus_initial_store_kwh'])>1e-4:
        metrics['energy_comparison_caveat']='Terminal SOC differs. Do not compare import or costs as a cyclic annual equivalent without correcting the SOC boundary.'
    output.mkdir(parents=False,exist_ok=False)
    compare.to_csv(output/'causal_pv_first_2025.csv',float_format='%.10f')
    record={'status':'FULL_8760H_CAUSAL_PV_FIRST_SENSITIVITY_NOT_EQUAL_TO_PYPSA_CYCLIC_OPTIMUM',
        'input_manifest_sha256':sha(args.manifest), 'reference_energy_manifest_sha256':sha(args.energy_dir/'energy_manifest.json'),
        'scenario':args.assignment,'transformer':args.transformer,'selected_houses':houses,
        'hardware_tier':args.anchor_tier,
        'initial_soc_basis':'SAME_BASELINE_CYCLIC_FINAL_SOC_AS_HOUR_ZERO_INITIAL',
        'terminal_soc_equality_enforced':False,'forecast_used':False,
        'no_grid_charging':True,'zero_export':True,'min_physical_soc':.20,
        'controller':'PV serves instantaneous load first; charge battery from solar surplus; discharge to remaining load; import remaining from grid',
        'note':'No AC, reactive capability, degradation economics or dispatch equal-optimality certification.',
        'source_anchor_id':src_id,'metrics':metrics,
        'reference_pypsa_metrics':ref['metrics'],'output_sha256':sha(output/'causal_pv_first_2025.csv')}
    dump(output/'causal_summary.json',record)
    print(json.dumps({'status':record['status'],'output':str(output),
                      'reference_import_kwh':ref['metrics']['grid_import_kwh'],
                      'causal_import_kwh':metrics['grid_import_kwh'],
                      'soc_terminal_delta_kwh':metrics['terminal_minus_initial_store_kwh']},indent=2))


def new_territory(repo, variant, trafo, houses, factor):
    read, infer, builder, cls = repo_modules(repo)
    hs, ts, lv = read()
    if trafo=='106039':
        rating=5.0  # user-selected hypothetical, not actual certified nameplate
    else:
        rating=RATINGS[trafo]
    assigned = resolve_v4_assignments(hs,ts,lv,infer,variant)
    territory = builder(trafo,hs,ts,lv,assigned,factor)
    if territory is None:
        raise ValueError('No LV GIS graph for this transformer')
    selected=sorted(x['house'] for x in territory.attachments)
    if selected != sorted(houses):
        raise ValueError(f'GIS territory houses do not match fixed profiles: {selected} != {houses}')
    territory = cls(trafo={**territory.trafo, 'kva':rating},
                    graph=territory.graph, attachments=territory.attachments,
                    label=territory.label,root=territory.root,line_count=territory.line_count)
    return territory


def inject_individual_loads(net, meta, case_row, pf, root_factor):
    if set(meta['loads']) != set(case_row.index):
        raise ValueError('Per-house load keys differ from the actual GIS attached house IDs')
    if not 0 < pf <= 1:
        raise ValueError('Invalid PF')
    qfac=math.tan(math.acos(pf))
    for hid, p_kw in case_row.items():
        if not math.isfinite(float(p_kw)) or p_kw<0:
            raise ValueError('Invalid individual load')
        idx=meta['loads'][hid]
        net.load.at[idx,'p_mw']=float(p_kw)*root_factor/1000.
        net.load.at[idx,'q_mvar']=float(p_kw)*qfac*root_factor/1000.
    expected_p=float(case_row.sum())*root_factor/1000.
    actual_p=sum(float(net.load.at[idx,'p_mw']) for idx in meta['loads'].values())
    if abs(expected_p-actual_p)>1e-11:
        raise AssertionError('GIS load node active-power balance invalid')


def solve_ac_hour(net, meta, territory, timestamp, loads, pf, inverter_kw,
                  inverter_kva, pv_dc_avail_kw, q_ratio, q_grid, mode, pp):
    root_factor=3.0
    inject_individual_loads(net,meta,loads,pf,root_factor)
    net.sgen.at[meta['inv'],'p_mw']=float(inverter_kw)*root_factor/1000.
    if float(inverter_kw)<-1e-7 or float(inverter_kw)>inverter_kva+1e-6:
        raise ValueError('Inverter AC output incompatible with reference rating')
    net.sgen.at[meta['inv'],'q_mvar']=0.
    res = {'timestamp_lst':str(timestamp), 'gross_demand_kw':float(loads.sum()),
           'inverter_ac_kw':float(inverter_kw),'load_pf':pf,'night_reactive_disabled':float(pv_dc_avail_kw)<=1e-9}
    from coordinated_q_control import ACLimits, ACPoint, choose_q, feasible
    limits=ACLimits(min_v=.95,max_v=1.05,max_trafo_pct=100.,max_line_pct=100.)
    try:
        # Simple load-only check; PV+BESS controller reuse is conditional on PV daylight.
        effective_ratio = 0. if mode=='gross' or float(pv_dc_avail_kw)<=1e-9 else q_ratio
        if mode=='gross' or effective_ratio==0.:
            q_req=0.
        else:
            from hil_voltvar import HILParams, capability_kvar, solve_q
            params=HILParams(q_ratio=effective_ratio)
            q_req, _, _ = solve_q(net,meta['inv'],meta['inv_bus'],float(inverter_kw),
                       float(inverter_kva),float(inverter_kva),'volt_var',params,root_factor)
            cap=capability_kvar(float(inverter_kw),float(inverter_kva),float(inverter_kva),params)
        cached={}
        def measure(q):
            key=round(float(q),11)
            if key not in cached:
                net.sgen.at[meta['inv'],'q_mvar']=float(q)*root_factor/1000.
                pp.runpp(net,algorithm='bfsw',init='flat',calculate_voltage_angles=False,
                         max_iteration=75,tolerance_mva=1e-8)
                vs=net.res_bus.loc[[meta['buses']['HOUSE_'+h] for h in meta['loads']],'vm_pu'].astype(float)
                load=float(net.res_trafo.at[meta['trafo'],'loading_percent'])
                line=float(net.res_line.loc[meta['line_ids'],'loading_percent'].max())
                loss=(float(net.res_line.pl_mw.sum())+float(net.res_trafo.pl_mw.sum()))*1000./root_factor
                pcc=math.hypot(float(net.res_ext_grid.p_mw.sum())*1000./root_factor,
                               float(net.res_ext_grid.q_mvar.sum())*1000./root_factor)
                cached[key]=ACPoint(float(q),float(vs.min()),float(vs.max()),load,line,loss,pcc)
            return cached[key]
        if mode=='gross' or effective_ratio==0.:
            final=measure(0.); status='Q_OFF'
        else:
            choice=choose_q(measure, cap,q_req,limits,grid_points=q_grid,refine=0)
            final=choice.point; status=choice.status
        # Re-establish the selected Q before saving state, do not leave last probe.
        net.sgen.at[meta['inv'],'q_mvar']=float(final.q_kvar)*root_factor/1000.
        pp.runpp(net,algorithm='bfsw',init='flat',calculate_voltage_angles=False,
                 max_iteration=75,tolerance_mva=1e-8)
        res.update(status='CONVERGED',ac_feasible=bool(feasible(final,limits)),q_selected_kvar=final.q_kvar,
           q_requested_kvar=q_req,q_controller_status=status,ac_evaluations=len(cached),
           min_v_pu=final.v_min,max_v_pu=final.v_max,max_trafo_pct=final.trafo_pct,
           max_line_pct=final.line_pct,loss_kw=final.loss_kw,pcc_kva=final.pcc_kva,
           voltage_below_095=int(final.v_min<.95-1e-6),voltage_above_105=int(final.v_max>1.05+1e-6),
           voltage_below_097=int(final.v_min<.97-1e-6),voltage_above_103=int(final.v_max>1.03+1e-6),
           trafo_over_100=int(final.trafo_pct>100+1e-4),line_over_100=int(final.line_pct>100+1e-4),
           error='')
    except Exception as e:
        res.update(status='AC_FAILURE',ac_feasible=False,q_selected_kvar=None,
                   q_requested_kvar=None,q_controller_status='AC_FAILURE',ac_evaluations=0,
                   min_v_pu=None,max_v_pu=None,max_trafo_pct=None,max_line_pct=None,
                   loss_kw=None,pcc_kva=None,voltage_below_095=None,voltage_above_105=None,
                   voltage_below_097=None,voltage_above_103=None,
                   trafo_over_100=None,line_over_100=None,error=str(e)[:300])
    return res


def command_ac(args):
    repo, input_manifest, houses, trace = data_for_case(args)
    if args.service_factor not in (1.,1.3,1.6):
        raise ValueError('Use approved 1.0, 1.3, 1.6 service length factor')
    if args.pf not in (.95,.98,1.0):
        raise ValueError('Use approved main sensitivity 0.95, 0.98, 1.00')
    if args.hours<1 or args.hours>8760:
        raise ValueError('Hours must be within 1..8760')
    out=new_output(args.outdir)
    hw,source_id,provenance=selected_hardware(repo,args.assignment,args.transformer,args.anchor_tier)
    if args.mode=='pvbess':
        if args.energy_dir is None:
            raise ValueError('PV+BESS AC requires --energy-dir source')
        hourly, energy_meta=read_energy_checked(args.energy_dir.resolve(),args.manifest.resolve(),houses,trace,
                                                 args.assignment,args.transformer)
        if energy_meta.get('hardware_selection_tier')!=args.anchor_tier:
            raise ValueError('AC hardware tier differs from signed PyPSA energy source')
        inverter_kva=hw.inverter_kva
    else:
        hourly=None; energy_meta=None; inverter_kva=0.
    territory=new_territory(repo,args.assignment,args.transformer,houses,args.service_factor)
    from run_epm_validation import build_net
    net, meta=build_net(territory,'head')
    if set(meta['loads'])!=set(houses):
        raise ValueError('Built GIS net does not preserve every selected household')
    import pandapower as pp
    rows=[]
    for i in range(args.hours):
        ts=trace.index[i]
        if hourly is None:
            p=0.; pv=0.
        else:
            p=float(hourly.iloc[i].inverter_ac_kw)
            pv=float(hourly.iloc[i].pv_dc_available_kw)
        rows.append(solve_ac_hour(net,meta,territory,ts,trace.iloc[i],args.pf,p,
                      inverter_kva,pv,args.q_ratio,args.q_grid_points,args.mode,pp))
        if (i+1)%250==0:print(f'AC evaluated {i+1}/{args.hours}',flush=True)
    results=pd.DataFrame(rows)
    converged=results[results.status=='CONVERGED']
    val={
       'status':'FULL_YEAR_GROSS_AC' if args.mode=='gross' and args.hours==8760 else
                ('FULL_YEAR_PVBESS_AC' if args.mode=='pvbess' and args.hours==8760 else 'PARTIAL_AC_SMOKE_TEST_NOT_AN_ANNUAL_RESULT'),
       'mode':args.mode,'scenario':args.assignment,'transformer':args.transformer,
       'hardware_tier':args.anchor_tier,
       'physical_household_connections':'PROVISIONAL', 'phase_model':'BALANCED_THREE_PHASE_PROXY',
       'simulation_hours':args.hours,'expected_year_hours':8760,'converged_hours':len(converged),
       'nonconverged_hours':args.hours-len(converged),
       'AC_feasible_hours':int(converged.ac_feasible.sum()) if len(converged) else 0,
       'AC_infeasible_hours':int((~converged.ac_feasible).sum()) if len(converged) else 0,
       'min_voltage_pu':float(converged.min_v_pu.min()) if len(converged) else None,
       'max_voltage_pu':float(converged.max_v_pu.max()) if len(converged) else None,
       'max_trafo_pct':float(converged.max_trafo_pct.max()) if len(converged) else None,
       'max_line_pct':float(converged.max_line_pct.max()) if len(converged) else None,
       'total_AC_losses_kwh_simulated':float(converged.loss_kw.sum()) if len(converged) else None,
       'hours_voltage_below_095':int(converged.voltage_below_095.sum()) if len(converged) else None,
       'hours_voltage_above_105':int(converged.voltage_above_105.sum()) if len(converged) else None,
       'hours_trafo_over_100':int(converged.trafo_over_100.sum()) if len(converged) else None,
       'hours_line_over_100':int(converged.line_over_100.sum()) if len(converged) else None,
       'PF':args.pf, 'service_length_multiplier':args.service_factor,'daylight_Q_ratio':args.q_ratio,
       'nighttime_Q':'OFF','inverter_placement':'HEAD_PROVISIONAL','PV_BESS_energy_baseline':str(args.energy_dir) if hourly is not None else None,
       'input_manifest_sha256':sha(args.manifest),
       'energy_manifest_sha256':sha(args.energy_dir/'energy_manifest.json') if hourly is not None else None,
       'geometry_status':'GIS_GRAPH_PREFLIGHT_ONLY_UNCERTIFIED',
       'interpretation':'AC static powerflow with provisional GIS connections; excludes other unmapped EPM consumers and actual phase imbalance; NOT field certification or AC-constrained dispatch.'}
    out.mkdir(parents=False,exist_ok=False)
    results.to_csv(out/'ac_hourly.csv',index=False,float_format='%.10f')
    val['ac_hourly_sha256']=sha(out/'ac_hourly.csv')
    dump(out/'ac_summary.json',val)
    print(json.dumps({'status':val['status'],'output':str(out),'hours':args.hours,
                      'nonconverged':val['nonconverged_hours'],'AC_feasible_hours':val['AC_feasible_hours']},indent=2))


def command_inspect(args):
    base=args.v4_run_dir.resolve()
    for name in ('fixed_house_to_profile_map.csv','household_profiles_2025_excel_35.csv'):
        p=base/name
        if not p.exists():print('MISSING:',p);continue
        d=pd.read_csv(p,nrows=3,encoding='utf-8-sig')
        print(json.dumps({'file':str(p),'sha256':sha(p),'columns':list(d.columns),
                          'first_two_rows':d.head(2).to_dict(orient='records')},indent=2,default=str))


def cli(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='stage',required=True)
    inspect=sub.add_parser('inspect',help='Read-only CSV schema inspection, no writes')
    inspect.add_argument('--v4-run-dir',type=Path,required=True)
    prepare=sub.add_parser('prepare',help='Validate named A0/A1 input provenance, no modelling')
    prepare.add_argument('--repo-root',type=Path,default=Path('.'))
    prepare.add_argument('--v4-run-dir',type=Path,required=True)
    prepare.add_argument('--out',type=Path,required=True)
    for mode in ('energy','causal','ac'):
        sp=sub.add_parser(mode)
        sp.add_argument('--manifest',type=Path,required=True)
        sp.add_argument('--assignment',choices=['A0','A1'],required=True)
        sp.add_argument('--anchor-tier',choices=['min_cost','ss90'],default='min_cost')
        sp.add_argument('--transformer',required=True,choices=sorted(ELIGIBLE))
        sp.add_argument('--outdir',type=Path,required=True)
        if mode=='causal':
            sp.add_argument('--energy-dir',type=Path,required=True)
        if mode=='ac':
            sp.add_argument('--mode',choices=['gross','pvbess'],default='gross')
            sp.add_argument('--energy-dir',type=Path)
            sp.add_argument('--pf',type=float,default=.98)
            sp.add_argument('--service-factor',type=float,default=1.)
            sp.add_argument('--q-ratio',type=float,default=.25)
            sp.add_argument('--q-grid-points',type=int,default=9)
            sp.add_argument('--hours',type=int,default=24)
    args=ap.parse_args(argv)
    if args.stage=='inspect':command_inspect(args)
    elif args.stage=='prepare':command_prepare(args)
    elif args.stage=='energy':command_energy(args)
    elif args.stage=='causal':command_causal(args)
    else:command_ac(args)


if __name__=='__main__':cli()
