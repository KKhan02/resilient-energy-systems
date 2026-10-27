"""2025 8760-hour provisional multi-territory shared PV/BESS expansion.

Energy-only heuristic, NOT PyPSA optimal dispatch, pandapower voltage, or EPM
service verification. Input source and historical 25-year cost basis unchanged.
"""
import argparse,csv,hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
HOUSE=ROOT/"case1/studies/community_georef/field_review_2026_10_27/houses_field_review.csv"
SOURCE=ROOT/"Energy Community - San Rafael/pandapower_results_nasa/nasa_hourly_pv_and_load_inputs.csv"
MODEL=ROOT/"case1/wp1_v3/model.py"
NODES=("931076","923848","923494","900607","823002","241054")
KNOWN_KVA=("931076","923848")
PANEL_KW=.435
MODULE_USE=17.3/4
EFF=math.sqrt(.95)
YEARS=25
DISCOUNT=.06
QUOTE_FACTOR=11974.79/(3856+4770+3330)
PV_USD=3856/12*QUOTE_FACTOR
BAT_USD=4770/4*QUOTE_FACTOR
INV_USD=3330/5*QUOTE_FACTOR
CRF=DISCOUNT*(1+DISCOUNT)**25/((1+DISCOUNT)**25-1)

def territories():
    with HOUSE.open(newline="",encoding="utf-8") as f:rows=list(csv.DictReader(f))
    d={x:[] for x in NODES}
    for r in rows:
        if r["candidate_epm_nodes"] in d:d[r["candidate_epm_nodes"]].append(r["house_id"])
    assert len(rows)==35 and sum(map(len,d.values()))==31
    return d

def hourly():
    with SOURCE.open(newline="",encoding="utf-8") as f:
        z=[([float(r["house_"+str(i)+"_kw"]) for i in range(1,21)],
            max(0.,float(r["nasa_pv_ac_kw_unclipped"]))) for r in csv.DictReader(f)]
    assert len(z)==8760
    return z

