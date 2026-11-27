#!/usr/bin/env python3
"""Final annual validation of five new A0 85398 designs, reusing signed archives."""
import hashlib,json,os,platform,sys,time,traceback
import numpy as np
import pandas as pd
from remote_94022_stress import ROOT,OUT,STUDY,run,save,restore
import remote_85398_A0_sizing as src
import remote_94022_A1_annual as runner
import sizing_priority_pilot as sizing
import sizing_ac_sample as sample
import reserve_full_night as rn
from audit_battery_coverage import read_frame

EXPECTED=json.loads("{\"A0_85398_P18_B5\":{\"sha\":\"c2d6525cd459f6680144d4aba55f36c11ad7ed14909e4c9947c30142a9f114e7\",\"cost\":1905.9364020587375,\"imports\":278.86172713689996,\"spill\":1582.6126174702,\"cycles\":216.45204141523612},\"A0_85398_P17_B5\":{\"sha\":\"c5c282896b8a0e7c9d46f5108e0313aa9ab499cca9b956db88aa745be4ed3729\",\"cost\":1914.0501643108666,\"imports\":415.8509896631,\"spill\":1204.8851718545,\"cycles\":210.45665410081463},\"A0_85398_P16_B5\":{\"sha\":\"05fc3481a63a6a3eb141bdacc93c967bffadb8a0b84d19029cf56b696e724952\",\"cost\":1936.0526353677437,\"imports\":600.7323515177,\"spill\":880.0624267226999,\"cycles\":202.08932694297047},\"A0_85398_P20_B4\":{\"sha\":\"539a799ef0344475f6496ab956c58e25bda692ab10a649d4434afc6fb83357cd\",\"cost\":1792.6838564479501,\"imports\":175.32099237569997,\"spill\":2526.5273064157,\"cycles\":274.78398167170536},\"A0_85398_P17_B4\":{\"sha\":\"7f8c0d1470ce56a8b7cb188314a1e700faa5f277e58bfb1e4dfcc16ce5f78af9\",\"cost\":1789.7733627725195,\"imports\":492.3171232956,\"spill\":1289.6121897296,\"cycles\":258.0304317698161}}")
PRIOR=json.loads("[{\"case\":\"A0_85398_P18_B5\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":41,\"converged\":41,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9608487666470827,\"maximum_voltage_pu\":0.9991439875647476,\"peak_transformer_pct\":35.46194287464451,\"peak_line_pct\":8.268481165615126,\"optional_under_097_hours\":12,\"optional_above_103_hours\":0,\"evidence\":\"NEW_AC_SAMPLE\",\"first_failed_timestamps\":[],\"energy_sha256\":\"c2d6525cd459f6680144d4aba55f36c11ad7ed14909e4c9947c30142a9f114e7\"},{\"case\":\"A0_85398_P17_B5\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":41,\"converged\":41,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9592968526108618,\"maximum_voltage_pu\":0.9991439875647476,\"peak_transformer_pct\":44.68725803376102,\"peak_line_pct\":8.268481165615126,\"optional_under_097_hours\":12,\"optional_above_103_hours\":0,\"evidence\":\"NEW_AC_SAMPLE\",\"first_failed_timestamps\":[],\"energy_sha256\":\"c5c282896b8a0e7c9d46f5108e0313aa9ab499cca9b956db88aa745be4ed3729\"},{\"case\":\"A0_85398_P16_B5\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":41,\"converged\":41,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9592968526108618,\"maximum_voltage_pu\":0.9991439875647476,\"peak_transformer_pct\":44.68725803376102,\"peak_line_pct\":8.287232817669606,\"optional_under_097_hours\":12,\"optional_above_103_hours\":0,\"evidence\":\"NEW_AC_SAMPLE\",\"first_failed_timestamps\":[],\"energy_sha256\":\"05fc3481a63a6a3eb141bdacc93c967bffadb8a0b84d19029cf56b696e724952\"},{\"case\":\"A0_85398_P20_B4\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":41,\"converged\":41,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9608487666470827,\"maximum_voltage_pu\":0.9991439875647476,\"peak_transformer_pct\":41.28289551049657,\"peak_line_pct\":8.268481165615126,\"optional_under_097_hours\":12,\"optional_above_103_hours\":0,\"evidence\":\"NEW_AC_SAMPLE\",\"first_failed_timestamps\":[],\"energy_sha256\":\"539a799ef0344475f6496ab956c58e25bda692ab10a649d4434afc6fb83357cd\"},{\"case\":\"A0_85398_P17_B4\",\"pf\":0.95,\"length_factor\":1.6,\"sampled_hours\":41,\"converged\":41,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9592968526108618,\"maximum_voltage_pu\":0.9991439875647476,\"peak_transformer_pct\":44.68725803376102,\"peak_line_pct\":8.268481165615126,\"optional_under_097_hours\":12,\"optional_above_103_hours\":0,\"evidence\":\"NEW_AC_SAMPLE\",\"first_failed_timestamps\":[],\"energy_sha256\":\"7f8c0d1470ce56a8b7cb188314a1e700faa5f277e58bfb1e4dfcc16ce5f78af9\"},{\"case\":\"A0_85398_P18_B5\",\"pf\":0.98,\"length_factor\":1,\"sampled_hours\":41,\"converged\":41,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.972278167549365,\"maximum_voltage_pu\":0.9993390202661693,\"peak_transformer_pct\":33.992383398062984,\"peak_line_pct\":7.968224413951636,\"optional_under_097_hours\":0,\"optional_above_103_hours\":0,\"evidence\":\"NEW_AC_SAMPLE\",\"first_failed_timestamps\":[],\"energy_sha256\":\"c2d6525cd459f6680144d4aba55f36c11ad7ed14909e4c9947c30142a9f114e7\"},{\"case\":\"A0_85398_P17_B5\",\"pf\":0.98,\"length_factor\":1,\"sampled_hours\":41,\"converged\":41,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9702117309754528,\"maximum_voltage_pu\":0.9993390202661693,\"peak_transformer_pct\":42.816896482934524,\"peak_line_pct\":7.968224413951636,\"optional_under_097_hours\":0,\"optional_above_103_hours\":0,\"evidence\":\"NEW_AC_SAMPLE\",\"first_failed_timestamps\":[],\"energy_sha256\":\"c5c282896b8a0e7c9d46f5108e0313aa9ab499cca9b956db88aa745be4ed3729\"},{\"case\":\"A0_85398_P16_B5\",\"pf\":0.98,\"length_factor\":1,\"sampled_hours\":41,\"converged\":41,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9702117309754528,\"maximum_voltage_pu\":0.9993390202661693,\"peak_transformer_pct\":42.816896482934524,\"peak_line_pct\":7.9860723512061345,\"optional_under_097_hours\":0,\"optional_above_103_hours\":0,\"evidence\":\"NEW_AC_SAMPLE\",\"first_failed_timestamps\":[],\"energy_sha256\":\"05fc3481a63a6a3eb141bdacc93c967bffadb8a0b84d19029cf56b696e724952\"},{\"case\":\"A0_85398_P20_B4\",\"pf\":0.98,\"length_factor\":1,\"sampled_hours\":41,\"converged\":41,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9725017004945335,\"maximum_voltage_pu\":0.9993390202661693,\"peak_transformer_pct\":39.54868398976723,\"peak_line_pct\":7.968224413951636,\"optional_under_097_hours\":0,\"optional_above_103_hours\":0,\"evidence\":\"NEW_AC_SAMPLE\",\"first_failed_timestamps\":[],\"energy_sha256\":\"539a799ef0344475f6496ab956c58e25bda692ab10a649d4434afc6fb83357cd\"},{\"case\":\"A0_85398_P17_B4\",\"pf\":0.98,\"length_factor\":1,\"sampled_hours\":41,\"converged\":41,\"strict_failures\":0,\"night_failures\":0,\"daylight_failures\":0,\"low_voltage_hours\":0,\"high_voltage_hours\":0,\"transformer_overload_hours\":0,\"line_overload_hours\":0,\"minimum_voltage_pu\":0.9702117309754528,\"maximum_voltage_pu\":0.9993390202661693,\"peak_transformer_pct\":42.816896482934524,\"peak_line_pct\":7.968224413951636,\"optional_under_097_hours\":0,\"optional_above_103_hours\":0,\"evidence\":\"NEW_AC_SAMPLE\",\"first_failed_timestamps\":[],\"energy_sha256\":\"7f8c0d1470ce56a8b7cb188314a1e700faa5f277e58bfb1e4dfcc16ce5f78af9\"}]")
ARCHIVE=json.loads("{\"A1_85398_ss90_to_A0|0.95|1\":\"fe3ee7cdc2e1d5e3df3a4f47b51e01c49b67ceb30f9163cb979d57141a613a6d\",\"A1_85398_ss90_to_A0|0.95|1.3\":\"ab6b1eb21136e9e6260130c898d06dcb0831f8eecfb4364623ecb3f1d490f40f\",\"A1_85398_ss90_to_A0|0.95|1.6\":\"8b6f9dc1cf9dba92f5283f0963bcae0d4ef129da28ae5c0a29119f3c5204c5f0\",\"A1_85398_ss90_to_A0|0.98|1\":\"749804ff5a62830c39e3077a022fd6e070b3af1ac53a29e492adc8890d65f979\",\"A1_85398_ss90_to_A0|0.98|1.3\":\"cc46c46067e733c2f65b0ce562c88fc35f371b22ac6ad65ade9586ed3003f6ca\",\"A1_85398_ss90_to_A0|0.98|1.6\":\"b9b50d8083c7b0f0f4a8347c7ce4397f1d47d1477235ca9900efa6f2008dad88\",\"A1_85398_ss90_to_A0|1|1\":\"ccefe97ab6b1f1ea37af8b15615c81a304f86bd41690421b2ddf1f94e6b3b56f\",\"A1_85398_ss90_to_A0|1|1.3\":\"dc7d891452f200223053128da4b973d2f361ba7f73a70c351433db854941b46e\",\"A1_85398_ss90_to_A0|1|1.6\":\"76b9014375819704558728b163f2f1348bedf4fa0a99ab0e818d46f0b989b58d\",\"A1_85398_min_cost_to_A0|0.95|1\":\"915d2731ebf96d2579a9b020d748027f06b9e73f1eac74b6f61cb687046a7a29\",\"A1_85398_min_cost_to_A0|0.95|1.3\":\"e69297dbfa1badf9cb78c5168de810a0201b47b801cc879e97373d8ce045a387\",\"A1_85398_min_cost_to_A0|0.95|1.6\":\"5f910374eed3480a1cb496a3b3bf35d92deaf737828d52a90c9e998dfd5881e1\",\"A1_85398_min_cost_to_A0|0.98|1\":\"d417271819a30c82cac3f3d78997b5ffcb2e433ff9187256191d411375d317f0\",\"A1_85398_min_cost_to_A0|0.98|1.3\":\"f87bd52c420b7016bc9d7e86f4326a44ff6c0468a0c8c37442a917632248f511\",\"A1_85398_min_cost_to_A0|0.98|1.6\":\"735636288137f56ab5a9a3a31a600ee7a8b1e9ae7098870308f85c07b057e074\",\"A1_85398_min_cost_to_A0|1|1\":\"5098c4c3bbbf9ee3abeafb66d5516c65c82e48b4a5874547a97110691d0076b5\",\"A1_85398_min_cost_to_A0|1|1.3\":\"6b53865baa0703e3a2d66a0dc377adb3968f1c1007e6fa899c15a2fb65580991\",\"A1_85398_min_cost_to_A0|1|1.6\":\"9f05a5d9d945a36c387f2951e840069f3ccf99c53da8ffd327da119487a9ad06\",\"A0_85398_min_cost_four|0.95|1\":\"4771bc8ab2342efed756a52e566cd9ee682d05353e37cba711e4d5aefd17cc8c\",\"A0_85398_min_cost_four|0.95|1.3\":\"726c9ab156b8464194f452d47dd84c5978e9da4217206b38e0a350063b05828d\",\"A0_85398_min_cost_four|0.95|1.6\":\"42488ccb9fe46a3b0e17e86ac78d25ef16b545322834a8912ff93950b9f122bd\",\"A0_85398_min_cost_four|0.98|1\":\"15b53c84bb03ce151da0711a24baf90f1a571dfa1c4aa4f880d36e98e86351af\",\"A0_85398_min_cost_four|0.98|1.3\":\"37b3197b2229eafd75858c8299e3b99b79469754954f715f172cea5b6a18f9cb\",\"A0_85398_min_cost_four|0.98|1.6\":\"8200b52c90407d430744f5f7cd0ed5ed2b0c7c1d09553c500442b088ecb78d4f\",\"A0_85398_min_cost_four|1|1\":\"385b9a56a0368fac7746d18eb4601b9bfd261c155650e2003641476fd37d106e\",\"A0_85398_min_cost_four|1|1.3\":\"3b019865ee184e9a03292a2a92d986697983e0f09a2a7c0a8893d5b73446d8a1\",\"A0_85398_min_cost_four|1|1.6\":\"4340c22bb2750e5fd9936c5cc4bdc2aa5ebd9f07780c9d05eb79b47c9568436c\",\"A0_85398_ss90_four|0.95|1\":\"66c661d0c655d9e244cd07a8ad50ea15f03741401af4651655f92d61d3981e7c\",\"A0_85398_ss90_four|0.95|1.3\":\"b87079b1a4c3d94ce4f3175388c1ad8a29beba25a016a1102473f201ac89ba17\",\"A0_85398_ss90_four|0.95|1.6\":\"cad9e7071937c8c9a86cecc755789ee26d2e5441744f7ea7d12cc2275ac4f3cc\",\"A0_85398_ss90_four|0.98|1\":\"85dda464cd8bdd13df12ee2f3e7984d16f0f641b3b59f75ebc50f6b1e6c602c8\",\"A0_85398_ss90_four|0.98|1.3\":\"afe466bcad3116bf6ed2b345a8bac261da1f5d1cc71d520a58f8cfefb409700b\",\"A0_85398_ss90_four|0.98|1.6\":\"8839b6d7a076ea0fe9f6a092e56900b4e0f2113a3c6b90e3a1b71afec4c087d6\",\"A0_85398_ss90_four|1|1\":\"f52eadcfae3ad11f072f285fe006b832fc204803af9ce0dfc60bc1235793fc0c\",\"A0_85398_ss90_four|1|1.3\":\"16b37beb8a21fb3c41f66f3ddca59bd2b951a545ade71a3c84281f444303219c\",\"A0_85398_ss90_four|1|1.6\":\"21d008a08d08bb842352028b9a9288ceee961a88038da6fe71802fe99342719f\"}")
HOURS_SHA="8fc4b68f744a38e8e03bcb8cd1be9ffb620bedc889bd21f1c42893b351261ca8"
FACTORS=((.98,1.),(.95,1.6))
CASES=tuple(EXPECTED)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def plan_gate():
    if len(CASES)!=5 or set(CASES)!={r[0] for r in src.PLAN} or len(ARCHIVE)!=36:
        raise ValueError("Source population")
    if len(PRIOR)!=10 or {(r["case"],r["pf"],r["length_factor"]) for r in PRIOR}!={(c,p,l) for c in CASES for p,l in FACTORS}:
        raise ValueError("Sample population")
    if any(r["strict_failures"] or r["converged"]!=41 or r["energy_sha256"]!=EXPECTED[r["case"]]["sha"] for r in PRIOR):
        raise ValueError("Sample evidence identity")

