#!/usr/bin/env python3
"""Conditional pandapower AC power-flow, NOT a surveyed EPM LV network."""
import argparse,csv,json,math,hashlib
from pathlib import Path
import pandapower as pp
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
REVIEW=ROOT/"case1/studies/community_georef/field_review_2026_10_27/houses_field_review.csv"
PROFILE=ROOT/"Energy Community - San Rafael/pandapower_results_nasa/nasa_hourly_pv_and_load_inputs.csv"
HOUSE_IDS=["H03","H06","H26","H27","H28","H34","H35"]
SITE=(6.246949759,-75.006208238)
STAMPS=("2025-11-01 19:00:00","2025-07-30 12:00:00")
FACTOR=3.0
def house_points():
    with REVIEW.open(newline="",encoding="utf-8") as f:
        rows={r["house_id"]:r for r in csv.DictReader(f)}
    assert all(rows[h]["candidate_epm_nodes"]=="931076" for h in HOUSE_IDS)
    return {h:(float(rows[h]["latitude"]),float(rows[h]["longitude"])) for h in HOUSE_IDS}
def length_m(geo,kind):
    lat,lon=geo;rad=math.pi/180;R=6378137
    dx=R*math.cos(rad*(lat+SITE[0])/2)*(lon-SITE[1])*rad
    dy=R*(lat-SITE[0])*rad
    if kind=="euclidean":return math.hypot(dx,dy)
    if kind=="rectilinear":return abs(dx)+abs(dy)
    raise ValueError(kind)
