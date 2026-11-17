import zipfile,io,hashlib,json,pandas as pd,numpy as np
p='/mnt/data/StudyA_A0_94022_Sequenced_Trial_v1.zip'
ref='/mnt/data/SEEDExchange_StudyA_A0_106039_Validated_2026-11-16/PORTFOLIO_432_POST_A0_106039_OVERLAY.csv'
dfref=pd.read_csv(ref,dtype={'transformer':str})
with zipfile.ZipFile(p) as z:
 assert z.testzip() is None
 j=json.loads(z.read('TRIAL_MANIFEST.json'))
 fs=pd.read_csv(io.BytesIO(z.read('NINE_FACTOR_ANNUAL_REUSE.csv')))
 ac=pd.read_csv(io.BytesIO(z.read('CHANGED_HOURS_FINAL_AC.csv')))
 shifts=pd.read_csv(io.BytesIO(z.read('ADOPTED_SHIFT_EVENTS.csv')))
 unresolved=pd.read_csv(io.BytesIO(z.read('UNRESOLVED_EVENTS.csv')))
 tests=[]
 def check(v,name):
  print(('PASS' if v else 'FAIL'),name)
  tests.append((name,bool(v)))
 check(j['adopted_shift_count']==len(shifts)==80,'80 adopted')
 check(j['unresolved_event_count']==len(unresolved)==32,'32 unresolved')
 check(j['selected_event_count']==112,'112 selected')
 check(len(fs)==36 and not fs.duplicated(['case','dispatch','pf','length_factor']).any(),'36 unique factors')
 check(len(ac)==1368 and not ac.duplicated(['case','dispatch','pf','length_factor','timestamp_lst']).any(),'1368 unique AC changed samples')
 check(ac.ac_feasible.eq(True).all() and ac.min_v_pu.min()>=.95-1e-8 and ac.max_trafo_pct.max()<=100+1e-8,'changed AC all within bounds')
 check((fs.annual_hours_accounted_for==8760).all(),'factor annual coverage')
 check((fs.trial_bad_hours <= fs.original_bad_hours).all(),'no case worsening')
 check(set(fs['pf'])=={.95,.98,1.0} and set(fs['length_factor'])=={1.,1.3,1.6},'9 stress settings')
 check(len(ac.groupby(['case','dispatch','pf','length_factor']))==36,'all factor groups have changed AC')
 keys=[*zip(fs.case,fs.dispatch,fs.pf,fs.length_factor)]
 check(len(set(keys))==36,'36 keys')
 for r in fs.itertuples():
  tier='min_cost' if 'min_cost' in r.case else 'ss90'
  m=(dfref.scenario=='A0') & (dfref.transformer=='94022') & (dfref.tier==tier) & (dfref.hardware_family=='archived_reference') & (dfref.topology=='mapped') &(dfref.dispatch==r.dispatch) &(abs(dfref.pf-r.pf)<1e-9) &(abs(dfref.length_factor-r.length_factor)<1e-9)
  check(bool(m.sum()==1 and int(dfref[m].iloc[0].adjusted_bad_hours)==int(r.original_bad_hours)),'prior count '+r.case+'/'+r.dispatch+'/'+str(r.pf)+'/'+str(r.length_factor))
 # test final changed-hour count = 9*unique affected hours per group
 summary=[]; dates=pd.date_range('2025-01-01',periods=8760,freq='h')
 for it in j['candidate_files']:
  raw=z.read(it['candidate_file']);s=hashlib.sha256(raw).hexdigest();
  check(s==it['sha256'],'sha file '+it['candidate_file'])
  df=pd.read_csv(io.BytesIO(raw),parse_dates=['timestamp_lst'])
  check(df.timestamp_lst.equals(pd.Series(dates,name='timestamp_lst')),'8760 consecutive '+it['candidate_file'])
  c=df.battery_charge_dc_kw.to_numpy();d=df.battery_discharge_dc_kw.to_numpy();soc=df.battery_soc_usable_kwh.to_numpy();eta=np.sqrt(.95)
  err_soc=np.max(np.abs(soc[1:]-soc[:-1]-(eta*c-d/eta)[1:]))
  err_ac=np.max(np.abs(df.inverter_ac_kw+df.grid_import_kw+df.unserved_kw-df.grid_export_kw-df.demand_kw))
  err_dc=np.max(np.abs(df.pv_dc_available_kw-df.curtailed_pv_dc_kw+d-c-df.inverter_ac_kw/.95))
  check(max(err_soc,err_ac,err_dc)<1e-6,'energy balances '+it['candidate_file'])
  check(abs(df.grid_export_kw).max()<1e-8 and abs(df.unserved_kw).max()<1e-8,'zero export ENS '+it['candidate_file'])
  check((df.grid_import_kw>=-1e-8).all() and (df.battery_charge_dc_kw>=-1e-8).all() and (df.battery_discharge_dc_kw>=-1e-8).all(),'nonnegative flows '+it['candidate_file'])
  for x,v in [('min_soc_kwh',soc.min()),('max_soc_kwh',soc.max()),('end_soc_kwh',soc[-1]),('annual_import_kwh',df.grid_import_kw.sum()),('annual_pv_curtailment_dc_kwh',df.curtailed_pv_dc_kw.sum())]:
   check(abs(v-it['energy_original'][x])<1e-6 and abs(v-it['energy_candidate'][x])<1e-6,'manifest metric '+it['candidate_file']+'/'+x)
  tier='min_cost' if 'min_cost' in it['case'] else 'ss90'; socfloor=1.374 if tier=='min_cost' else 1.832
  check(soc.min()>=socfloor-1e-7,'SOC 20% floor '+it['candidate_file'])
  if it['dispatch']=='optimized':
   check(np.max(np.abs(df.pcc_p_kw-df.grid_import_kw))<1e-6,'PCC P alignment '+it['candidate_file'])
  summary.append({'case':it['case'],'dispatch':it['dispatch'],'sha256':s,'soc_err':err_soc,'ac_err':err_ac,'dc_err':err_dc,'min_soc':soc.min(),'end_soc':soc[-1],'annual_import':df.grid_import_kw.sum(),'curtailed_pv_dc':df.curtailed_pv_dc_kw.sum(),'n_shifts':len(shifts[(shifts.case==it['case'])&(shifts.dispatch==it['dispatch'])]),'n_unresolved':len(unresolved[(unresolved.case==it['case'])&(unresolved.dispatch==it['dispatch'])])})
 print('total pass',sum(x[1] for x in tests),'/',len(tests))
 print('min changed AC voltage',ac.min_v_pu.min(),'max load',ac.max_trafo_pct.max())
 print('annual original total',fs.original_bad_hours.sum(),'after',fs.trial_bad_hours.sum())
 print('unique unresolved clock times',unresolved.event_timestamp.nunique())
 print('changed hour group sizes',ac.groupby(['case','dispatch']).size().to_dict())
 print('shift target unique',not shifts.duplicated(['case','dispatch','target_hour']).any())
 print('group summary',pd.DataFrame(summary).to_string(index=False))
 assert all(v for _,v in tests),'Some tests failed'