def archive_gate(x):
    got={f'{r["case"]}|{r["pf"]:g}|{r["length_factor"]:g}':r["source_ac_sha256"] for r in x["archive_receipts"]}
    if got!=ARCHIVE or len(x["archive_receipts"])!=36 or any(r["strict_failures"] or r["converged"]!=8760 for r in x["archive_receipts"]):
        raise ValueError("Archive identity")

def reconstruct(prepared,report):
    fh,v6,annual,x=prepared
    for c,h in x["candidates"].items():
        hw=fh.Hardware(panels=h["pv_panels"],battery_modules=h["battery_modules"],
            battery_power_dc_kw=h["battery_power_dc_kw"],inverter_kva=h["inverter_kva"],
            transformer_kva=h["transformer_kva_assumed_or_evidenced"],loading_pu=1.,load_pf=.98,
            export_policy="zero",annual_equipment_usd=float("nan"),annual_total_usd=float("nan"))
        f,sm=fh.solve_fixed(ROOT,hw,x["demand"],x["solar"],min_physical_soc=.20)
        f.index.name="timestamp_lst";sizing.validate_comparison(f,h,x["demand"],x["solar"])
        path=OUT/(c+"_8760.csv");f.to_csv(path,float_format="%.10f")
        e=EXPECTED[c]
        if sha(path)!=e["sha"]:raise ValueError("Exact energy reconstruction "+c)
        f=read_frame(path);sizing.validate_comparison(f,h,x["demand"],x["solar"])
        m=sizing.summary(c,"A0_85398_four_house","RECONSTRUCTED_SIZING",h,f,sm)
        for k,v in (("annual_total_usd",e["cost"]),("import_ac_kwh",e["imports"]),("curtail_dc_kwh",e["spill"]),("store_equivalent_discharge_cycles",e["cycles"])):
            if abs(m[k]-v)>1e-6:raise ValueError("Energy metric identity "+c+" "+k)
        x["frames"][c]=f;x["hardware"][c]=h;x["models"][c]=sm;x["signatures"][c]=e["sha"]
    hours=sample.pick_hours(x["frames"],x["archived_risk_hours"])
    path=OUT/"COMMON_SAMPLE_HOURS.csv"
    pd.DataFrame({"timestamp_lst":hours}).to_csv(path,index=False)
    if len(hours)!=41 or sha(path)!=HOURS_SHA:raise ValueError("Common sample identity")
    report.update(reconstructed_LPs=5,verified_new_energy_schedules=5,common_hours=41,
        reused_archived_annual_groups=36,reused_archived_annual_case_hours=315360,
        prior_AC_sample_repeated=False)
    return set(hours)