def source_hours():
    records={}
    with PROFILE.open(newline="",encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["timestamp"] in STAMPS:
                records[row["timestamp"]]={
                  "house_kw":[float(row["house_"+str(i)+"_kw"]) for i in range(1,8)],
                  "pv_kw":float(row["nasa_pv_ac_kw"])}
            if len(records)==2:break
    assert len(records)==2,"Reference hourly data changed"
    return records
def make_network(points,distance,siting):
    n=pp.create_empty_network(f_hz=60,sn_mva=1)
    hvsrc=pp.create_bus(n,vn_kv=math.sqrt(3)*7.621)
    hv=pp.create_bus(n,vn_kv=math.sqrt(3)*7.621)
    lv=pp.create_bus(n,vn_kv=math.sqrt(3)*0.240)
    pp.create_ext_grid(n,bus=hvsrc,vm_pu=1)
    pp.create_line_from_parameters(n,from_bus=hvsrc,to_bus=hv,length_km=.3542,
        r_ohm_per_km=.832,x_ohm_per_km=.40,c_nf_per_km=0,max_i_ka=.184)
    pp.create_transformer_from_parameters(n,hv_bus=hv,lv_bus=lv,sn_mva=.015,
        vn_hv_kv=math.sqrt(3)*7.621,vn_lv_kv=math.sqrt(3)*.240,
        vk_percent=3,vkr_percent=1.8,pfe_kw=.09,i0_percent=2.5,shift_degree=0)
    buses,loads,lines={},{},{}
    for hid,geo in points.items():
        b=pp.create_bus(n,vn_kv=math.sqrt(3)*.240)
        l=pp.create_line_from_parameters(n,from_bus=lv,to_bus=b,
             length_km=length_m(geo,distance)/1000,r_ohm_per_km=1.312,
             x_ohm_per_km=.16,c_nf_per_km=0,max_i_ka=.150)
        ld=pp.create_load(n,bus=b,p_mw=0,q_mvar=0)
        buses[hid],loads[hid],lines[hid]=b,ld,l
    injection_buses=[lv] if siting=="central" else [buses["H06"],buses["H35"]]
    sg=[pp.create_sgen(n,bus=bus,p_mw=0,q_mvar=0) for bus in injection_buses]
    assert len(n.trafo)==1
    return n,buses,loads,lines,sg
def solve(points,hour,distance,siting,mode,pv_kwp=0,bess_kw=0,export="unrestricted"):
    n,buses,loads,lines,sg=make_network(points,distance,siting)
    pf=.9
    for h,kw in zip(HOUSE_IDS,hour["house_kw"]):
        n.load.at[loads[h],"p_mw"]=3*kw/1000
        n.load.at[loads[h],"q_mvar"]=3*kw*math.tan(math.acos(pf))/1000
    if mode=="pv":
        injection=min(5.0,hour["pv_kw"]*pv_kwp/5.22)
        if export=="gross_load_capped":injection=min(injection,sum(hour["house_kw"]))
    else:injection=min(5.0,bess_kw,sum(hour["house_kw"]))
    for idx in sg:n.sgen.at[idx,"p_mw"]=3*injection/1000/len(sg)
    pp.runpp(n,algorithm="bfsw",init="flat",max_iteration=100,tolerance_mva=1e-9)
    vs=[float(n.res_bus.vm_pu.at[b]) for b in buses.values()]
    trafo=float(n.res_trafo.loading_percent.iloc[0])
    vl=max(float(n.res_line.loading_percent.at[idx]) for idx in lines.values())
    return dict(distance=distance,architecture=siting,mode=mode,
          pv_kwp=pv_kwp,battery_power_kw=bess_kw,export_policy=export if mode=="pv" else "not_applicable",
          actual_injection_kw=round(injection,6),min_lv_pu=round(min(vs),6),
          max_lv_pu=round(max(vs),6),trafo_loading_pct=round(trafo,6),
          max_lv_line_loading_pct=round(vl,6),
          transformer_import_kw=round(float(n.res_trafo.p_hv_mw.iloc[0])*1000/3,6),
          lv_losses_kw=round(sum(float(n.res_line.pl_mw.at(idx)) for idx in lines.values())*1000/3,6),
          screen_pass=(min(vs)>=.97 and max(vs)<=1.03 and trafo<=100 and vl<=100))
def study():
    pts=house_points();hours=source_hours();rows=[]
    for d in ("euclidean","rectilinear"):
        for a in ("central","shared_two_sites"):
            for b in (0,2,4):
                rows.append(solve(pts,hours[STAMPS[0]],d,a,"storage",bess_kw=b))
            for pv in (2.61,5.22,10.44):
                for e in ("unrestricted","gross_load_capped"):
                    rows.append(solve(pts,hours[STAMPS[1]],d,a,"pv",pv_kwp=pv,export=e))
    ds=[{"house_id":h,"euclidean_m":round(length_m(p,"euclidean"),3),
         "rectilinear_m":round(length_m(p,"rectilinear"),3)} for h,p in pts.items()]
    return rows,ds
def run(out):
    rows,dist=study();out.mkdir(parents=True,exist_ok=True)
    for filename,data in (("conditional_snapshots.csv",rows),("distance_sensitivity.csv",dist)):
        with (out/filename).open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator="\n");w.writeheader();w.writerows(data)
    (out/"manifest.json").write_text(json.dumps({
       "status":"conditional physical sensitivity, not utility-verified feeder",
       "house_ids":HOUSE_IDS,"distance_options":["Euclidean sqrt(dx²+dy²)","rectilinear abs(dx)+abs(dy)"],
       "topology":"separate straight/rectilinear radial service paths from existing 94022 5kVA LV bus",
       "reference":"original pandapower v5 MV and LV conductor/transformer parameters",
       "pv_reference":"NASA July 30 2025 noon, linearly scaled 5.22kWp reference, clipped 5kW AC",
       "bess":"instantaneous 0/2/4kW, 5kW aggregate inverter cap, SOC feasibility NOT simulated",
       "profiles":"archived stochastic house_1-7 mapped to candidate H03,H06,H26,H27,H28,H34,H35 by order; not metered",
       "not_included":["actual MV/LV topology","actual transformer customer accounts","25yr lifecycle economics","8760h BESS SOC","split-phase currents","parked load categories"],
       "input_sha256":{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [REVIEW,PROFILE]}
    },indent=2)+"\n",encoding="utf-8")
    print("SNAPSHOTS_BEGIN")
    print((out/"conditional_snapshots.csv").read_text(),end="")
    print("SNAPSHOTS_END")
    print("DISTANCES_BEGIN")
    print((out/"distance_sensitivity.csv").read_text(),end="")
    print("DISTANCES_END")
    print("PASS_COUNT",sum(int(r["screen_pass"]) for r in rows),"OF",len(rows))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--outdir",type=Path,default=HERE/"outputs");args=p.parse_args()
    run(args.outdir)
