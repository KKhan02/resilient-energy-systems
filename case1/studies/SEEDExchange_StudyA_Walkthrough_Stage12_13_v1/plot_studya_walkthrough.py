#!/usr/bin/env python3
"""Read-only, figure-only Stage 12/13 research walkthrough for SEEDExchange.

All numerical results derive from the 16-Nov-2026 audited Study A summary CSVs;
no optimizer or power-flow is invoked. For G4 topology, prefer original GitLab
checkout GIS source files when --repo-root is provided; otherwise the included
rounded GIS snapshot is a figure-preview-only extract from remote GitLab main.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

HERE=Path(__file__).resolve().parent
TID_TO_NODE={'94022':'931076','106039':'923494','113699':'823002',
             '85398':'900607','92395':'923848','98380':'241054'}
COL={'94022':'#287fba','106039':'#df842b','113699':'#bc3d74',
     '85398':'#29915c','92395':'#8b5fc9','98380':'#c49b30'}
GREY='#5b6672'
DARK='#1c2935'
BGC='#ffffff'
YLAB={'min_cost':'Minimum-cost hardware','ss90':'Higher-SS hardware'}


def look():
    mpl.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':13,
        'axes.labelsize':10,'figure.facecolor':BGC,'savefig.facecolor':BGC,
        'axes.spines.top':False,'axes.spines.right':False,'axes.grid':False,
        'svg.fonttype':'none','pdf.fonttype':42})


def emit(fig, out, name):
    out.mkdir(parents=True,exist_ok=True)
    for ext in ('png','svg'):
        fig.savefig(out/f'{name}.{ext}',dpi=280,bbox_inches='tight',pad_inches=.16)
    plt.close(fig)


def exact(frame,**kw):
    s=frame
    for k,v in kw.items():
        if isinstance(v,float):s=s[np.isclose(s[k],v,rtol=0,atol=1e-7)]
        else:s=s[s[k].astype(str)==str(v)]
    if len(s)!=1:raise AssertionError(f'Expected one source row {kw}; found {len(s)}')
    return s.iloc[0]


def validate(e):
    agg=pd.read_csv(e/'FIVE_TERRITORY_STAR_AGGREGATE_COMPARISON_36.csv')
    ac=pd.read_csv(e/'AC_432_CORRECTED_UNIQUE_CASES.csv')
    gr=pd.read_csv(e/'GROSS_90_CASE_REFERENCE.csv')
    en=pd.read_csv(e/'ENERGY_22_RECONCILED_COSTS.csv')
    assert len(agg)==36 and len(ac)==432 and len(gr)==90 and len(en)==22
    assert ac.case_identity.nunique()==432
    assert set(ac.pf.round(2))=={.95,.98,1.00}
    assert set(ac.length_factor.round(1))=={1.0,1.3,1.6}
    assert (ac.hours==8760).all() and (ac.nonconverged_hours==0).all()
    assert len(ac.input_manifest_sha256.unique())==1
    assert len(agg[['scenario','tier','pf','length_factor']].drop_duplicates())==36
    assert set(en.annual_cost_validation)=={'MATCH','REPAIRED_MISSING_COLLECTOR_VALUE'}
    return agg,ac,gr,en


def label_footer(fig,msg,y=.015):
    fig.text(.065,y,msg,fontsize=8,color=GREY,ha='left',va='bottom')


def fig_p1(agg,out):
    """Five-territory matched annual violation-hour progression."""
    fig,axs=plt.subplots(1,2,figsize=(11.2,4.45),sharey=True)
    bins=[('Gross demand','gross','#637080'),('Minimum-cost PV+BESS','min_cost',COL['94022']),
          ('Higher-SS PV+BESS','ss90','#229379')]
    for ax,variant in zip(axs,('A0','A1')):
        r=exact(agg,scenario=variant,tier='ss90',pf=.98,length_factor=1.)
        allvalues={
            'gross':int(r.five_territory_gross_transformer_violation_hours),
            'min_cost':int(exact(agg,scenario=variant,tier='min_cost',pf=.98,length_factor=1.).five_territory_pvbess_transformer_violation_hours),
            'ss90':int(r.five_territory_pvbess_transformer_violation_hours)}
        for i,(title,key,color) in enumerate(bins):
            v=allvalues[key]
            ax.barh(i,v,height=.47,color=color,edgecolor='none')
            ax.annotate(str(v),xy=(v,i),xytext=(7,0),textcoords='offset points',
                        ha='left',va='center',fontsize=11,fontweight='bold',color=DARK)
        ax.invert_yaxis()
        ax.set_yticks(range(3),[x[0] for x in bins])
        ax.set_xlim(0,125)
        ax.set_xticks([0,25,50,75,100,125])
        ax.grid(axis='x',alpha=.16,lw=.6)
        ax.set_axisbelow(True)
        ax.set_title(f'{variant} household assignment',loc='left',fontweight='bold',pad=12)
        ax.set_xlabel('Annual AC violation territory-hours')
    fig.suptitle('How geographic assignment and shared PV+BESS change AC feasibility',
        x=.05,y=1.02,ha='left',fontsize=14,fontweight='medium')
    fig.subplots_adjust(wspace=.16,top=.8,bottom=.24,left=.225,right=.985)
    label_footer(fig,'34 households across five territories, including proposed 92395 STAR. PF 0.98, service ×1.0, optimized dispatch. Counts sum per-territory hours.',.06)
    emit(fig,out,'P1_gross_vs_pvbess_ac_violations')


def fig_p2(agg,out):
    """Identical 3x3 PF/route grid for higher-SS equipment A0/A1."""
    fig,axs=plt.subplots(1,2,figsize=(10.6,4.8))
    values={}
    for ax,sc in zip(axs,('A0','A1')):
        vals=np.array([[exact(agg,scenario=sc,tier='ss90',pf=pf,length_factor=lf).five_territory_pvbess_transformer_violation_hours
                        for lf in (1.,1.3,1.6)] for pf in (.95,.98,1.0)],dtype=float)
        values[sc]=vals
    bound=max(v.max() for v in values.values())
    for ax,sc in zip(axs,('A0','A1')):
        vals=values[sc]
        im=ax.imshow(vals,vmin=0,vmax=bound,cmap='viridis_r',aspect='auto')
        ax.set_xticks([0,1,2],['1.0×','1.3×','1.6×'])
        ax.set_yticks([0,1,2],['0.95','0.98','1.00'])
        ax.set_xlabel('Service-length multiplier')
        ax.set_ylabel('Demand power factor')
        ax.set_title(f'{sc}: higher-SS PV+BESS',loc='left',pad=11,fontweight='bold')
        for i in range(3):
            for j in range(3):
                n=int(vals[i,j]);ax.text(j,i,str(n),ha='center',va='center',
                    color=('white' if n>bound*.55 else DARK),fontsize=13,fontweight='bold')
        ax.tick_params(length=0)
        for sp in ax.spines.values():sp.set_visible(False)
        ax.set_xticks(np.arange(-.5,3,1),minor=True)
        ax.set_yticks(np.arange(-.5,3,1),minor=True)
        ax.grid(which='minor',color='white',lw=3)
        ax.tick_params(which='minor',bottom=False,left=False)
    cb=fig.colorbar(im,ax=axs.tolist(),fraction=.025,pad=.02)
    cb.set_label('Annual violation territory-hours',fontsize=9)
    fig.suptitle('Residual AC violations persist under power-factor and route uncertainty',
        x=.06,y=.995,ha='left',fontsize=13,fontweight='medium')
    fig.subplots_adjust(left=.075,right=.87,top=.84,bottom=.22,wspace=.36)
    label_footer(fig,'34-house aggregate, proposed 92395 STAR, optimized dispatch. Identical 0.95–1.05 pu and 100% loading screens; 2025 full-year replays.',.06)
    emit(fig,out,'P2_higher_ss_pf_length_robustness')


def fig_p3(ac,gr,out):
    """Topology dependence of four-house 92395 gross and two investment tiers."""
    fig,ax=plt.subplots(figsize=(10.3,5.2))
    colors={'Gross demand':'#697783','Minimum-cost PV+BESS':COL['94022'],'Higher-SS PV+BESS':'#229379'}
    marks={'Gross demand':'o','Minimum-cost PV+BESS':'s','Higher-SS PV+BESS':'D'}
    for topo,linestyle in (('STAR','--'),('MST','-')):
        for label,tier in (('Gross demand',None),('Minimum-cost PV+BESS','min_cost'),('Higher-SS PV+BESS','ss90')):
            vals=[]
            for length in (1.,1.3,1.6):
                if tier is None:
                    sl=gr[(gr.transformer.astype(str)=='92395')&(gr.topology.str.upper()==topo)&(np.isclose(gr.PF,.95))&(np.isclose(gr.length_factor,length))]
                    # Gross 92395 is independently modelled once with identical A0/A1 cohorts.
                    if len(sl)!=1:raise AssertionError('Expected single 92395 gross case '+str((topo,length,len(sl))))
                    val=int(sl.iloc[0].AC_infeasible_hours)
                else:
                    sl=ac[(ac.transformer.astype(str)=='92395')&(ac.topology.str.upper()==topo)&(ac.tier==tier)&(ac.dispatch=='optimized')&(np.isclose(ac.pf,.95))&(np.isclose(ac.length_factor,length))]
                    if len(sl)!=1:raise AssertionError('Expected single 92395 DER case '+str((topo,tier,length,len(sl))))
                    val=int(sl.iloc[0].infeasible_hours)
                vals.append(val)
            if topo=='STAR' and all(z==0 for z in vals):
                # Plot a single explicit STAR all-zero reference, not three redundant identical curves.
                continue
            ax.plot((1.,1.3,1.6),vals,marker=marks[label],lw=2.25,ms=7,
                    color=colors[label],label=f'MST: {label}',zorder=3)
            ax.annotate(str(vals[-1]),(1.6,vals[-1]),xytext=(13,13 if tier=='min_cost' else (-13 if tier=='ss90' else 0)),textcoords='offset points',fontsize=10,fontweight='bold',va='center',color=colors[label])
    ax.plot([1.,1.6],[0.,0.],ls='--',lw=1.8,color='#8053a5',label='STAR: all three cases, 0 hours')
    ax.set_xlim(.94,1.72);ax.set_ylim(-12,305)
    ax.set_xticks([1.,1.3,1.6],['×1.0','×1.3','×1.6'])
    ax.set_ylabel('Hours failing main AC feasibility screen')
    ax.set_xlabel('Proposed feeder-length multiplier')
    ax.set_title('Four-house 92395: shorter proposed wiring can increase voltage risk',loc='left',pad=12)
    ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    ax.legend(loc='upper left',frameon=False,fontsize=9)
    fig.subplots_adjust(left=.10,right=.86,top=.84,bottom=.24)
    fig.text(.10,.125,'Proposed total cable at ×1.0: STAR 1,153 m; MST 550 m. Same four households, PF 0.95, optimized dispatch.',fontsize=9,color=DARK)
    fig.text(.10,.076,'Not a real routing or installation-cost comparison. Both topologies require construction, conductor and protection evidence.',fontsize=8,color=GREY)
    emit(fig,out,'P3_92395_star_mst_pvbess')


def fig_p4(agg,en,out):
    """Four aggregate architecture points, not continuous Pareto frontier."""
    # Exact five-system aggregation: four archived-ref cohorts and A0 92395 new four-house.
    ids={'A0':{'94022':10,'106039':12,'113699':4,'85398':4,'92395':4},
         'A1':{'94022':8,'106039':11,'113699':6,'85398':5,'92395':4}}
    fig,ax=plt.subplots(figsize=(9.4,5.0))
    summary=[]
    for sc in ('A0','A1'):
        for tier in ('min_cost','ss90'):
            picked=[]
            for t in ('94022','106039','113699','85398','92395'):
                fam='four_house_new' if t=='92395' else 'archived_reference'
                row=en[(en.scenario==sc if t!='92395' else en.scenario=='A0')&(en.transformer.astype(str)==t)&(en.tier==tier)&(en.hardware_family==fam)]
                if len(row)!=1:raise AssertionError(f'Invalid economic source {sc}/{t}/{tier} (got {len(row)})')
                picked.append(row.iloc[0])
            demand=sum(float(r.demand_kwh) for r in picked)
            imports=sum(float(r.imports_kwh) for r in picked)
            cost=sum(float(r.effective_cost_usd) for r in picked)
            assert abs(demand-64532)<1e-7
            violations=int(exact(agg,scenario=sc,tier=tier,pf=.98,length_factor=1.).five_territory_pvbess_transformer_violation_hours)
            ss=100*(1-imports/demand)
            summary.append(dict(scenario=sc,tier=tier,annual_cost_usd=cost,self_sufficiency_pct=ss,violation_territory_hours=violations))
            color=COL['94022'] if sc=='A0' else COL['106039']
            marker='o' if tier=='min_cost' else 'D'
            ax.scatter(cost,ss,s=150,c=color,marker=marker,zorder=3,edgecolor='white',linewidth=1.2)
            positions={('A0','min_cost'):(13120,84.4),
                       ('A1','min_cost'):(14020,79.9),
                       ('A0','ss90'):(15000,95.2),
                       ('A1','ss90'):(14100,88.7)}
            annotation=positions[(sc,tier)]
            lab=f'{sc} {"minimum cost" if tier=="min_cost" else "higher SS"}\n${cost:,.0f}/yr | {violations} AC h'
            ax.annotate(lab,xy=(cost,ss),xytext=annotation,textcoords='data',
                        fontsize=9,color=DARK,ha='left',va='center',
                        arrowprops=dict(arrowstyle='-',lw=.65,color='#8994a1',shrinkA=3,shrinkB=5))
    ax.set_xlim(13000,15800);ax.set_ylim(78,97)
    ax.set_yticks([80,85,90,95]);ax.set_xticks([13000,13500,14000,14500,15000,15500])
    ax.set_xticklabels(['13,000','13,500','14,000','14,500','15,000','15,500'])
    ax.axhline(90,color='#7e8792',ls=':',lw=1.1,zorder=0)
    ax.grid(axis='both',alpha=.16);ax.set_axisbelow(True)
    ax.set_xlabel('Modelled annual equipment + grid electricity cost (USD/year)')
    ax.set_ylabel('Achieved annual energy self-sufficiency (%)')
    ax.set_title('34-house configuration trade-off: annual cost, energy and residual AC risk',loc='left',pad=14)
    fig.subplots_adjust(left=.12,right=.95,top=.85,bottom=.26)
    fig.text(.12,.125,'Four discrete architecture references, not a continuous Pareto frontier. PV+BESS AC screen: PF 0.98, route ×1.0, 92395 STAR.',fontsize=8,color=GREY)
    fig.text(.12,.08,'Annual costs exclude verified LV civil works, interconnection and loss-aware optimization. The 34 houses use five independent shared systems.',fontsize=8,color=GREY)
    emit(fig,out,'P4_cost_self_sufficiency_ac_tradeoff')
    return summary


def local_geometry(repo):
    if repo is None:return None
    d=repo/'case1/studies/epm_gis_pandapower_v1/data'
    needed=(d/'houses_candidate_associations.csv',d/'transformers_evidence.csv',d/'epm_network_relevant_sanitized.geojson')
    if not all(p.exists() for p in needed):return None
    houses=pd.read_csv(needed[0]);trafos=pd.read_csv(needed[1])
    obj=json.loads(needed[2].read_text(encoding='utf-8'))
    lines=[]
    for feat in obj['features']:
        prop=feat.get('properties',{})
        if prop.get('layer')!='EPM LV':continue
        node=str(prop.get('NODO_TRANSFORM_CONN'))
        if node not in set(TID_TO_NODE.values()):continue
        cs=feat['geometry']['coordinates']
        if feat['geometry']['type']!='LineString':continue
        for a,b in zip(cs[:-1],cs[1:]):
            lines.append(dict(node=node,fid=str(prop.get('G3E_FID')),lon1=a[0],lat1=a[1],lon2=b[0],lat2=b[1]))
    return houses,trafos,pd.DataFrame(lines),'Original GitLab GIS source in local checkout'


def backup_geometry():
    folder=HERE/'source_geometry'
    houses=pd.read_csv(folder/'houses_candidate_associations.csv')
    trafos=pd.read_csv(folder/'transformers_evidence.csv')
    lines=pd.read_csv(folder/'epm_lv_segments_compact.csv')
    return houses,trafos,lines,'Rounded read-only GitLab GIS coordinate extract (2026-11-16 preview)'


def xy(lon,lat,lat0=6.24):
    # Local plotting coordinates for this figure only, not conductor-length cost estimates.
    return (float(lon)+75.01)*111.195*np.cos(np.deg2rad(lat0)),(float(lat)-6.24)*111.195


def nearest_tap(house,linelist):
    px,py=xy(house.longitude,house.latitude)
    best=(1.e9,None)
    for row in linelist.itertuples():
        ax,ay=xy(row.lon1,row.lat1); bx,by=xy(row.lon2,row.lat2)
        den=(bx-ax)**2+(by-ay)**2
        t=max(0,min(1,((px-ax)*(bx-ax)+(py-ay)*(by-ay))/den)) if den>0 else 0
        tx=ax+t*(bx-ax);ty=ay+t*(by-ay)
        d=(px-tx)**2+(py-ty)**2
        if d<best[0]:best=(d,(tx,ty))
    return best[1]


def fig_g4(e,out,repo=None):
    with (e/'input_manifest_v6_2.json').open(encoding='utf-8') as fh:manifest=json.load(fh)
    assert manifest['population_houses']==35
    grps=manifest['groups']
    assert len(grps['A0'])==len(grps['A1'])==6
    shifts={h:(manifest['changed_houses'][h]['from'],manifest['changed_houses'][h]['to']) for h in manifest['changed_houses']}
    assert set(shifts)=={'H03','H06','H13'}
    inputs=local_geometry(repo) or backup_geometry()
    houses,trafos,lines,source=inputs
    houses['house_id']=houses['house_id'].astype(str)
    trafos['transformer_number']=trafos['transformer_number'].astype(str)
    lines['node']=lines['node'].astype(str)
    assert len(houses)==35 and set(houses.house_id)==set(grps['A0']['94022']+grps['A0']['106039']+grps['A0']['113699']+grps['A0']['85398']+grps['A0']['92395']+grps['A0']['98380'])
    assert set(TID_TO_NODE.values()).issuperset(set(lines.node))
    fig,axs=plt.subplots(1,2,figsize=(15.8,7.8),sharex=True,sharey=True)
    h_lookup={h.house_id:h for h in houses.itertuples()}
    t_lookup={t.transformer_number:t for t in trafos.itertuples()}
    for ax,variant in zip(axs,('A0','A1')):
        for tid in ('94022','106039','113699','85398','92395','98380'):
            color=COL[tid]
            seg=lines[lines.node==TID_TO_NODE[tid]]
            for line in seg.itertuples():
                ax.plot([xy(line.lon1,line.lat1)[0],xy(line.lon2,line.lat2)[0]],
                    [xy(line.lon1,line.lat1)[1],xy(line.lon2,line.lat2)[1]],
                    color=color,alpha=.9,lw=2.7,zorder=2,solid_capstyle='round')
            members=grps[variant][tid]
            for h in members:
                r=h_lookup[h];coord=xy(r.longitude,r.latitude)
                if len(seg)>0:
                    tap=nearest_tap(r,seg)
                    ax.plot([coord[0],tap[0]],[coord[1],tap[1]],color=color,
                            lw=.9,ls=':',alpha=.53,zorder=1)
                ax.scatter(*coord,s=27,color=color,edgecolor='white',linewidth=.5,zorder=4)
                if h in shifts:
                    ax.scatter(*coord,s=100,facecolors='none',edgecolors=DARK,linewidths=1.35,zorder=6)
                ax.annotate(h.replace('H',''),coord,xytext=(3,3),textcoords='offset points',
                            fontsize=6.5,color=DARK if h in shifts else GREY,
                            fontweight='bold' if h in shifts else 'normal')
            tf=t_lookup[tid];star=xy(tf.longitude,tf.latitude)
            ax.scatter(*star,marker='*',color=color,edgecolor=DARK,linewidth=.9,s=160,zorder=7)
        ax.set_aspect('equal',adjustable='box')
        ax.set_title(f'{variant}  |  {"Original provisional associations" if variant=="A0" else "Nearest-transformer reassignment"}',
                    fontsize=12,loc='left',pad=11)
        ax.set_xticks([]);ax.set_yticks([])
        for spine in ax.spines.values():spine.set_visible(False)
    fig.suptitle('EPM LV backbone and 35 provisional household connections: A0 versus A1',x=.045,y=.995,ha='left',fontsize=14)
    handles=[Line2D([0],[0],color=COL[t],lw=2.5,label=f'{t}  ({len(grps["A0"][t])} → {len(grps["A1"][t])} houses)') for t in ('94022','106039','113699','85398','92395','98380')]
    handles += [Line2D([0],[0],color='#637080',lw=2.5,label='Solid: EPM-mapped LV sections'),
        Line2D([0],[0],color='#637080',lw=1.3,ls=':',label='Dotted: assumed direct service tap'),
        Line2D([0],[0],marker='o',markerfacecolor='none',markeredgecolor=DARK,lw=0,label='Black ring: H03 / H06 / H13 reassigned'),
        Line2D([0],[0],marker='*',color='#637080',lw=0,markersize=10,label='Star: transformer')]
    fig.legend(handles=handles,ncol=5,loc='lower center',bbox_to_anchor=(.5,.113),frameon=False,fontsize=8.5)
    fig.subplots_adjust(left=.025,right=.99,top=.93,bottom=.25,wspace=.05)
    fig.text(.045,.055,'No extracted EPM LV segments for transformer 92395. Its STAR/MST layouts are separately proposed, not shown here as mapped conductors.',fontsize=8,color=DARK)
    fig.text(.045,.025,source+' | Geographic nearest transformer is the membership rule; service tap geometry is for illustration only.',fontsize=7.7,color=GREY)
    emit(fig,out,'G4_epm_mapped_lv_A0_vs_A1')
    return {'source':source,'changed_houses':shifts,'n_households':len(houses),'n_lv_segments':len(lines)}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evidence-dir',type=Path,default=HERE/'evidence')
    ap.add_argument('--out',type=Path,default=HERE/'figures')
    ap.add_argument('--repo-root',type=Path,default=None,help='Optional real local GitLab checkout; preferred for G4 source coordinates')
    ap.add_argument('--only',choices=['all','summary','topology'],default='all')
    args=ap.parse_args(argv)
    look();agg,ac,gr,en=validate(args.evidence_dir)
    summary=[]
    if args.only in ('all','summary'):
        fig_p1(agg,args.out);fig_p2(agg,args.out);fig_p3(ac,gr,args.out)
        summary=fig_p4(agg,en,args.out)
    provenance={}
    if args.only in ('all','topology'):provenance=fig_g4(args.evidence_dir,args.out,args.repo_root)
    manifest={'status':'FIGURE_ONLY_READ_ONLY_NO_NUMERIC_SIMULATIONS',
      'derived_source':'16-Nov-2026 independently reviewed Study A 476-case compact ZIP + gross 90-case evidence',
      'figure_names':sorted(p.name for p in args.out.glob('*.png')),
      'economic_architecture_points':summary,
      'topology':provenance,
      'known_gates':['A1 106039 annual overload remains','Causal year-end SOC drift two borrowed four-house cases',
       'Missing hourly data prevents monthly-energy figure and exact violation-hour diagnosis',
       'Daylight Q 0.25 assumed; as-built topology and equipment not verified']}
    with (args.out/'FIGURE_MANIFEST.json').open('w',encoding='utf-8') as fh:json.dump(manifest,fh,indent=2,ensure_ascii=False)
    print('Figure output',args.out, 'PNGs',len(manifest['figure_names']))
    return 0

if __name__=='__main__':raise SystemExit(main())