def annual_validation(prepared,hours,report):
    import pandapower as pp
    from run_epm_validation import build_net
    fh,v6,annual,x=prepared
    results=[];checks=0;report["annual_results"]=results
    for c in CASES:
        f=x["frames"][c];e=EXPECTED[c]
        for pf,l in FACTORS:
            terr=x["territories"][l];net,meta=build_net(terr,"head")
            if set(meta["loads"])!=set(x["ids"]):raise ValueError("Household identity")
            rows=[]
            for i,t in enumerate(f.index):
                q=runner.checked(v6,pp,net,meta,terr,x,c,t,pf)
                q.update(case=c,pf=pf,length_factor=l,energy_sha256=e["sha"],
                    reference_energy_sha256=src.EXPECTED[src.REF],source_grid_import_kw=float(f.at[t,"grid_import_kw"]),
                    strict_feasible=rn.strict_point(q))
                rows.append(q)
                if (i+1)%2000==0:print("Annual",c,pf,l,i+1,flush=True)
            a=pd.DataFrame(rows)
            if len(a)!=8760 or not pd.DatetimeIndex(pd.to_datetime(a.timestamp_lst)).equals(f.index):
                raise ValueError("Annual chronology")
            select=a[pd.to_datetime(a.timestamp_lst).isin(hours)]
            expected=next(r for r in PRIOR if r["case"]==c and r["pf"]==pf and r["length_factor"]==l)
            if len(select)!=41:raise ValueError("Annual sample coverage")
            runner.sample_regression(runner.stats(select),expected);checks+=41
            name=c+"_PF"+str(round(pf*100))+"_L"+str(round(l*10))+"_ANNUAL_AC.csv"
            annual.save_csv(OUT/name,rows)
            loss=float(a.loss_kw.sum())
            result=dict(case=c,pf=pf,length_factor=l,hours=8760,energy_sha256=e["sha"],
                reference_energy_sha256=src.EXPECTED[src.REF],**runner.stats(a),losses_kwh=loss,
                annual_energy_cost_usd=e["cost"],all_loss_purchase_cost_usd=e["cost"]+.29*loss,
                annual_import_kwh=float(f.grid_import_kw.sum()),annual_curtail_dc_kwh=float(f.curtailed_pv_dc_kw.sum()),
                failed_timestamps_first_30=a.loc[~a.strict_feasible,"timestamp_lst"].astype(str).head(30).tolist(),
                output_sha256=sha(OUT/name))
            results.append(result);print("A0_85398_ANNUAL_RESULT="+json.dumps(result,allow_nan=False),flush=True)
            save(OUT/"PARTIAL_RESULTS.json",report)
    if checks!=410 or len(results)!=10:raise ValueError("Annual regression coverage")
    pd.DataFrame(results).to_csv(OUT/"A0_85398_ANNUAL_AC_SUMMARY.csv",index=False)
    pd.DataFrame(x["archive_receipts"]).to_csv(OUT/"A0_85398_ARCHIVED_ANNUAL_COMPARATORS.csv",index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    a=pd.DataFrame(results)
    fig,ax=plt.subplots(1,2,figsize=(12,5),layout="constrained")
    labels=[c.replace("A0_85398_","") for c in CASES]
    for i,(pf,l) in enumerate(FACTORS):
        s=a[a.pf.eq(pf)&a.length_factor.eq(l)].set_index("case").loc[list(CASES)]
        xx=np.arange(len(CASES))+(i-.5)*.36
        ax[0].bar(xx,s.minimum_voltage_pu,.36,label=f"PF {pf}, length {l}")
        ax[1].bar(xx,s.all_loss_purchase_cost_usd,.36,label=f"PF {pf}, length {l}")
    ax[0].axhline(.95,ls="--",color="firebrick")
    ax[0].set_ylim(min(.93,float(a.minimum_voltage_pu.min())-.002),1.05)
    ax[0].set_ylabel("Annual minimum voltage (pu)")
    ax[1].set_ylabel("Annual modeled cost incl. loss sensitivity (USD)")
    for z in ax:z.set_xticks(range(len(CASES)),labels,rotation=35,ha="right");z.legend(fontsize=8)
    fig.suptitle("85398 A0 | annual AC and costs for five new designs")
    for ext in ("png","svg"):fig.savefig(OUT/("A0_85398_annual."+ext),dpi=180)
    plt.close(fig)
    report.update(status="COMPLETE_A0_85398_FIVE_DESIGN_ANNUAL",sampled_case_hours_reconciled=checks,
        annual_sample_summary_groups=10,new_AC_case_hours=87600,
        annual_passing_groups=sum(r["strict_failures"]==0 for r in results))

def main():
    OUT.mkdir(exist_ok=False);start=time.perf_counter()
    preflight=sys.argv[1:]==["--preflight-only"]
    report=dict(status="INCOMPLETE",mode="preflight" if preflight else "research",job_id=os.environ.get("CI_JOB_ID"),
        pipeline_id=os.environ.get("CI_PIPELINE_ID"),execution_commit=os.environ.get("CI_COMMIT_SHA"),
        runner_id=os.environ.get("CI_RUNNER_ID"),prior_sizing_job=18424297982,selected_cases=list(CASES),
        factors=[list(z) for z in FACTORS],planned_annual_AC_case_hours=87600,
        field_verified=False,offline_perfect_foresight=True,no_new_equipment_design=True,night_Q_disabled=True)
    try:
        if sys.argv[1:] not in ([],["--preflight-only"]) or platform.system()!="Windows" or sys.version_info[:3]!=(3,12,9) or os.environ.get("RUNNER_VERIFIED_SESSION_ID")!="0":raise ValueError("Unexpected environment")
        run(["-m","unittest","discover","-s",STUDY,"-p","test_remote_signed_source_checkout.py","-v"],"source_portability_tests")
        report["source_byte_audit"]=restore(ROOT,OUT)
        for test in ("test_remote_A0_85398_sizing.py","test_remote_A0_85398_annual.py","test_remote_A1_94022_annual.py"):
            run(["-m","unittest","discover","-s",STUDY,"-p",test,"-v"],test)
        plan_gate()
        prepared=src.prepare()
        _,_,_,x=prepared;archive_gate(x)
        if x["signatures"]!=src.EXPECTED or set(x["candidates"])!=set(EXPECTED):raise ValueError("Preflight source set")
        if preflight:report["status"]="COMPLETE_SIGNED_A0_85398_ANNUAL_PREFLIGHT"
        else:
            hours=reconstruct(prepared,report)
            annual_validation(prepared,hours,report)
    except Exception as exc:
        report["error"]=repr(exc);traceback.print_exc()
    finally:
        report["duration_s"]=round(time.perf_counter()-start,3)
        report["output_sha256"]={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}
        save(OUT/"A0_85398_ANNUAL_REPORT.json",report)
        print("A0_85398_ANNUAL_REPORT_JSON="+json.dumps(report,separators=(",",":"),allow_nan=False),flush=True)
    return 0 if report["status"] in ("COMPLETE_SIGNED_A0_85398_ANNUAL_PREFLIGHT","COMPLETE_A0_85398_FIVE_DESIGN_ANNUAL") else 1

if __name__=="__main__":raise SystemExit(main())
