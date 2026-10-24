"""SEEDExchange El Arenal Case 1 v2, script-first preliminary screening.

Uses unchanged input XML and hourly NASA file. The preferred PV path is pvlib GHI+Erbs
matching v18/v5. An explicitly labelled NOAA/Erbs approximation runs when pvlib is
unavailable, and must NOT be interpreted as a reproduction of v18/v5.
The dispatch is causal and local-first; grid checks are PCC algebra only, not pandapower.
The hardware map covers split-phase Deye ratings, but does not verify actual PV strings.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'results'
OUT.mkdir(exist_ok=True)
NASA_PATH = ROOT / 'NASA_POWER_SanRafael_hourly_2025.csv'
META_PATH = ROOT / 'NASA_POWER_SanRafael_hourly_2025_metadata.json'
XML_PATH = ROOT / 'SimulacionTampico1k(1).xml'
REFERENCE_PANDAPOWER_NASA_KWH = 7054.003295  # Saved v5 output. Comparison only.
SEED = 20250913
PF = .95
TRAFO_KVA = 5.
VAT = 14250./11974.79  # Quote subtotal / total. Do not apply twice.
LOAD_MIN_PU, LOAD_MAX_PU = .97, 1.03


def hashfile(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def read_inputs():
    df=pd.read_csv(NASA_PATH, parse_dates=['timestamp_lst']).set_index('timestamp_lst')
    exp=pd.date_range('2025-01-01',periods=8760,freq='h')
    assert len(df)==8760 and df.index.equals(exp), 'NASA 2025 timestamps incomplete or misaligned'
    for c in ['ALLSKY_SFC_SW_DWN','ALLSKY_SFC_SW_DIFF','ALLSKY_SFC_SW_DNI','CLRSKY_SFC_SW_DWN','T2M','WS10M']:
        assert c in df and pd.to_numeric(df[c],errors='coerce').notna().all() and (df[c]>-900).all(),f'Bad NASA column {c}'
    meta=json.loads(META_PATH.read_text())
    assert meta['time_standard']=='LST' and meta['start']=='20250101' and meta['end']=='20251231'
    sd=ET.parse(XML_PATH).getroot().find('system_description')
    assert sd is not None
    return df,meta,sd


def build_stochastic_load(sd, idx, houses=8,seed=SEED):
    """Exact v18 algorithm: per-house day/hour perturbation, clipping and annual renormalization."""
    d={'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
    vals={}
    for daytype in ['weekday','weekend']:
        for month in d:
            s=sd.findtext(f'primary_load/data/monthly/daily_profiles/{month}/{daytype}/float_array')
            vals[(d[month],daytype)]=np.array([float(z) for z in s.split()])
    shape=np.array([vals[(x.month,'weekend' if x.weekday()>=5 else 'weekday')][x.hour] for x in idx])
    annual_total=float(sd.findtext('primary_load/scaled_annual_average'))*365.0
    shape=shape*annual_total/shape.sum()
    daily_sigma=float(sd.findtext('primary_load/data/monthly/daily_noise'))/100
    hour_sigma=float(sd.findtext('primary_load/data/monthly/hourly_noise'))/100
    seed_seq=np.random.SeedSequence(seed)
    rngs=[np.random.default_rng(x) for x in seed_seq.spawn(houses)]
    frame=pd.DataFrame(index=idx)
    frame['deterministic_load_4hh_kw']=shape
    for i,rng in enumerate(rngs,1):
        daily_delta=rng.normal(0.,daily_sigma,size=365)
        hourly_delta=rng.normal(0.,hour_sigma,size=8760)
        alpha=np.maximum(1.+daily_delta[idx.dayofyear.to_numpy()-1]+hourly_delta,0.)
        vec=shape/4*alpha
        vec*=annual_total/4/vec.sum()
        frame[f'house_{i}_kw']=vec
        frame[f'load_{i}hh_kw']=frame[[f'house_{j}_kw' for j in range(1,i+1)]].sum(axis=1)
    assert abs(frame['load_4hh_kw'].sum()-7592)<1e-7
    assert np.isclose(frame['load_4hh_kw'].max(),2.166677435937405,atol=1e-10), 'Stochastic parity with v18 failed'
    return frame


def approximate_nasa_pv(df):
    """Independent NOAA solar-position + Erbs approximation, NOT pvlib parity."""
    idx=df.index
    doy=idx.dayofyear.to_numpy(); hr=idx.hour.to_numpy()+0.5
    phi=np.deg2rad(6.2523)
    gamma=2*np.pi/365*(doy-1+(hr-12)/24)
    decl=(.006918-.399912*np.cos(gamma)+.070257*np.sin(gamma)-.006758*np.cos(2*gamma)+.000907*np.sin(2*gamma)-.002697*np.cos(3*gamma)+.00148*np.sin(3*gamma))
    eot=229.18*(.000075+.001868*np.cos(gamma)-.032077*np.sin(gamma)-.014615*np.cos(2*gamma)-.040849*np.sin(2*gamma))
    lon=-75.0143
    ha=np.deg2rad(((hr*60+eot+4*lon+300)/4)-180)
    cosz=np.clip(np.sin(phi)*np.sin(decl)+np.cos(phi)*np.cos(decl)*np.cos(ha),0,1)
    zen=np.rad2deg(np.arccos(cosz))
    ghi=df['ALLSKY_SFC_SW_DWN'].to_numpy(dtype=float)
    extra=1366.1*(1+.033*np.cos(2*np.pi*doy/365))
    kt=np.clip(np.divide(ghi,extra*cosz,out=np.zeros_like(ghi),where=cosz>0),0,1)
    dfactor=np.where(kt<=.22,1-.09*kt,np.where(kt<=.8,.9511-.1604*kt+4.388*kt**2-16.638*kt**3+12.336*kt**4,.165))
    dhi=np.clip(ghi*dfactor,0,ghi)
    dni=np.divide(ghi-dhi,cosz,out=np.zeros_like(ghi),where=(cosz>.05234)&(zen<=87))
    tilt=np.deg2rad(5)
    south_component=np.sin(phi)*np.cos(decl)*np.cos(ha)-np.cos(phi)*np.sin(decl)
    cosinc=np.clip(cosz*np.cos(tilt)+south_component*np.sin(tilt),0,None)
    poa=dni*cosinc+dhi*(1+np.cos(tilt))/2+ghi*.2*(1-np.cos(tilt))/2
    temp_cell=df['T2M'].to_numpy(dtype=float)+(45-20)*poa/800
    dc_per_kwp=poa/1000*.80*np.maximum(1-.003*(temp_cell-25),0)
    return pd.Series(dc_per_kwp,index=idx,name='pv_dc_per_kwp'),{'method':'independent_NOAA_Erbs_approximation_UNVERIFIED','annual_ghi_kwh_m2':round(ghi.sum()/1000,3),'poa_to_ghi_ratio':round(poa.sum()/ghi.sum(),6),'annual_dc_kwh_at_5p22':round(float((5.22*dc_per_kwp).sum()),3)}


def pvlib_nasa_pv(df):
    import pvlib
    idx=df.index; ts=idx.tz_localize('Etc/GMT+5')+pd.Timedelta(minutes=30)
    sol=pvlib.solarposition.get_solarposition(ts,6.2523,-75.0143,altitude=1291.33)
    ghi=df['ALLSKY_SFC_SW_DWN'].to_numpy(dtype=float)
    erbs=pvlib.irradiance.erbs(ghi=ghi,zenith=sol['zenith'].to_numpy(),datetime_or_doy=ts)
    poa=pvlib.irradiance.get_total_irradiance(surface_tilt=5,surface_azimuth=180,
      solar_zenith=sol['apparent_zenith'].to_numpy(),solar_azimuth=sol['azimuth'].to_numpy(),
      dni=np.clip(np.asarray(erbs['dni']),0,None),dhi=np.clip(np.asarray(erbs['dhi']),0,None),
      ghi=ghi,albedo=.2,model='isotropic')['poa_global']
    poa=np.asarray(poa,dtype=float)
    tc=df['T2M'].to_numpy()+(45-20)*poa/800
    out=pd.Series(np.maximum(0,poa)/1000*.8*np.maximum(0,1-.003*(tc-25)),index=idx,name='pv_dc_per_kwp')
    return out,{'method':'original_v18_v5_PVLIB_GHI_ERBS_MIDPOINT','annual_ghi_kwh_m2':round(ghi.sum()/1000,3),'poa_to_ghi_ratio':round(poa.sum()/ghi.sum(),6),'annual_dc_kwh_at_5p22':round(float((5.22*out).sum()),3)}




def resource_components(df, method, pv_per_kwp):
    """Create one-hour resource and PV conversion chain for plotting.

    POA matches the selected PV calculation: either pvlib GHI/Erbs at the
    local-solar-time midpoint or the explicitly unverified approximation.
    """
    idx=df.index
    ghi=df['ALLSKY_SFC_SW_DWN'].to_numpy(dtype=float)
    if method=='original_v18_v5_PVLIB_GHI_ERBS_MIDPOINT':
        import pvlib
        ts=idx.tz_localize('Etc/GMT+5')+pd.Timedelta(minutes=30)
        sol=pvlib.solarposition.get_solarposition(ts,6.2523,-75.0143,altitude=1291.33)
        erbs=pvlib.irradiance.erbs(ghi=ghi,zenith=sol['zenith'].to_numpy(),datetime_or_doy=ts)
        poa=np.asarray(pvlib.irradiance.get_total_irradiance(
            surface_tilt=5,surface_azimuth=180,
            solar_zenith=sol['apparent_zenith'].to_numpy(),solar_azimuth=sol['azimuth'].to_numpy(),
            dni=np.clip(np.asarray(erbs['dni']),0,None),dhi=np.clip(np.asarray(erbs['dhi']),0,None),
            ghi=ghi,albedo=.2,model='isotropic')['poa_global'],dtype=float)
    else:
        # Retain the *same* NOAA/Erbs equations as approximate_nasa_pv.
        doy=idx.dayofyear.to_numpy();hr=idx.hour.to_numpy()+.5
        phi=np.deg2rad(6.2523)
        gamma=2*np.pi/365*(doy-1+(hr-12)/24)
        decl=(.006918-.399912*np.cos(gamma)+.070257*np.sin(gamma)-.006758*np.cos(2*gamma)+.000907*np.sin(2*gamma)-.002697*np.cos(3*gamma)+.00148*np.sin(3*gamma))
        eot=229.18*(.000075+.001868*np.cos(gamma)-.032077*np.sin(gamma)-.014615*np.cos(2*gamma)-.040849*np.sin(2*gamma))
        ha=np.deg2rad(((hr*60+eot+4*(-75.0143)+300)/4)-180)
        cosz=np.clip(np.sin(phi)*np.sin(decl)+np.cos(phi)*np.cos(decl)*np.cos(ha),0,1)
        zen=np.rad2deg(np.arccos(cosz))
        extra=1366.1*(1+.033*np.cos(2*np.pi*doy/365))
        kt=np.clip(np.divide(ghi,extra*cosz,out=np.zeros_like(ghi),where=cosz>0),0,1)
        dfactor=np.where(kt<=.22,1-.09*kt,np.where(kt<=.8,.9511-.1604*kt+4.388*kt**2-16.638*kt**3+12.336*kt**4,.165))
        dhi=np.clip(ghi*dfactor,0,ghi)
        dni=np.divide(ghi-dhi,cosz,out=np.zeros_like(ghi),where=(cosz>.05234)&(zen<=87))
        tilt=np.deg2rad(5)
        south_component=np.sin(phi)*np.cos(decl)*np.cos(ha)-np.cos(phi)*np.sin(decl)
        cosinc=np.clip(cosz*np.cos(tilt)+south_component*np.sin(tilt),0,None)
        poa=dni*cosinc+dhi*(1+np.cos(tilt))/2+ghi*.2*(1-np.cos(tilt))/2
    cell_temp=df['T2M'].to_numpy(dtype=float)+25*poa/800
    dc=np.asarray(pv_per_kwp,dtype=float)
    expected=np.maximum(poa,0)/1000*.8*np.maximum(0,1-.003*(cell_temp-25))
    if not np.allclose(dc,expected,atol=5e-4):
        raise AssertionError('Solar conversion diagnostics do not reproduce the actual PV DC series')
    return pd.DataFrame({'ghi_wh_m2':ghi,'poa_wh_m2':poa,
            'cell_temperature_c':cell_temp,'ideal_poa_kw_per_kwp':poa/1000,
            'pv_dc_kw_per_kwp':dc,'pv_ac_equiv_kw_per_kwp':dc*EFF_INV},index=idx)


# Deye manufacturer's published SUN-...SG02LP2-US-AM2/AM3 family.
# Limits shown here are *DC input nameplate power only*. They are NOT proof of
# module string Voc, Isc, MPPT configuration, approval or battery compatibility.
INVERTER_OPTIONS = {
    5.0: {'model': 'SUN-5K-SG02LP2-US-AM2', 'max_pv_kwp': 7.5, 'battery_max_current_a': 120},
    6.0: {'model': 'SUN-6K-SG02LP2-US-AM2', 'max_pv_kwp': 9.0, 'battery_max_current_a': 135},
    7.6: {'model': 'SUN-7.6K-SG02LP2-US-AM2', 'max_pv_kwp': 11.4, 'battery_max_current_a': 190},
    8.0: {'model': 'SUN-8K-SG02LP2-US-AM2', 'max_pv_kwp': 12.0, 'battery_max_current_a': 190},
    10.0: {'model': 'SUN-10K-SG02LP2-US-AM3', 'max_pv_kwp': 15.0, 'battery_max_current_a': 220},
}
PV_PANEL_W = 435.
BATT_NOMINAL_KWH_4 = 19.2  # HOMER XML, not 4x 5.12 kWh nameplate
BATT_USABLE_KWH_4 = 17.3
EFF_INV = .95
EFF_BATT_ONEWAY = float(np.sqrt(.95))


def hardware_screen(panels: int, inverter_kva: float) -> dict:
    pv_kwp = panels * PV_PANEL_W / 1000
    spec = INVERTER_OPTIONS[inverter_kva]
    can_connect = pv_kwp <= spec['max_pv_kwp'] + 1e-10
    return {
        'inverter_model': spec['model'], 'inverter_kva': inverter_kva,
        'pv_kwp': pv_kwp, 'max_pv_input_kwp': spec['max_pv_kwp'],
        'dc_ac_ratio': pv_kwp / inverter_kva,
        'pv_input_rating_feasible': can_connect,
        'hardware_note': 'DC_input_Power_pass_only_Strings_and_grid_approval_UNVERIFIED' if can_connect
                         else 'FAIL_PV_input_nameplate_limit',
    }


def pf_reactive_kw(demand_kw, pf):
    if not 0 < pf <= 1: raise ValueError('PF must be in (0, 1]')
    return float(demand_kw * np.tan(np.arccos(pf)))


def trafo_p_limit_at_fixed_pf(loading_pu, pf, kva=TRAFO_KVA):
    """If PF at the transformer *itself* is held fixed: P_max = S_allow * PF."""
    return float(kva * loading_pu * pf)


def run_causal(load, pv_dc, *, modules=4, inverter_kva=5., cap_pu=.9,
               load_pf=.95, export_limit_kw=0., policy='conventional',
               charge_kw=5., discharge_kw=5., outage=None,
               critical_fraction=.5, initial_soc_kwh=None, q_control='unity'):
    """One-hour causal dispatch, central PV and battery on DC, split-phase AC equivalent.

    No forecast/lookahead. At the PCC, S=sqrt(P_grid**2+Q_grid**2).
    Household PF is used for Q_load. Inverter is unity Q unless q_control='compensate',
    a hypothetical Q-support sensitivity requiring an EPM-approved setting.
    Grid power to charge batteries is disabled; all battery charging uses excess solar.
    AC power limit and AC apparent limit both use inverter_kva (rated at unity PF).
    
    During outage, critical demand is allocated first. This is an idealized
    energy-availability calculation and does NOT certify islanding capability.
    """
    if not 0 <= cap_pu <= 1: raise ValueError('cap_pu must be 0..1')
    if policy not in ('conventional','fixed_reserve','adaptive_reactive'):
        raise ValueError('Unknown policy')
    if q_control not in ('unity','compensate'): raise ValueError('Unknown Q policy')
    if inverter_kva not in INVERTER_OPTIONS: raise ValueError('Use supported split-phase inverter')
    if not 0 <= critical_fraction <= 1: raise ValueError('Invalid critical fraction')
    if export_limit_kw is not None and export_limit_kw < 0: raise ValueError('Invalid export cap')
    if modules < 0 or modules != int(modules): raise ValueError('Invalid battery modules')
    assert load.index.equals(pv_dc.index), 'Load / solar timestamps must match'
    n=len(load)
    demand=np.asarray(load,dtype=float)
    pv=np.asarray(pv_dc,dtype=float)
    if (demand < 0).any() or (pv < 0).any(): raise ValueError('Negative load or PV')
    off=np.zeros(n,dtype=bool) if outage is None else np.asarray(outage,dtype=bool)
    assert len(off)==n
    usable=BATT_USABLE_KWH_4*modules/4
    soc=float(usable*.5 if initial_soc_kwh is None else initial_soc_kwh)
    if not 0<=soc<=usable:raise ValueError('Invalid initial SOC')
    # Approximate nominal DC operating voltage 48 V from the HOMER XML; BMS and
    # true operating voltage still need verification before implementing hardware.
    inverter_batt_max_kw=48*INVERTER_OPTIONS[inverter_kva]['battery_max_current_a']/1000
    bank_module_max_kw=4.8*modules # 100 A at 48 V per module (HOMER)
    bank_cap=min(inverter_batt_max_kw,bank_module_max_kw)
    ch_limit=min(float(charge_kw),bank_cap)
    dis_limit=min(float(discharge_kw),bank_cap)
    names=['grid_import_kw','grid_export_kw','inverter_ac_kw','inverter_q_kvar',
           'pv_dc_used_for_ac_kw','pv_dc_charge_kw','battery_dc_discharge_kw',
           'soc_usable_kwh','pv_dc_curtailed_kw','unserved_kw','critical_unserved_kw',
           'pcc_p_kw','pcc_q_kvar','transformer_s_kva','transformer_loading_pct',
           'inverter_s_kva','critical_load_kw','available_pv_dc_kw']
    out={x:np.zeros(n) for x in names}
    history=[]
    for t in range(n):
        ld=float(demand[t]); sun=float(pv[t]); is_off=bool(off[t])
        q_load=pf_reactive_kw(ld, load_pf)
        if policy=='fixed_reserve': reserve=.4*usable
        elif policy=='adaptive_reactive':
            prev=np.mean(history[-24:]) if history else 0.
            reserve=usable*(.55 if prev>.30 else .20)
        else:reserve=0.
        if is_off: reserve=0.  # release stored emergency energy

        # PV direct use, then PV -> battery DC charge, then battery DC -> AC for load.
        dc_direct=min(sun, ld/EFF_INV, inverter_kva/EFF_INV)
        p_direct=dc_direct*EFF_INV
        remaining_sun=sun-dc_direct
        charge=min(remaining_sun,ch_limit,max((usable-soc)/EFF_BATT_ONEWAY,0.)) if modules else 0.
        soc+=charge*EFF_BATT_ONEWAY
        remaining_sun-=charge
        batt_energy_available=max(soc-reserve,0)*EFF_BATT_ONEWAY
        batt_dc=min(max(ld-p_direct,0)/EFF_INV,
                    max(inverter_kva-p_direct,0)/EFF_INV,dis_limit,
                    batt_energy_available) if modules else 0.
        soc-=batt_dc/EFF_BATT_ONEWAY
        p_local=p_direct+batt_dc*EFF_INV
        assert p_local<=inverter_kva+1e-7

        # Conservative export calculation. Choose delivered PV export under
        # the inverter headroom and the 5 kVA transformer with Q_load present.
        # Export limits are *additional* controls, not a connection approval.
        export_potential=min(remaining_sun*EFF_INV,max(inverter_kva-p_local,0.))
        max_s_grid=TRAFO_KVA*cap_pu
        q_assumed=q_load if not is_off else 0.
        p_grid_bound=math.sqrt(max(0,max_s_grid**2-q_assumed**2))
        if is_off: p_export=0.
        else:
            absolute_cap=p_grid_bound if export_limit_kw is None else min(p_grid_bound,export_limit_kw)
            p_export=min(export_potential,absolute_cap)
        p_inv=p_local+p_export
        pdc_export=p_export/EFF_INV
        pv_curtailed=remaining_sun-pdc_export

        # Inverter Q compensation is non-forecast, optional and *not* baseline.
        # Reserve only instantaneous kVA headroom, do not generate fictitious Q.
        q_inv=0.
        if q_control=='compensate' and (p_inv>1e-8) and not is_off:
            available_q=math.sqrt(max(0,inverter_kva**2-p_inv**2))
            q_inv=min(q_load,available_q)
        q_pcc=q_load-q_inv if not is_off else 0.
        ens=0.

        # If the source is large enough to export, the q_assumed limit is
        # conservative since 0 <= q_pcc <= q_assumed.
        # For imports, solve maximum served load including its reactive demand.
        # Loads shed reduce Q proportionately. This avoids v1's overestimating Q
        # under load shedding. Grid demand is pld - inverter P.
        if is_off:
            imp=exp=0.
            served=min(ld,p_inv)
            ens=ld-served
            q_pcc=0.
        elif p_inv>ld:
            served=ld;ens=0.;imp=0.;exp=min(p_inv-ld,p_grid_bound)
            # No net curtail introduced here: selected p_export<=p_grid_bound,
            # and p_inv<=ld+p_grid_bound by construction.
            assert abs(exp-(p_inv-ld))<1e-7
        else:
            exp=0.
            served=ld
            imp=max(ld-p_inv,0.)
            if math.hypot(imp,q_pcc)>max_s_grid+1e-8:
                # Correct Q to the *actually served* load, at fixed PF.
                # Inverter Q compensation is reduced proportionally if needed.
                lo=0.;hi=ld
                for _ in range(55):
                    mid=(lo+hi)/2
                    p_grid=max(mid-p_inv,0.)
                    q_s=pf_reactive_kw(mid,load_pf)
                    q_i=min(q_inv,q_s)
                    if math.hypot(p_grid,q_s-q_i)<=max_s_grid:lo=mid
                    else:hi=mid
                served=lo; ens=ld-served; imp=max(served-p_inv,0)
                q_s=pf_reactive_kw(served,load_pf)
                q_inv=min(q_inv,q_s)
                q_pcc=q_s-q_inv
        pcc=imp-exp
        s_grid=0. if is_off else math.hypot(pcc,q_pcc)
        s_inv=math.hypot(p_inv,q_inv)
        assert s_grid<=max_s_grid+1e-6, (t, s_grid, max_s_grid)
        assert s_inv<=inverter_kva+1e-6
        assert -1e-8<=soc<=usable+1e-8
        assert abs((dc_direct+charge+pdc_export+pv_curtailed)-sun)<1e-6
        assert abs((imp+p_inv-exp+ens)-ld)<1e-6, 'AC balance failed'
        assert not (imp>1e-9 and exp>1e-9)
        crit=ld*critical_fraction
        critical_ens=max(ens-(ld-crit),0.)
        row={
          'grid_import_kw':imp,'grid_export_kw':exp,'inverter_ac_kw':p_inv,
          'inverter_q_kvar':q_inv,'pv_dc_used_for_ac_kw':dc_direct+pdc_export,
          'pv_dc_charge_kw':charge,'battery_dc_discharge_kw':batt_dc,
          'soc_usable_kwh':soc,'pv_dc_curtailed_kw':max(pv_curtailed,0),
          'unserved_kw':ens,'critical_unserved_kw':critical_ens,'pcc_p_kw':pcc,
          'pcc_q_kvar':q_pcc,'transformer_s_kva':s_grid,
          'transformer_loading_pct':s_grid/TRAFO_KVA*100,
          'inverter_s_kva':s_inv,'critical_load_kw':crit,
          'available_pv_dc_kw':sun,
        }
        for k,v in row.items():out[k][t]=v
        history.append(max(ld-sun*EFF_INV,0.))
    return pd.DataFrame(out,index=load.index)


def summary_kpis(res, demand, solar, *, panels, modules, inverter_kva,
                 strategy, allowed_loading, load_pf, export_cap, q_control,
                 label='annual'):
    served=demand.sum()-res.unserved_kw.sum()
    available=solar.sum()
    # Illustrative capital scaling from unchanged HOMER XML; *NOT* a quote for
    # alternative inverters, modules, DC strings, civil works or real EPM costs.
    capex=(3856*panels/12+4770*modules/4+3330*inverter_kva/5)*(11974.79/11956)
    factor=.06*1.06**25/(1.06**25-1)
    imports=res.grid_import_kw.sum();exports=res.grid_export_kw.sum()
    return {
       'scenario':label,'panels':panels,'pv_kwp':panels*.435,
       'bess_modules':modules,'bess_usable_kwh':modules*BATT_USABLE_KWH_4/4,
       'inverter_kva':inverter_kva,'inverter_model':INVERTER_OPTIONS[inverter_kva]['model'],
       'export_cap_kw': export_cap if export_cap is not None else 'trafo_only',
       'allowed_transformer_loading_pct':allowed_loading*100,
       'assumed_household_pf':load_pf,'q_control':q_control,'policy':strategy,
       'demand_kwh':float(demand.sum()),'served_kwh':float(served),
       'self_sufficiency_pct':float(100*(served-imports)/demand.sum()),
       'import_kwh':float(imports),'export_kwh':float(exports),
       'ens_kwh':float(res.unserved_kw.sum()),
       'critical_ens_kwh':float(res.critical_unserved_kw.sum()),
       'pv_available_dc_kwh':float(available),
       'pv_curtailment_pct':float(100*res.pv_dc_curtailed_kw.sum()/available) if available else 0.,
       'max_transformer_s_kva':float(res.transformer_s_kva.max()),
       'max_transformer_loading_pct':float(res.transformer_loading_pct.max()),
       'max_import_kw':float(res.grid_import_kw.max()),
       'max_export_kw':float(res.grid_export_kw.max()),
       'max_inverter_s_kva':float(res.inverter_s_kva.max()),
       'battery_charge_kwh_dc':float(res.pv_dc_charge_kw.sum()),
       'battery_discharge_kwh_dc':float(res.battery_dc_discharge_kw.sum()),
       'battery_throughput_proxy_kwh':float((res.pv_dc_charge_kw.sum()+res.battery_dc_discharge_kw.sum())/2),
       'approx_capex_usd':float(capex),
       'approx_annual_cost_usd_no_export':float(capex*factor+imports*.29+
                                        .052*(res.pv_dc_charge_kw.sum()+res.battery_dc_discharge_kw.sum())/2),
       'approx_annual_cost_usd_homer_sellback':float(capex*factor+imports*.29-exports*.275+
                                        .052*(res.pv_dc_charge_kw.sum()+res.battery_dc_discharge_kw.sum())/2),
       'economic_label':'HOMER_price_and_linear_cost_proxy_no_validated_EPM_tariff',
       'model_validation':'PRELIMINARY_PCC_algebra_only',
    }


def times_of_interest(res, loads):
    idx=set()
    for column in ('grid_import_kw','grid_export_kw','transformer_s_kva','inverter_s_kva','pcc_q_kvar'):
        idx.add(res[column].idxmax());idx.add(res[column].idxmin())
    idx.add(loads.idxmax());idx.add(loads.idxmin())
    return sorted(idx)


def read_source_pv(require_pvlib=False):
    df,meta,sd=read_inputs()
    try:
        pv,diag=pvlib_nasa_pv(df)
    except ImportError:
        if require_pvlib: raise RuntimeError('pvlib missing. Install pvlib to match original v18/v5 GHI-Erbs method.')
        pv,diag=approximate_nasa_pv(df)
    diag.update({
      'model_status':'PRELIMINARY_PCC_ONLY_PANDAPOWER_NOT_EXECUTED',
      'inverter_ratings_source':'Deye SUN-(5-12)K-SG02LP2-US-AM2/AM3 manufacturer table',
      'loading_pu_levels_are_assumptions_not_EPM_operating_rules':[.8,.9,1.0],
      'demand_basis':'HOMER_1898_kWh_per_house_year_2025_stochastic_v18',
      'tariffs_basis':'HOMER_0p29_USD_per_kWh_primary; EPM_invoice_COP_sensitivity_only',
      'nasa_sha256':hashfile(NASA_PATH), 'homer_sha256':hashfile(XML_PATH),
      'annual_demand_kwh':7592.,'v18_saved_load_peak_kw':2.166677435937405,
      'v5_saved_nasa_pv_dc_kwh':REFERENCE_PANDAPOWER_NASA_KWH,
      'dc_pv_difference_from_v5_pct':float(100*(diag['annual_dc_kwh_at_5p22']/REFERENCE_PANDAPOWER_NASA_KWH-1))
    })
    return df,sd,pv,diag


def run(args):
    df,sd,pv,diag=read_source_pv(args.require_pvlib)
    baseline_loading=args.baseline_loading
    baseline_pf=args.baseline_load_pf
    assert 0<baseline_loading<=1 and 0<baseline_pf<=1
    diag['baseline_transformer_max_pu']=baseline_loading
    diag['baseline_household_pf']=baseline_pf
    resource=resource_components(df,diag['method'],pv)
    resource.index.name='timestamp_LST'
    resource.to_csv(OUT/'solar_conversion_hourly_2025.csv',float_format='%.7f')
    profiles=build_stochastic_load(sd,df.index)
    load=profiles['load_4hh_kw']
    assert abs(load.sum()-7592)<1e-7 and abs(load.max()-2.166677435937405)<1e-8
    OUT.mkdir(exist_ok=True,parents=True)
    (OUT/'model_provenance.json').write_text(json.dumps(diag,indent=2)+'\n')
    rows=[];invalid=[];handoff=[]
    # Factors are independent. PV DC rating failures are recorded but never simulated.
    # 2 export policies here; all further axes can be expanded without notebook edits.
    for panels in (12,16,20,24):
        for inv in (5.,6.,7.6,8.,10.):
            hd=hardware_screen(panels,inv)
            if not hd['pv_input_rating_feasible']:
                invalid.append({'panels':panels,**hd})
                continue
            for modules in (0,2,4,6,8):
                for ex_kw in (0., 1.0):
                    for policy in ('conventional','fixed_reserve','adaptive_reactive'):
                        sol=pv*panels*.435
                        r=run_causal(load,sol,modules=modules,inverter_kva=inv,
                                cap_pu=baseline_loading,load_pf=baseline_pf,export_limit_kw=ex_kw,policy=policy)
                        s=summary_kpis(r,load,sol,panels=panels,modules=modules,
                           inverter_kva=inv,strategy=policy,allowed_loading=baseline_loading,
                           load_pf=baseline_pf,export_cap=ex_kw,q_control='unity')
                        s.update({'max_pv_input_kwp':hd['max_pv_input_kwp'],
                                  'dc_ac_ratio':hd['dc_ac_ratio'],
                                  'pv_power_rating_pass':True,
                                  'physical_hardware_approved':False,
                                  'LV_powerflow_validated':False,
                                  'pv_method':diag['method']})
                        rows.append(s)
                        if ex_kw==0 and policy=='conventional' and ((modules==4 and inv==5. and panels in (12,16)) or (modules==8 and inv==5. and panels==16)):
                            hourly=r.copy()
                            hourly.insert(0,'load_kw',load.to_numpy())
                            hourly.insert(1,'pv_dc_available_kw',sol.to_numpy())
                            hourly.index.name='timestamp_LST'
                            hourly.to_csv(OUT/f'reference_hourly_dispatch_{panels}p_5kva_{modules}b.csv',float_format='%.7f')
                            if modules==4:
                                hourly.to_csv(OUT/f'reference_hourly_dispatch_{panels}p_5kva.csv',float_format='%.7f')
                        if modules==4 and ex_kw==0 and policy=='conventional':
                            for ts in times_of_interest(r,load):
                                pvrow=r.loc[ts]
                                event={'timestamp':str(ts),'panels':panels,
                                       'inverter_kva':inv,'inverter_model':hd['inverter_model'],
                                       'pv_kwp':panels*.435,'bess_modules':modules,
                                       'inverter_p_kw':float(pvrow.inverter_ac_kw),
                                       'inverter_q_kvar':float(pvrow.inverter_q_kvar),
                                       'pcc_p_kw':float(pvrow.pcc_p_kw),
                                       'pcc_q_kvar':float(pvrow.pcc_q_kvar),
                                       'max_loading_kva':TRAFO_KVA*baseline_loading,
                                       'transformer_s_kva_screen':float(pvrow.transformer_s_kva),
                                       'load_kw':float(load.loc[ts]),
                                       'soc_usable_kwh':float(pvrow.soc_usable_kwh),
                                       'note':'PCC_only_handoff_not_yet_v5_split_phase_checked'}
                                for i in range(1,5):
                                    event[f'house_{i}_p_kw']=float(profiles.loc[ts,f'house_{i}_kw'])
                                    event[f'house_{i}_q_kvar']=pf_reactive_kw(event[f'house_{i}_p_kw'],baseline_pf)
                                handoff.append(event)
    # Dedicated envelope-limited export case, used to show when the PCC cap actually binds.
    # This remains an algebraic PCC screen, not a pandapower validation.
    for panels, inv, mods in ((12,5.,4),(16,5.,4),(24,7.6,8)):
        sol=pv*panels*.435
        er=run_causal(load,sol,modules=mods,inverter_kva=inv,cap_pu=baseline_loading,
                load_pf=baseline_pf,export_limit_kw=None,policy='conventional')
        hourly=er.copy()
        hourly.insert(0,'load_kw',load.to_numpy())
        hourly.insert(1,'pv_dc_available_kw',sol.to_numpy())
        hourly.index.name='timestamp_LST'
        inv_slug=str(inv).replace('.','p')
        hourly.to_csv(OUT/f'export_envelope_{panels}p_{inv_slug}kva_{mods}b.csv',float_format='%.7f')

    pd.DataFrame(rows).to_csv(OUT/'sizing_screen_v2.csv',index=False,float_format='%.7f')
    pd.DataFrame(invalid).to_csv(OUT/'excluded_pv_inverter_pairs.csv',index=False)
    pd.DataFrame(handoff).to_csv(OUT/'pandapower_v5_handoff.csv',index=False,float_format='%.7f')

    pf_rows=[]
    # PF of loads and PF at PCC are different: calculate both the common fixed-PF
    # capacity convention and the instantaneous load-P,Q loading actually achieved.
    for cap in (.8,.9,1.):
        for pf in (.8,.9,.95,1.):
            for nh in (4,6,8):
                ld=profiles[f'load_{nh}hh_kw']
                result=run_causal(ld,pv*5.22,modules=4,inverter_kva=5.,
                   cap_pu=cap,load_pf=pf,export_limit_kw=0.,policy='conventional')
                row=summary_kpis(result,ld,pv*5.22,panels=12,modules=4,inverter_kva=5.,
                   strategy='conventional',allowed_loading=cap,
                   load_pf=pf,export_cap=0.,q_control='unity',label='PF_and_derating')
                row.update({'households':nh,
                            'pmax_kw_if_pcc_pf_constant':trafo_p_limit_at_fixed_pf(cap,pf),
                            'q_load_peak_kvar':float(ld.max()*np.tan(np.arccos(pf)))})
                pf_rows.append(row)
    pd.DataFrame(pf_rows).to_csv(OUT/'transformer_pf_derating_sensitivity.csv',index=False,float_format='%.7f')

    # Charging and discharging are distinct battery DC ratings. Independent
    # sensitivity at a physically PV-input-eligible inverter / panel combination.
    power_rows=[]
    for c in (2.5,5.,7.5):
        for d in (2.5,5.,7.5):
            for mods in (2,4,6):
                sc=run_causal(load,pv*6.96,modules=mods,inverter_kva=6.,
                     cap_pu=baseline_loading,load_pf=baseline_pf,export_limit_kw=0.,
                     policy='conventional',charge_kw=c,discharge_kw=d)
                row=summary_kpis(sc,load,pv*6.96,panels=16,modules=mods,
                         inverter_kva=6.,strategy='conventional',allowed_loading=baseline_loading,
                         load_pf=baseline_pf,export_cap=0.,q_control='unity',label='battery_power')
                row['requested_charge_dc_kw']=c;row['requested_discharge_dc_kw']=d
                row['effective_charge_dc_kw']=min(c,mods*4.8,48*135/1000)
                row['effective_discharge_dc_kw']=min(d,mods*4.8,48*135/1000)
                power_rows.append(row)
    pd.DataFrame(power_rows).to_csv(OUT/'battery_power_sensitivity.csv',index=False,float_format='%.7f')

    # EPM invoices are for one DIFFERENT San Carlos service/transformer, not site.
    # Only demand scalar and tariff sensitivity. COP values never converted to USD.
    epm_rows=[]
    for annual_hh in (1898.,1055.):
        ratio=annual_hh/1898.
        ld=load*ratio
        for panels,inv in ((12,5.),(16,6.),(20,7.6),(24,7.6)):
            sol=pv*panels*.435
            res=run_causal(ld,sol,modules=4,inverter_kva=inv,cap_pu=baseline_loading,
                       load_pf=baseline_pf,export_limit_kw=0.,policy='conventional')
            for tariff in (400.,860.,920.):
                epm_rows.append({'demand_basis': 'HOMER_reference' if annual_hh==1898 else 'San_Carlos_different_service_sensitivity',
                  'annual_kwh_per_household':annual_hh,'total_4hh_kwh':float(ld.sum()),
                  'panels':panels,'inverter_kva':inv,'tariff_COP_per_kwh':tariff,
                  'grid_import_kwh':float(res.grid_import_kw.sum()),
                  'estimated_import_energy_charge_COP':float(res.grid_import_kw.sum()*tariff),
                  'self_sufficiency_pct':float(100*(1-res.grid_import_kw.sum()/ld.sum())),
                  'export_credit_COP':0.,
                  'note':'Bill-only_sensitivity_from_different_San_Carlos_service_no_actual_site_calibration'})
    pd.DataFrame(epm_rows).to_csv(OUT/'epm_invoice_demand_tariff_SENSITIVITY_ONLY.csv',index=False,float_format='%.7f')

    # Selected outage windows; run full year first to obtain previous-hour SOC.
    # No forecast, no perfect-foresight dispatch.
    low_end=(pv*5.22).rolling(168).sum().idxmin()
    start=low_end-pd.Timedelta(hours=71)
    low_daily=low_end-pd.Timedelta(hours=23)
    stress_rows=[]
    for name,begin,hours,lmult,smult in (
      ('24hr_outage_low_solar',low_daily,24,1.,1.),
      ('72hr_outage_low_solar',start,72,1.,1.),
      ('72hr_outage_plus_demand_and_solar',start,72,1.5,.5)):
        xx=load.loc[begin:begin+pd.Timedelta(hours=hours-1)]*lmult
        yy=(pv*5.22).loc[xx.index]*smult
        for policy in ('conventional','fixed_reserve','adaptive_reactive'):
            reference=run_causal(load,pv*5.22,modules=4,inverter_kva=5.,
                cap_pu=baseline_loading,load_pf=baseline_pf,export_limit_kw=0.,policy=policy)
            before=float(reference.loc[begin-pd.Timedelta(hours=1),'soc_usable_kwh'])
            r=run_causal(xx,yy,modules=4,inverter_kva=5.,cap_pu=baseline_loading,
                load_pf=baseline_pf,export_limit_kw=0.,policy=policy,
                outage=np.ones(hours,dtype=bool),initial_soc_kwh=before)
            ens=r.unserved_kw.to_numpy();crit=r.critical_unserved_kw.to_numpy()
            stress_rows.append({'case':name,'policy':policy,'start_LST':str(begin),
               'outage_hours':hours,'initial_usable_soc_kwh':before,
               'ens_kwh':float(ens.sum()),'critical_ens_kwh':float(crit.sum()),
               'full_load_survival_hours':int(np.argmax(ens>1e-8)) if (ens>1e-8).any() else hours,
               'critical_survival_hours':int(np.argmax(crit>1e-8)) if (crit>1e-8).any() else hours,
               'critical_load_fraction_ASSUMED':.5,
               'status':'HYPOTHETICAL_outage_islanding_hardware_NOT_verified'})
    pd.DataFrame(stress_rows).to_csv(OUT/'outage_stress_SENSITIVITY_ONLY.csv',index=False,float_format='%.7f')
    from case1_plots import generate_case1_figures
    if not args.no_plots:
        plots = generate_case1_figures(OUT)
        print(f'Generated {len(plots)} PNG figures in {OUT / "figures"}')
    print(json.dumps({'version':'2.2-preliminary','pv_method':diag['method'],
         'valid_PV_inverter_scenario_rows':len(rows),'excluded_PV_inverter_pairs':len(invalid),
         'load_kwh_4hh':float(load.sum()),
         'max_load_kw_4hh':float(load.max()),
         'active_kW_at_reference_pcc_pf':trafo_p_limit_at_fixed_pf(baseline_loading,baseline_pf),
         'output':str(OUT)},indent=2))


def cli():
    ap=argparse.ArgumentParser(description='SEEDexchange El Arenal Case 1 v2, Python script (no notebook).')
    ap.add_argument('--require-pvlib',action='store_true',help='Abort rather than run an explicitly unverified PV approximation')
    ap.add_argument('--baseline-loading',type=float,default=.9,help='Illustrative transformer permitted loading, fraction of 5 kVA (default 0.9)')
    ap.add_argument('--baseline-load-pf',type=float,default=.95,help='Lagging PF assumed for rural household demand, not PCC PF (default 0.95; use 1.0 for a unity-PF sensitivity)')
    ap.add_argument('--plots-only',action='store_true',help='Generate figures from existing result CSVs, without rerunning simulation')
    ap.add_argument('--no-plots',action='store_true',help='Generate CSVs without figures')
    args=ap.parse_args()
    if args.plots_only:
        from case1_plots import generate_case1_figures
        plots=generate_case1_figures(OUT)
        print(f'Generated {len(plots)} PNG figures in {OUT / "figures"}')
    else:
        run(args)

if __name__=='__main__':cli()
