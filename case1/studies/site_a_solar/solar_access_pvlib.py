#!/usr/bin/env python3
"""Exploratory Site A solar access: NOT a measured Site A shading prediction."""
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd
import pvlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LAT,LON=6.248376671296207,-75.00932156861505
PANEL_HEIGHT_M=1.5  # assumed midpoint above assumed level ground

def tree_angle(tree_height, setback, panel_height=PANEL_HEIGHT_M):
    if setback<=0 or tree_height<0 or panel_height<0:
        raise ValueError("invalid tree height, panel height or setback")
    return math.degrees(math.atan2(max(tree_height-panel_height,0.),setback))

def load_weather(path):
    df=pd.read_csv(path,parse_dates=["timestamp_lst"]).set_index("timestamp_lst").sort_index()
    if len(df)!=8760 or df.index.has_duplicates or df.index[0]!=pd.Timestamp("2025-01-01") or df.index[-1]!=pd.Timestamp("2025-12-31 23:00") or not (df.index[1:]-df.index[:-1]==pd.Timedelta(hours=1)).all():
        raise ValueError("expected consecutive 2025 NASA POWER hourly local-solar-time records")
    for col in ["ALLSKY_SFC_SW_DWN","ALLSKY_SFC_SW_DIFF","ALLSKY_SFC_SW_DNI"]:
        if df[col].isna().any() or (df[col]<0).any():
            raise ValueError("invalid weather column "+col)
    df.index=(df.index+pd.Timedelta(minutes=30)).tz_localize("Etc/GMT+5")
    sun=pvlib.solarposition.get_solarposition(df.index,LAT,LON,method="nrel_numpy")
    return df,sun

def poa(df,sun,tilt,azimuth,horizon=0.,sector="all"):
    elevation=sun.apparent_elevation.to_numpy()
    bearing=sun.azimuth.to_numpy()
    sectors={"all":np.ones(len(sun),dtype=bool),
             "east":(bearing>=45)&(bearing<135),
             "west":(bearing>=225)&(bearing<315)}
    if sector not in sectors:raise ValueError("unknown sector")
    mask=(elevation>0)&(elevation<=horizon)&sectors[sector]
    dni=df.ALLSKY_SFC_SW_DNI.to_numpy()
    irrad=pvlib.irradiance.get_total_irradiance(
        surface_tilt=tilt,surface_azimuth=azimuth,
        solar_zenith=sun.apparent_zenith.to_numpy(),solar_azimuth=bearing,
        dni=np.where(mask,0.,dni),ghi=df.ALLSKY_SFC_SW_DWN.to_numpy(),
        dhi=df.ALLSKY_SFC_SW_DIFF.to_numpy(),albedo=.2,model="isotropic")
    return np.asarray(irrad["poa_global"],dtype=float),mask