def banks(n,pv,mods,power,layout):
    if layout=="K":
        if n<4:raise ValueError("K must have two MULTI-home clusters")
        ids=[list(range(0,n,2)),list(range(1,n,2))]
        pv_parts=[pv//2,pv-pv//2]
        mod_parts=[mods//2,mods-mods//2]
        cap=[5.,5.]
        power_parts=[power/2]*2
    else:
        ids=[list(range(n))];pv_parts=[pv];mod_parts=[mods]
        cap=[10. if pv+mods else 0.];power_parts=[power]
    a=[]
    for i,pan,m,ic,p in zip(ids,pv_parts,mod_parts,cap,power_parts):
        if pan*PANEL_KW>ic*1.5+1e-9 or p>ic or (not m and p):
            raise ValueError("Hardware DC input/inverter/battery incompatibility")
        a.append(dict(ids=i,pv=pan,mods=m,ic=ic,power=p,soc=m*MODULE_USE/2,throughput=0))
    return a

def simulate(data,n,pv,mods,power,layout,export_cap):
    groups=banks(n,pv,mods,power,layout)
    import_kwh=export_kwh=curtail=total_load=pv_ac=ch=dis=peak_import=0.
    hours_above=0
    for load,ref_pv_ac in data:
        net=0.
        for g in groups:
            d=sum(load[i] for i in g["ids"])
            solar=min(g["ic"],ref_pv_ac*g["pv"]*PANEL_KW/5.22)
            total_load+=d;pv_ac+=solar
            residual=d-solar
            if residual>0 and g["mods"]:
                b=min(residual,g["power"],max(0.,g["ic"]-solar),g["soc"]*EFF)
                residual-=b;g["soc"]-=b/EFF;g["throughput"]+=b/(2*EFF);dis+=b
            elif residual<0 and g["mods"]:
                b=min(-residual,g["power"],max(0.,(g["mods"]*MODULE_USE-g["soc"])/EFF))
                residual+=b;g["soc"]+=b*EFF;g["throughput"]+=b*EFF/2;ch+=b
            net+=residual
        if net>=0:
            import_kwh+=net;peak_import=max(peak_import,net)
            if net>4.5:hours_above+=1
        else:
            export_kwh+=min(-net,export_cap)
            curtail+=max(0.,-net-export_cap)
    component=pv*PV_USD+mods*BAT_USD+sum(g["ic"] for g in groups)*INV_USD
    replacements=0.
    for g in groups:
        if not g["mods"]:continue
        life=min(20.,g["mods"]*23660/max(g["throughput"],1e-12))
        year=life
        while year<YEARS-1e-6:
            replacements+=g["mods"]*BAT_USD/(1+DISCOUNT)**year
            year+=life
    inv=sum(g["ic"] for g in groups)*INV_USD
    active_sites=len(groups) if component>0 else 0
    replacements+=inv/(1+DISCOUNT)**15
    # BOS scenarios explicitly UNSOURCED (0-30% + 0-1500 USD per site).
    def annual_cost(rate,site_fee):
        capex=component*(1+rate)+site_fee*active_sites
        return (capex+replacements)*CRF+.02*capex+.29*import_kwh
    return dict(homes=n,architecture=layout,shared_sites=len(groups),pv_panels=pv,
        pv_kwp=round(pv*PANEL_KW,5),battery_modules=mods,
        battery_usable_kwh=round(mods*MODULE_USE,5),battery_power_kw=power,
        inverter_total_kw=sum(g["ic"] for g in groups),export_limit_kw=export_cap,
        load_kwh=round(total_load,3),pv_ac_kwh=round(pv_ac,3),
        battery_charge_kwh=round(ch,3),battery_discharge_kwh=round(dis,3),
        grid_import_kwh=round(import_kwh,3),grid_export_kwh=round(export_kwh,3),
        solar_curtailment_kwh=round(curtail,3),self_sufficiency_pct=round(100*(1-import_kwh/total_load),3),
        max_import_kw=round(peak_import,3),hours_above_4p5_kw=hours_above,
        cost_annual_usd_low_BOS=round(annual_cost(0,0),2),
        cost_annual_usd_mid_BOS=round(annual_cost(.15,750),2),
        cost_annual_usd_high_BOS=round(annual_cost(.30,1500),2),
        export_credit_reference_usd=round(export_kwh*.275,2),
        annual_cost_with_reference_export_credit_usd=round(annual_cost(.15,750)-export_kwh*.275,2),
        lv_voltage_status="NOT_SIMULATED",utility_connection_status="NOT_VERIFIED")

def study():
    d=territories();inp=hourly();out=[]
    for node,homes in d.items():
        n=len(homes)
        for pv in (0,12,24,32):
            for mods in (0,4,8):
                for power in ((0,) if mods==0 else (5,10)):
                    if pv==0 and mods==0:
                        modes=(("C",0.),)
                    else:
                        modes=[(a,c) for a in (("C","K") if n>=4 else ("C",)) for c in (0.,4.5)]
                    for layout,ex in modes:
                        try:r=simulate(inp,n,pv,mods,power,layout,ex)
                        except ValueError:continue
                        out.append(dict(epm_node=node,candidate_houses="|".join(homes),
                                        confirmed_nameplate_kva=5 if node in KNOWN_KVA else "",
                                        other_portal_capacity_kw_NOT_kva=(node not in KNOWN_KVA),**r))
    manifest={
      "description":"2025 annual energy/SOC/25y cost *conditional* screen, NOT PyPSA v18 optimization or pandapower validation",
      "profiles":"Archived 8760h v5 NASA-based AC-unclipped PV profile and 20 synthetic household demands; ordinally reused by group, not meter data",
      "input_sha256":{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in (HOUSE,SOURCE,MODEL)},
      "candidate_territory_sizes":{k:len(v) for k,v in d.items()},
      "total_unique_candidates":31,"excluded_H01_H02_H10_H29":"unknown or multiple transformer candidates",
      "architecture":"C one 10kW inverter vs K two separate 5kW shared systems for >=4 houses; matched aggregate panels, modules and battery power; pooled PCC balancing assumed",
      "hardware":"435Wp PV, 5.12 kWh nominal / 4.325 kWh usable module; sqrt(0.95) battery one-way efficiency; inverter DC PV input <= 1.5 x AC screen",
      "dispatch":"hourly myopic local self-consumption; zero battery lookahead, start 50% SOC; not optimized; source AC-unclipped PV scaled from 5.22kWp reference",
      "cost":"HOMER historical component split in case1/wp1_v3/model.py, 25yr, 6% discount, inverter replaced year15, battery throughput or float20yr replacements; assumed BOS 0-30%, 0-1500USD/site, 2% annual O&M; import 0.29USD/kWh, export credit optional 0.275USD/kWh",
      "missing_costs":"Actual LV cable, BOS quotes, protection, meter, permission, land, taxes, connection and transformer upgrades unpriced. Cost table NOT full verified lifecycle quote.",
      "known_5kva":"Only existing node 931076/94022 and 923848/92395 have archived 5kVA rating; EPM portal 3kW/5kW not converted to kVA",
      "excluded_assumptions":"No new transformers; no critical/deferrable fractions; no confirmed EPM service network; no voltage/current/neutral compliance"
    }
    return out,manifest

def run(where):
    where.mkdir(parents=True,exist_ok=True)
    rows,manifest=study()
    with (where/"annual_scenarios.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
    (where/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print("SCENARIOS_COUNT",len(rows),"TERRITORY_SIZES",manifest["candidate_territory_sizes"])
    selected=[r for r in rows if r["epm_node"] in KNOWN_KVA and r["pv_panels"]==24 and r["battery_modules"]==4 and r["battery_power_kw"]==5 and r["export_limit_kw"]==0]
    print("SELECTED="+json.dumps(selected,separators=(",",":")))
    print("DATA_START");print((where/"annual_scenarios.csv").read_text(),end="");print("DATA_END")
    print("MANIFEST_START");print((where/"manifest.json").read_text(),end="");print("MANIFEST_END")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--outdir",type=Path,default=HERE/"outputs")
    run(parser.parse_args().outdir)
