#!/usr/bin/env python3
"""Study A 92395: proposed STAR vs MST annual gross AC using frozen v6.2 source.

A0 and A1 have identical H30-H33 membership and profile mapping at 92395,
so each STAR/MST/PF/length combination is numerically identical for A0/A1.
Reports BOTH, without duplicating 8,760h numerical computations.

No existing EPM LV line is claimed or modified. Both networks are proposed.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import networkx as nx
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_RUNNER = Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/seed_study_a_v6.py')
DEFAULT_MANIFEST = Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/input_manifest_v6_2.json')
OUT_REL = Path('case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/92395_proposed_STAR_MST_v1')
EXPECTED_MANIFEST_SHA = '2ff7eb9c1f28f12efc11aca9b366e5277da72a62f6d7709f47dc3841b6e71d69'
HOUSE_IDS = ('H30','H31','H32','H33')
FLOOR_M = .25
PF = (.95,.98,1.00)
LENGTH = (1.0,1.3,1.6)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_v6(repo):
    p=repo/REPO_RUNNER
    spec=importlib.util.spec_from_file_location('study_a_frozen_v6_2',p)
    if spec is None or spec.loader is None:raise FileNotFoundError(str(p))
    v6=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=v6
    spec.loader.exec_module(v6)
    return v6


def preflight(repo,manifest_path):
    if not (repo/'.git').exists():
        raise ValueError('Use checked-out local repository root, including .git')
    if sha(manifest_path)!=EXPECTED_MANIFEST_SHA:
        raise ValueError('Manifest bytes changed; refusing to mix source versions')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if sha(repo/REPO_RUNNER)!=manifest['script_sha256']:
        raise ValueError('Frozen v6.2 script changed')
    for name,sig in manifest['model_source_hashes'].items():
        if sha(repo/name)!=sig:raise ValueError('Original module hash changed: '+name)
    if (manifest['groups']['A0']['92395']!=list(HOUSE_IDS) or
        manifest['groups']['A1']['92395']!=list(HOUSE_IDS)):
        raise ValueError('92395 A0/A1 must contain exactly the identical 4 households')
    if manifest['population_houses']!=35 or manifest['2025_hours']!=8760:
        raise ValueError('Manifest population/year mismatch')
    v6=load_v6(repo)
    inputs=Path(manifest['v4_run_dir'])
    _,_,mapping,profiles,groups,_=v6.validated_sources(repo,inputs,manifest)
    if groups != manifest['groups'] or mapping != manifest['mapping']:
        raise ValueError('A0/A1 membership or profile mapping changed')
    read,_,_,Territory=v6.repo_modules(repo)
    houses,trafos,lv=read()
    if sha(repo/'case1/studies/epm_gis_pandapower_v1/data/epm_network_relevant_sanitized.geojson')!=manifest['gis_geojson_sha256']:
        raise ValueError('Source EPM geometry hash mismatch')
    if sha(repo/'case1/studies/epm_gis_pandapower_v1/data/houses_candidate_associations.csv')!=manifest['gis_house_sha256']:
        raise ValueError('Source house coordinates hash mismatch')
    if '92395' not in trafos or float(trafos['92395']['kva'])!=5.:
        raise ValueError('Source 92395 nameplate is not the expected 5 kVA')
    for h in HOUSE_IDS:
        if houses[h]['transformer_number']!='92395':
            raise ValueError('Source house association changed for '+h)
    trace=pd.DataFrame({h:profiles[mapping[h]].to_numpy() for h in HOUSE_IDS},index=profiles.index)
    if not np.isfinite(trace.to_numpy()).all() or abs(trace.to_numpy().sum()-4*1898)>0.1:
        raise ValueError('Invalid 92395 4-house annual 2025 trace')
    return v6,manifest,trace,houses,trafos,Territory


def plan(phase='all',topologies=('star','mst')):
    if phase not in ('baseline','main','interactions','all'):raise ValueError('Invalid phase')
    baseline=((.98,1.),)
    main=((.95,1.),(1.,1.),(.98,1.3),(.98,1.6))
    interactions=((.95,1.3),(.95,1.6),(1.,1.3),(1.,1.6))
    combinations={'baseline':baseline,'main':main,'interactions':interactions,
                  'all':baseline+main+interactions}[phase]
    if len(set(combinations))!=len(combinations):raise AssertionError('Duplicate combinations')
    return [(topo,pf,length) for topo in topologies for pf,length in combinations]


def make_territory(houses,trafos,Territory,topology,length_factor):
    """Direct STAR or five-node Euclidean MST, both proposed, with 0.25m house stubs for MST.

    Same conservative illustrative AAC size 4 conductor across all assumed edges.
    The service-length multiplier applies to every proposed edge, not source GIS.
    """
    if topology not in ('star','mst'):raise ValueError('Use star or mst')
    if length_factor not in LENGTH:raise ValueError('Length must be one of x1.0,x1.3,x1.6')
    t=trafos['92395']
    root='PROPOSED_TRAFO_92395'
    points={root:(float(t['x']),float(t['y']))}
    for hid in HOUSE_IDS:
        points['JUNCTION_'+hid]=(float(houses[hid]['x']),float(houses[hid]['y']))
    if not all(math.isfinite(v) for pt in points.values() for v in pt):
        raise ValueError('Nonfinite georeferenced coordinates')
    g=nx.Graph()
    g.add_node(root,x=points[root][0],y=points[root][1],type='transformer_root_proposed')
    attachments=[]
    def edge(u,v,dist,kind):
        length=max(FLOOR_M,float(dist))*length_factor
        g.add_edge(u,v,length_m=length,kind=kind,source_fid='PROPOSED_92395_'+topology.upper(),
                   material='ASSUMED_AAC',calibre='4')
    if topology=='star':
        for hid in HOUSE_IDS:
            node='HOUSE_'+hid;p=points['JUNCTION_'+hid]
            g.add_node(node,x=p[0],y=p[1],type='house',house=hid)
            eu=math.dist(points[root],p)
            edge(root,node,max(FLOOR_M,eu),'assumed_service')
            attachments.append({'house':hid,'trafo':'92395','segment':'PROPOSED_STAR',
                                'service_euclidean_m':eu,'service_length_m':max(FLOOR_M,eu)*length_factor,
                                'assumed':True,'changed':False,
                                'source_status':houses[hid].get('assignment_status','UNKNOWN')})
    else:
        complete=nx.Graph()
        for node in points:complete.add_node(node)
        nodes=sorted(points)
        for i,u in enumerate(nodes):
            for v in nodes[i+1:]:
                complete.add_edge(u,v,weight=math.dist(points[u],points[v]))
        tree=nx.minimum_spanning_tree(complete,weight='weight',algorithm='kruskal')
        for node in sorted(points):
            if node==root:continue
            p=points[node];g.add_node(node,x=p[0],y=p[1],type='proposed_lv_junction')
        for u,v in sorted((tuple(sorted((u,v))) for u,v in tree.edges())):
            edge(u,v,math.dist(points[u],points[v]),'assumed_service')
        for hid in HOUSE_IDS:
            key='JUNCTION_'+hid;node='HOUSE_'+hid;p=points[key]
            g.add_node(node,x=p[0],y=p[1],type='house',house=hid)
            # Separation is a numerical model stub, not a surveyed meter drop.
            edge(key,node,FLOOR_M,'assumed_service')
            path=nx.shortest_path(g,root,node)
            route=sum(g[a][b]['length_m'] for a,b in zip(path,path[1:]))
            attachments.append({'house':hid,'trafo':'92395','segment':'PROPOSED_MST',
                                'service_euclidean_m':math.dist(points[root],p),
                                'service_length_m':route,'assumed':True,'changed':False,
                                'source_status':houses[hid].get('assignment_status','UNKNOWN')})
    assert nx.is_tree(g) and g.number_of_nodes() in (5,9)
    return Territory(trafo=t,graph=g,attachments=attachments,
                     label=f'92395_PROPOSED_{topology.upper()}_A0_EQUALS_A1',root=root,line_count=0)


def suffix(topology,pf,length):
    return f'92395_proposed_{topology}_pf{round(pf*100):03d}_length{round(length*10):02d}'


def check_existing(folder, topology,pf,length,hours,manifest_hash):
    if not folder.exists():return False
    summary=folder/'ac_summary.json';csv=folder/'ac_hourly.csv'
    if not summary.exists() or not csv.exists():
        raise RuntimeError('Partial existing output, review without overwriting '+str(folder))
    d=json.loads(summary.read_text(encoding='utf-8'))
    expected={'transformer':'92395','mode':'gross','topology':topology,'PF':pf,
              'service_length_multiplier':length,'simulation_hours':hours,
              'input_manifest_sha256':manifest_hash,'ac_hourly_sha256':sha(csv),
              'source_assignments':['A0','A1']}
    if any(d.get(k)!=v for k,v in expected.items()):
        raise RuntimeError('Existing output not verified; refusing overwrite '+str(folder))
    if d['converged_hours']+d['nonconverged_hours']!=hours:
        raise RuntimeError('Convergence accounting mismatch '+str(folder))
    return True


def run_case(v6,manifest_path,trace,houses,trafos,Territory,topology,pf,length,hours,outdir):
    if check_existing(outdir,topology,pf,length,hours,sha(manifest_path)):
        print('PRESERVED',outdir,flush=True)
        return json.loads((outdir/'ac_summary.json').read_text(encoding='utf-8'))
    terr=make_territory(houses,trafos,Territory,topology,length)
    from run_epm_validation import build_net
    net,meta=build_net(terr,'head')
    if set(meta['loads'])!=set(HOUSE_IDS):raise AssertionError('Wrong network households')
    import pandapower as pp
    rows=[]
    for i in range(hours):
        rows.append(v6.solve_ac_hour(net,meta,terr,trace.index[i],trace.iloc[i],pf,
                                    0.,0.,0.,.25,9,'gross',pp))
        if (i+1)%500==0: print('Evaluated',i+1,'/',hours,flush=True)
    frame=pd.DataFrame(rows)
    good=frame[frame.status.eq('CONVERGED')]
    val={'status':'FULL_YEAR_GROSS_AC' if hours==8760 else 'PARTIAL_AC_SMOKE_TEST_NOT_AN_ANNUAL_RESULT',
         'mode':'gross','scenario':'A0_EQUALS_A1','source_assignments':['A0','A1'],
         'transformer':'92395','houses':list(HOUSE_IDS),'topology':topology,
         'topology_evidence':'PROPOSED_HYPOTHETICAL_NO_EPM_LV_GEOMETRY',
         'physical_household_connections':'PROPOSED_NOT_FIELD_VERIFIED',
         'line_conductor':'ASSUMED_AAC_4_ALL_EDGES','phase_model':'BALANCED_THREE_PHASE_PROXY',
         'simulation_hours':hours,'expected_year_hours':8760,
         'converged_hours':len(good),'nonconverged_hours':hours-len(good),
         'AC_feasible_hours':int(good.ac_feasible.sum()) if len(good) else 0,
         'AC_infeasible_hours':int((~good.ac_feasible).sum()) if len(good) else 0,
         'min_voltage_pu':float(good.min_v_pu.min()) if len(good) else None,
         'max_voltage_pu':float(good.max_v_pu.max()) if len(good) else None,
         'max_trafo_pct':float(good.max_trafo_pct.max()) if len(good) else None,
         'max_line_pct':float(good.max_line_pct.max()) if len(good) else None,
         'total_AC_losses_kwh_simulated':float(good.loss_kw.sum()) if len(good) else None,
         'hours_voltage_below_095':int(good.voltage_below_095.sum()) if len(good) else None,
         'hours_voltage_above_105':int(good.voltage_above_105.sum()) if len(good) else None,
         'hours_voltage_below_097':int(good.voltage_below_097.sum()) if len(good) else None,
         'hours_trafo_over_100':int(good.trafo_over_100.sum()) if len(good) else None,
         'hours_line_over_100':int(good.line_over_100.sum()) if len(good) else None,
         'PF':pf,'service_length_multiplier':length,
         'inverter_placement':'NONE_GROSS','PV_BESS_energy_baseline':None,
         'input_manifest_sha256':sha(manifest_path),
         'geometry_status':'HYPOTHETICAL_STAR_OR_MST_NOT_GIS_CERTIFIED',
         'total_proposed_edge_m':round(sum(x['length_m'] for _,_,x in terr.graph.edges(data=True)),3),
         'edge_count':terr.graph.number_of_edges(),
         'interpretation':'No source LV coverage for 92395; service existence not disproved. Proposed geometry only; no PV/BESS, no actual phases, no other unmapped consumers.'}
    outdir.parent.mkdir(parents=True,exist_ok=True)
    if outdir.exists():raise RuntimeError('Refusing to overwrite '+str(outdir))
    outdir.mkdir(exist_ok=False)
    frame.to_csv(outdir/'ac_hourly.csv',index=False,float_format='%.10f')
    val['ac_hourly_sha256']=sha(outdir/'ac_hourly.csv')
    (outdir/'ac_summary.json').write_text(json.dumps(val,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('RESULT',suffix(topology,pf,length),hours,'h, convergence',len(good),'/',hours,
          'infeasible',val['AC_infeasible_hours'],flush=True)
    return val


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--manifest',type=Path)
    ap.add_argument('--phase',choices=('baseline','main','interactions','all'),default='all')
    ap.add_argument('--topology',choices=('star','mst'),action='append',help='Omit to run both')
    g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--dry-run',action='store_true')
    g.add_argument('--run',action='store_true')
    args=ap.parse_args(argv)
    repo=args.repo_root.resolve();mp=(args.manifest or repo/DEFAULT_MANIFEST).resolve()
    v6,m,trace,houses,trafos,Territory=preflight(repo,mp)
    topo=tuple(dict.fromkeys(args.topology)) if args.topology else ('star','mst')
    cases=plan(args.phase,topo)
    target=repo/OUT_REL
    print('Source evidence OK. 92395 has four IDENTICAL A0/A1 customers.',
          len(cases),'unique proposed AC combinations')
    if args.dry_run:
        for k,pf,length in cases:
            for hrs in (24,8760):
                print('PLAN',k,pf,length,hrs,target/(suffix(k,pf,length)+('_smoke24' if hrs==24 else '_annual8760')))
        print('DRY RUN ONLY: no power flow calculated, no outputs written')
        return 0
    issues=[]
    for k,pf,length in cases:
        tag=suffix(k,pf,length)
        print('\n=== CASE',tag,'===',flush=True)
        try:
            smoke=run_case(v6,mp,trace,houses,trafos,Territory,k,pf,length,24,target/(tag+'_smoke24'))
            if smoke['nonconverged_hours']:
                issues.append((tag,'smoke_nonconvergence'));continue
            annual=run_case(v6,mp,trace,houses,trafos,Territory,k,pf,length,8760,target/(tag+'_annual8760'))
            if annual['nonconverged_hours']:issues.append((tag,'annual_nonconvergence'))
        except Exception as e:
            print('CASE ERROR (preserved)',tag,str(e),flush=True)
            issues.append((tag,str(e)))
    if issues:
        print('NONCOMPLETE RESULTS:',issues)
        return 2
    print('COMPLETE: 92395 proposed STAR/MST',len(cases),'unique annual parameter cases; A0=A1')
    return 0

if __name__=='__main__':sys.exit(main())