def run(weather,outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    df,sun=load_weather(weather)
    orientations=[(0,180),(10,0),(10,180),(20,0),(20,180)]
    bases={}
    for tilt,azimuth in orientations:
        values,_=poa(df,sun,tilt,azimuth)
        bases[(tilt,azimuth)]=float(values.sum()/1000)
    pd.DataFrame([{"tilt_deg":t,"azimuth_deg":a,"unshaded_poa_kwh_m2":round(v,3)}
                  for (t,a),v in bases.items()]).to_csv(outdir/"orientation_unshaded.csv",index=False)
    horizon_rows=[]
    for (tilt,azimuth),baseline in bases.items():
        for level in (0,10,20,30):
            irradiance,_=poa(df,sun,tilt,azimuth,level)
            total=float(irradiance.sum()/1000)
            horizon_rows.append(dict(tilt_deg=tilt,azimuth_deg=azimuth,
                horizon_deg_assumed=level,poa_kwh_m2=round(total,3),
                direct_only_poa_loss_pct=round(100*(1-total/baseline),3)))
    uniform=pd.DataFrame(horizon_rows)
    uniform.to_csv(outdir/"uniform_horizon_sensitivity.csv",index=False)
    tree_rows=[]
    for tilt,azimuth in ((10,0),(10,180)):
        baseline=bases[(tilt,azimuth)]
        for height in (8.,12.,18.):
            for distance in (5.,10.,20.):
                angle=tree_angle(height,distance)
                for sector in ("all","east","west"):
                    screened,mask=poa(df,sun,tilt,azimuth,angle,sector)
                    new=float(screened.sum()/1000)
                    tree_rows.append(dict(tilt_deg=tilt,azimuth_deg=azimuth,
                        assumed_tree_height_m=height,assumed_setback_m=distance,
                        panel_height_assumed_m=PANEL_HEIGHT_M,assumed_tree_sector=sector,
                        derived_horizon_deg=round(angle,3),unshaded_poa_kwh_m2=round(baseline,3),
                        screened_poa_kwh_m2=round(new,3),
                        direct_only_poa_loss_pct=round(100*(1-new/baseline),3),
                        beam_blocked_daylight_hours=int((mask&(df.ALLSKY_SFC_SW_DNI.to_numpy()>0)).sum())))
    trees=pd.DataFrame(tree_rows)
    trees.to_csv(outdir/"tree_height_setback_sensitivity.csv",index=False)
    fig,ax=plt.subplots(figsize=(8,5))
    for (t,a),_ in bases.items():
        f=uniform[(uniform.tilt_deg==t)&(uniform.azimuth_deg==a)]
        ax.plot(f.horizon_deg_assumed,f.direct_only_poa_loss_pct,"o-",label=str(t)+"deg tilt "+str(a)+"deg az")
    ax.set(xlabel="Hypothetical uniform obstruction angle (degrees)",
           ylabel="Direct-beam-screened POA loss (%)",
           title="Site A: hypothetical horizon, NOT measured tree shading")
    ax.grid(alpha=.2);ax.legend(fontsize=8);fig.tight_layout()
    fig.savefig(outdir/"horizon_sensitivity.png",dpi=150);plt.close(fig)
    summary=dict(status="EXPLORATORY_ASSUMPTION_NOT_SITE_SHADE_MEASUREMENT",
        site_lat=LAT,site_lon=LON,source_lat=6.2523,source_lon=-75.0143,
        assumed_level_ground=True,assumed_panel_midheight_m=PANEL_HEIGHT_M,
        assumed_tree_heights_m=[8,12,18],assumed_setbacks_m=[5,10,20],
        assumed_tree_azimuth_sectors=["all","east","west"],
        observed_tree_heights_m=None,chosen_pv_configuration=None,
        annual_ghi_kwh_m2=round(float(df.ALLSKY_SFC_SW_DWN.sum()/1000),3),
        hours_dhi_exceeds_ghi=int((df.ALLSKY_SFC_SW_DIFF>df.ALLSKY_SFC_SW_DWN).sum()),
        source_sha256=hashlib.sha256(Path(weather).read_bytes()).hexdigest(),
        pvlib_version=pvlib.__version__,screened_tree_cases=len(trees),
        output_unit="plane-of-array kWh/m2 NOT PV DC or AC electricity",
        limitations="no sky-diffuse occlusion, canopy shape, near-array shadows, string mismatch or survey")
    (outdir/"RESULTS_AND_LIMITATIONS.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("SITE_A_SUMMARY_JSON="+json.dumps(summary))
    print("SITE_A_TREE_SOUTH_WEST_JSON="+trees.query("tilt_deg==10 and azimuth_deg==180 and assumed_tree_sector=='west'").to_json(orient="records"))
    print("SITE_A_FULL_TREES_JSON="+trees.to_json(orient="records"))
    print("SITE_A_UNIFORM_HORIZON_JSON="+uniform.to_json(orient="records"))
    print("SITE_A_ORIENTATION_JSON="+pd.DataFrame([{"tilt_deg":t,"azimuth_deg":a,"unshaded_poa_kwh_m2":round(v,3)} for (t,a),v in bases.items()]).to_json(orient="records"))
    return summary

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--weather",type=Path,default=Path(__file__).resolve().parents[2]/"data"/"NASA_POWER_SanRafael_hourly_2025.csv")
    parser.add_argument("--outdir",type=Path,default=Path("site_a_solar_results"))
    a=parser.parse_args()
    run(a.weather,a.outdir)
