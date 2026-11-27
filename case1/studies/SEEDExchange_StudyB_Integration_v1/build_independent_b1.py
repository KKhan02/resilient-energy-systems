"""Study B1/B2: reproducible geometry and gross-load screening, not AC."""
from __future__ import annotations
import argparse, csv, hashlib, itertools, json, math, sys
from pathlib import Path
from functools import lru_cache
import numpy as np
import pandas as pd

BASE = "case1/studies/SEEDExchange_StudyA_LocalPreflight_v4/outputs/run_02/"
SOURCES = {
    BASE+"household_profiles_2025_excel_35.csv":"74a66b2795769e564a41e859fab665fc3db65ae81dfdfc53e1addf6aa459dd8c",
    BASE+"fixed_house_to_profile_map.csv":"81b736a29a1b2b3921663b58a267d8217d45e630881d215a182df7454e3471f9",
    "case1/studies/community_georef/field_review_2026_10_27/houses_field_review.csv":"157f2ac460d5cf2e3ef4f162f1d03f91437f85f13157d0f4c711d559b85f60fe",
}
PFS=(.95,.98,1.)
FACTORS=(1.,1.3,1.6)
def require(ok,msg):
    if not ok: raise ValueError(msg)
def sha(b): return hashlib.sha256(b).hexdigest()
def verify(root):
    for path, digest in SOURCES.items():
        b=(root/path).read_bytes()
        require(digest in (sha(b),sha(b.replace(b'\r\n',b'\n')),sha(b.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))),f"source hash mismatch: {path}")
def rows(path):
    with path.open(encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))
def write(path, data):
    require(bool(data),f"empty output {path}")
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(data[0])); w.writeheader(); w.writerows(data)
def canonical(g): return tuple(sorted(g))
def nearest_groups(ids, xy):
    return {canonical(sorted(ids,key=lambda h:(float(np.linalg.norm(xy[h]-xy[s])),h))[:n])
            for s in ids for n in range(5,16)}
