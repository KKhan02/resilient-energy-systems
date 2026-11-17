#!/usr/bin/env python3
"""Render Stage 14 from the signed 2025 A1 106039 review CSVs. No modelling runs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

FILES = {
    'annual': ('ALL_8_DESIGNS_COST_IMPORT_FRONTIER.csv', '18717d0fc598c6ec0561e7bbd5c9d1d48a56116f0a4b2c4ada3535e710d89a10'),
    'monthly': ('MONTHLY_96_CASE_MONTH_RECORDS.csv', '4a3fb6e99f0edc69cdcae1da65f063923c8d9210dc5e74d98543fc3a76420861'),
}
IDS = {'MC_REF', 'MC_B9', 'MC_P37', 'SS_REF', 'SS_B9', 'SS_B10', 'SS_P45', 'SS_P41_KEEP20'}


def read_checked(folder):
    data = {}
    for key, (name, wanted) in FILES.items():
        path = folder / name
        payload = path.read_bytes()
        got = hashlib.sha256(payload).hexdigest()
        if got != wanted:
            raise ValueError(f'Incorrect source {name}: {got}, expected {wanted}')
        with path.open(encoding='utf-8-sig', newline='') as stream:
            data[key] = list(csv.DictReader(stream))
    if {row['case_id'] for row in data['annual']} != IDS or len(data['annual']) != 8:
        raise ValueError('Expected the original eight cases')
    for key in ('SS_REF', 'SS_B9'):
        months = [r for r in data['monthly'] if r['case_id'] == key]
        annual = next(r for r in data['annual'] if r['case_id'] == key)
        if len(months) != 12 or {int(m['month']) for m in months} != set(range(1, 13)):
            raise ValueError(f'Incomplete monthly data: {key}')
        for mcol, acol in [('grid_import_kw_kwh', 'grid_import_kwh'), ('curtailed_pv_dc_kw_kwh', 'curtailed_pv_dc_kwh')]:
            if abs(sum(float(m[mcol]) for m in months) - float(annual[acol])) > 1e-5:
                raise ValueError(f'Monthly mismatch: {key}/{mcol}')
    return data


def pareto(rows):
    pts = {r['case_id']:(float(r['grid_import_kwh']),float(r['annual_total_usd'])) for r in rows}
    return {name for name, (imp,cost) in pts.items() if not any(bimp<=imp and bcost<=cost and (bimp<imp or bcost<cost) for other,(bimp,bcost) in pts.items() if other!=name)}


def render(data, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'axes.titlesize': 12, 'figure.dpi': 140, 'savefig.dpi': 180})
    annual, monthly = data['annual'], data['monthly']
    by_id = {r['case_id']: r for r in annual}
    front = pareto(annual)
    if front != {'MC_REF','MC_B9','SS_B9','SS_B10'}:
        raise ValueError(f'Unexpected energy-only nondominated frontier: {front}')
    fig, ax = plt.subplots(figsize=(12, 7))
    points = sorted((by_id[n] for n in front),key=lambda r:float(r['grid_import_kwh']))
    ax.plot([float(r['grid_import_kwh']) for r in points], [float(r['annual_total_usd']) for r in points], ':', linewidth=1.8, label='Within-sample non-dominated designs', color='0.42')
    for row in annual:
        name=row['case_id'];ref = row['kind']=='SIGNED_REFERENCE'
        ax.scatter(float(row['grid_import_kwh']),float(row['annual_total_usd']),s=78,marker='s' if ref else 'o',color='tab:blue' if ref else ('tab:orange' if name in front else '0.65'),edgecolor='0.2',zorder=3)
        ax.annotate(name,(float(row['grid_import_kwh']),float(row['annual_total_usd'])),xytext=(5,7),textcoords='offset points',fontsize=9)
    ax.set(xlabel='Annual grid imports, kWh',ylabel='Modelled annual cost, USD/year',title='Stage 14 | Energy-only PV/BESS cost and grid imports')
    ax.grid(alpha=.25);ax.legend(loc='lower right')
    fig.text(.085,.035,'Eight fixed-hardware LP scenarios. No new investment optimization, installed-network costs or AC feasibility claim.',fontsize=9)
    fig.text(.085,.015,'PF 0.95, length 1.6: SS_B9 1 and MC_B9 2 transformer overload hours. New B9 designs not AC-feasible.',fontsize=9)
    fig.tight_layout(rect=[0,.07,1,1]);fig.savefig(output/'01_stage14_energy_only_cost_import_frontier.png',bbox_inches='tight');plt.close(fig)

    fig, axes = plt.subplots(2,1,figsize=(12,8),sharex=True)
    month_axis=list(range(1,13))
    for ax, case in zip(axes,('SS_REF','SS_B9')):
        records=sorted((r for r in monthly if r['case_id']==case),key=lambda r:int(r['month']))
        available=[float(r['pv_dc_available_kw_kwh']) for r in records]
        curtailed=[float(r['curtailed_pv_dc_kw_kwh']) for r in records]
        used=[a-c for a,c in zip(available,curtailed)]
        imports=[float(r['grid_import_kw_kwh']) for r in records]
        ax.bar(month_axis,used,label='DC PV not curtailed',color='tab:blue',width=.75)
        ax.bar(month_axis,curtailed,bottom=used,label='DC PV curtailed',color='tab:orange',width=.75)
        ax.plot(month_axis,imports,'o-',label='AC grid imports',color='tab:green',linewidth=1.8)
        ax.set(ylabel='Monthly energy, kWh',title=f'{case}: {by_id[case]["pv_panels"]} panels, {by_id[case]["battery_modules"]} batteries, {by_id[case]["inverter_kva"]} kVA')
        ax.grid(axis='y',alpha=.2)
    axes[1].set_xticks(month_axis,['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
    axes[0].legend(loc='upper right',ncol=3,fontsize=8)
    fig.suptitle('Stage 14 | Monthly solar use, curtailment and imports',fontsize=14)
    fig.text(.09,.024,'DC PV not curtailed is not equal to AC energy delivered to loads. Signed 2025 fixed-equipment records.',fontsize=9)
    fig.tight_layout(rect=[0,.06,1,.95]);fig.savefig(output/'02_stage14_monthly_solar_utilization.png',bbox_inches='tight');plt.close(fig)

    fig, axes=plt.subplots(1,2,figsize=(12,5.6))
    groups=[(['SS_REF','SS_B9','SS_B10'],'49 panels, 20 kVA'),(['MC_REF','MC_B9'],'41 panels, 12 kVA')]
    for ax,col,title in zip(axes,('grid_import_kwh','equivalent_full_cycles'),('Grid imports, kWh/year','Equivalent battery full cycles/year')):
        for names,label in groups:
            rr=[by_id[name] for name in names]
            ax.plot([int(r['battery_modules']) for r in rr],[float(r[col]) for r in rr],'o-',label=label)
            for r in rr:ax.annotate(r['case_id'],(int(r['battery_modules']),float(r[col])),xytext=(4,7),textcoords='offset points',fontsize=8)
        ax.set(xlabel='Battery modules, 5.12 kWh each',ylabel=title,xticks=[8,9,10]);ax.grid(alpha=.25)
    axes[0].legend(loc='upper right',fontsize=9)
    fig.suptitle('Stage 14 | Battery utilization in matched hardware families',fontsize=14)
    fig.text(.09,.03,'Fixed-hardware perfect-foresight optimization only. Equipment changes require their own AC validation.',fontsize=9)
    fig.tight_layout(rect=[0,.07,1,.94]);fig.savefig(output/'03_stage14_battery_utilization.png',bbox_inches='tight');plt.close(fig)
    return sorted(front)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    repo=Path(__file__).resolve().parents[3]
    ap.add_argument('--source-root',type=Path,default=repo/'case1/studies/SEEDExchange_StudyA_Utilization_Pilot_Review_2026-11-17')
    ap.add_argument('--out',type=Path,default=Path(__file__).resolve().parent/'figures')
    a=ap.parse_args()
    if a.out.exists():
        raise FileExistsError(f'Refusing to overwrite {a.out}. Use a new --out path.')
    data=read_checked(a.source_root)
    a.out.mkdir(parents=True)
    front=render(data,a.out)
    manifest={'kind':'ENERGY_ONLY','case':'A1 106039 (11 houses)','year':2025,'source_files':{name:sha for name,sha in FILES.values()},'non_dominated_in_eight':front,'figures':sorted(p.name for p in a.out.glob('*.png')),'ac_limit':'B9 designs have transformer overload hours at PF 0.95 and length 1.6; no AC certification'}
    (a.out/'FIGURE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2))


if __name__ == '__main__':
    main()