def partitions(ids, xy):
    orders={"EW":sorted(ids,key=lambda h:(xy[h][0],xy[h][1],h)),
            "NS":sorted(ids,key=lambda h:(xy[h][1],xy[h][0],h))}
    for axis in ("EW","NS"):
        unused=set(ids); ordered=[]; h=orders[axis][0]
        while unused:
            ordered.append(h); unused.remove(h)
            if unused: h=min(unused,key=lambda k:(float(np.linalg.norm(xy[k]-xy[h])),k))
        orders["NN_"+axis]=ordered
    for label,order in orders.items():
        for k in range(math.ceil(len(ids)/15),len(ids)//5+1):
            q,r=divmod(len(ids),k); groups=[]; start=0
            for i in range(k):
                n=q+(i<r); groups.append(canonical(order[start:start+n]));start+=n
            require(sorted(itertools.chain.from_iterable(groups))==sorted(ids),"partition population")
            yield label,k,groups
def sites(g,xy):
    points=np.array([xy[h] for h in g]); c=points.mean(axis=0)
    d=np.linalg.norm(points[:,None,:]-points[None,:,:],axis=2)
    medoid=points[np.argmin(d.sum(axis=1))]
    mini=points[np.argmin(d.max(axis=1))]
    # Smoothed Weiszfeld iteration, candidate only, no claim of feasible land.
    gm=c.copy()
    for _ in range(500):
        weights=1/np.maximum(np.linalg.norm(points-gm,axis=1),1e-7)
        nxt=(points*weights[:,None]).sum(axis=0)/weights.sum()
        if np.linalg.norm(nxt-gm)<1e-7: gm=nxt;break
        gm=nxt
    unique=[]
    for name,pos in (("CENTROID",c),("GEOMETRIC_MEDIAN_APPROX",gm),("MEDOID",medoid),("MINIMAX_HOUSE",mini)):
        # snap numerical coincidence, combine identical candidate sites
        i=int(np.argmin(np.linalg.norm(points-pos,axis=1)))
        if np.linalg.norm(points[i]-pos)<1e-5: pos=points[i].copy()
        match=next((x for x in unique if np.linalg.norm(x[1]-pos)<1e-5),None)
        if match: match[0].append(name)
        else: unique.append(([name],pos.copy()))
    return unique
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--repo-root",type=Path,default=Path("."))
    a.add_argument("--out",type=Path,required=True)
    a.add_argument("--preflight-only",action="store_true")
    args=a.parse_args(); root=args.repo_root.resolve();verify(root)
    sys.path.insert(0,str(root/"case1/studies/geographic_pandapower_v1"))
    from topology import territory, EARTH
    hh=rows(root/"case1/studies/community_georef/field_review_2026_10_27/houses_field_review.csv")
    profiles=rows(root/(BASE+"fixed_house_to_profile_map.csv"))
    H={r["house_id"]:dict(lat=float(r["latitude"]),lon=float(r["longitude"])) for r in hh}
    M={r["house"]:r["profile_column"] for r in profiles}
    ids=sorted(H); require(ids==[f"H{i:02}" for i in range(1,36)] and set(M)==set(ids) and len(set(M.values()))==35,"house/profile identity")
    require(M["H08"]=="house_25_kw","H08 identity")
    require(len({(v["lat"],v["lon"]) for v in H.values()})==35,"unique coordinates")
    df=pd.read_csv(root/(BASE+"household_profiles_2025_excel_35.csv"))
    time=pd.to_datetime(df.timestamp)
    require(time.tolist()==pd.date_range("2025-01-01",periods=8760,freq="h").tolist(),"annual timestamps")
    X=df[[M[h] for h in ids]].to_numpy(dtype=float)
    require(X.shape==(8760,35) and np.isfinite(X).all() and (X>=0).all() and np.allclose(X.sum(axis=0),1898,atol=1e-7,rtol=0),"annual profile gate")
    idx={h:i for i,h in enumerate(ids)}
    lat0=np.mean([v["lat"] for v in H.values()]);lon0=np.mean([v["lon"] for v in H.values()])
    sx=EARTH*math.pi/180*math.cos(math.radians(lat0)); sy=EARTH*math.pi/180
    xy={h:np.array([(v["lon"]-lon0)*sx,(v["lat"]-lat0)*sy]) for h,v in H.items()}
    @lru_cache(maxsize=None)
    def peak(g):
        v=X[:,[idx[h] for h in g]].sum(axis=1)
        return float(v.max()),int(v.argmax()),tuple(int(np.count_nonzero(v/pf>5+1e-9)) for pf in PFS)
    # Independent overlapping candidate groups and explicit whole-population alternatives.
    group_methods={}; part_specs=[]
    for pop,eligible in (("FULL35",ids),("MATCHED34",[h for h in ids if h!="H08"])):
        for g in nearest_groups(eligible,xy):group_methods.setdefault(g,set()).add(pop+"_NEAREST")
        for method,k,groups in partitions(eligible,xy):
            part_specs.append((pop,method,k,groups))
            for g in groups:group_methods.setdefault(g,set()).add(pop+"_PARTITION")
    groups=sorted(group_methods,key=lambda g:(len(g),g))
    G={g:f"B_G{i:04}" for i,g in enumerate(groups,1)}
    require(set(map(len,groups))==set(range(5,16)) and any("H08" in g for g in groups),"group coverage")
    # Tiny analytic topology check: independent, same supply, no duplicated edge.
    test={"A":{"lat":0.001,"lon":0.},"B":{"lat":0.002,"lon":0.}}
    t0={"lat":0.,"lon":0.,"transformer_number":"B_TEST"}
    require(territory(t0,test,"mst",1).total_m<territory(t0,test,"star",1).total_m,"STAR/MST analytic test")
    if args.preflight_only:
        print("B1_PREFLIGHT_JSON "+json.dumps({"status":"PASS","groups":len(groups),"partitions":len(part_specs),"hours":len(X),"demand_kwh":float(X.sum())}));return
    out=args.out.resolve();require(out.is_relative_to(root),"output outside checkout");out.mkdir(parents=True,exist_ok=False)
    roster=[];partrows=[];site_rows=[];cases=[];nodes=[];edges=[];screens=[]
    for pop,method,k,gg in part_specs:
        pid=f"{pop}_{method}_{k}"
        for g in gg:partrows.append(dict(partition_id=pid,population=pop,method=method,cluster_count=k,group_id=G[g]))
    for g in groups:
        gid=G[g]
        for h in g:roster.append(dict(group_id=gid,house_id=h,profile_column=M[h],methods=";".join(sorted(group_methods[g]))))
        gp,gh,over=peak(g)
        for j,(methods,pos) in enumerate(sites(g,xy),1):
            sid=f"{gid}_S{j}"; lat=lat0+pos[1]/sy;lon=lon0+pos[0]/sx
            coloc=[h for h in g if np.linalg.norm(xy[h]-pos)<1e-5]
            require(len(coloc)<=1,"duplicate co-location")
            if coloc: lat,lon=H[coloc[0]]["lat"],H[coloc[0]]["lon"]
            site_rows.append(dict(site_id=sid,group_id=gid,latitude=lat,longitude=lon,method=";".join(methods),
                colocated_house=coloc[0] if coloc else "",supply_basis="PROPOSED_NEW_SUPPLY_UNVERIFIED",site_status="GEOMETRIC_ONLY"))
            root_node={"lat":lat,"lon":lon,"transformer_number":sid}
            pair=[]
            for typ in ("star","mst"):
                cid=f"{sid}_{typ.upper()}"
                t=territory(root_node,{h:H[h] for h in g},typ,1.)
                require(len(t.parent)==len(g),"tree coverage")
                # Contract a coincident house/supply bus. No zero-length physical branch.
                def node_id(h):return "SUPPLY" if h=="TRAFO" or h in coloc else h
                nodes.append(dict(case_id=cid,node_id="SUPPLY",node_type="supply",house_id=coloc[0] if coloc else "",latitude=lat,longitude=lon))
                for h in g:
                    if h not in coloc:nodes.append(dict(case_id=cid,node_id=h,node_type="house",house_id=h,latitude=H[h]["lat"],longitude=H[h]["lon"]))
                downstream={h:[] for h in g}
                for h in g:
                    cur=h;seen=set()
                    while cur!="TRAFO":
                        require(cur not in seen,"cycle");seen.add(cur);downstream[cur].append(h);cur=t.parent[cur]
                positive=[]; max_branch=0.
                for h,par in t.parent.items():
                    length=t.lengths_m[h]
                    if length<1e-6:
                        require(h in coloc and par=="TRAFO","unexpected zero edge");continue
                    require(node_id(par)!=node_id(h) and length>0,"invalid edge")
                    sub=canonical(downstream[h]);bp,bh,_=peak(sub);max_branch=max(max_branch,bp)
                    positive.append(length)
                    edges.append(dict(case_id=cid,branch_id=f"{cid}_{h}",from_node=node_id(par),to_node=node_id(h),base_length_m=length,
                        length_method="LOCAL_GEOMETRIC_UNROUTED",conductor="UNKNOWN",downstream_house_ids=";".join(sub),peak_downstream_kw=bp,peak_timestamp=str(time.iloc[bh])))
                require(len(positive)==len(g)-len(coloc),"contracted radial count")
                total=sum(positive);pair.append(total)
                cases.append(dict(case_id=cid,group_id=gid,site_id=sid,topology=typ.upper(),house_count=len(g),supply_node_id="SUPPLY",rating_kva_hypothesis=5,
                    total_base_m=total,longest_base_path_m=t.max_m,peak_branch_kw=max_branch,geometry_status="HYPOTHETICAL"))
                for pf,oh in zip(PFS,over):
                    for factor in FACTORS:
                        screens.append(dict(case_id=cid,pf=pf,route_factor=factor,total_route_m=total*factor,longest_path_m=t.max_m*factor,
                          annual_demand_kwh=1898*len(g),gross_peak_kw=gp,gross_peak_kva=gp/pf,gross_peak_timestamp=str(time.iloc[gh]),
                          gross_5kva_exceed_hours=oh,max_branch_gross_kva=max_branch/pf,ac_status="NOT_RUN"))
            require(pair[1]<=pair[0]+1e-7,"MST longer than STAR")
    tables={"group_roster.csv":roster,"partition_membership.csv":partrows,"supply_sites.csv":site_rows,"network_cases.csv":cases,
      "network_nodes.csv":nodes,"network_branches.csv":edges,"gross_screen.csv":screens}
    for name,data in tables.items():write(out/name,data)
    result={"status":"PASS_GEOMETRY_AND_GROSS_SCREEN_ONLY","source_hashes_expected":SOURCES,
      "source_hashes_actual":{p:sha((root/p).read_bytes()) for p in SOURCES},
      "topology_sha256":sha((root/"case1/studies/geographic_pandapower_v1/topology.py").read_bytes()),
      "script_sha256":sha(Path(__file__).read_bytes()),"hours":len(X),"demand_kwh":float(X.sum()),"groups":len(groups),
      "groups_per_N":{str(n):sum(len(g)==n for g in groups) for n in range(5,16)},
      "partitions":len(part_specs),"sites":len(site_rows),"cases":len(cases),"screen_rows":len(screens),
      "branch_rows":len(edges),"AC_solves":0,"LP_solves":0,
      "output_hashes":{name:sha((out/name).read_bytes()) for name in tables}}
    (out/"manifest.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print("B1_REPORT_JSON "+json.dumps(result))
if __name__=="__main__":main()
