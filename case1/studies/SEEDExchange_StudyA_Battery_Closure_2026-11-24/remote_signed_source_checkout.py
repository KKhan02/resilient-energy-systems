#!/usr/bin/env python3
"""Restore signed byte representations in an isolated CI checkout only.
Require both HEAD blob and checkout content to equal the signed bytes exactly
or differ by one uniform LF/CRLF conversion. Never change a receipt or pin.
"""
from pathlib import Path
import hashlib,json,os,subprocess

MANIFEST="case1/studies/SEEDExchange_StudyA_v6_LocalRunner/outputs/run_01/input_manifest_v6_2.json"
MANIFEST_SHA="2ff7eb9c1f28f12efc11aca9b366e5277da72a62f6d7709f47dc3841b6e71d69"
RUNNER="case1/studies/SEEDExchange_StudyA_v6_LocalRunner/seed_study_a_v6.py"
V4="case1/studies/SEEDExchange_StudyA_LocalPreflight_v4/outputs/run_02/"
GIS="case1/studies/epm_gis_pandapower_v1/data/"
def sha(b):return hashlib.sha256(b).hexdigest()
def signed_bytes(raw,expected):
    if sha(raw)==expected:return raw,"EXACT"
    if b"\r" not in raw:
        alt=raw.replace(b"\n",b"\r\n");mode="LF_TO_CRLF"
    elif b"\r" not in raw.replace(b"\r\n",b"") and b"\n" not in raw.replace(b"\r\n",b""):
        alt=raw.replace(b"\r\n",b"\n");mode="CRLF_TO_LF"
    else:raise ValueError("Mixed newline file differs from signature")
    if sha(alt)!=expected:raise ValueError("Not an exact newline-only match")
    return alt,mode
def git_blob(root,rel):
    return subprocess.check_output(["git","show","HEAD:"+rel],cwd=root)
def inspect(root,rel,expected):
    path=(root/rel).resolve()
    if not path.is_relative_to(root) or not path.is_file():raise ValueError("Invalid checkout path "+rel)
    blob=git_blob(root,rel);raw=path.read_bytes()
    try:
        want,bmode=signed_bytes(blob,expected)
        local,lmode=signed_bytes(raw,expected)
    except ValueError as e:
        raise ValueError(f"{rel}: expected {expected}; blob {sha(blob)}; checkout {sha(raw)}; {e}") from e
    if want!=local:raise ValueError("Signed representation mismatch "+rel)
    return path,want,dict(path=rel,expected_sha256=expected,git_blob_sha256=sha(blob),
                          checkout_before_sha256=sha(raw),git_blob_mode=bmode,checkout_mode=lmode,
                          checkout_after_sha256=sha(want),changed=raw!=want)
def restore(root,out):
    root=root.resolve()
    if os.environ.get("CI_PROJECT_ID")!="88036556" or os.environ.get("CI_RUNNER_ID")!="60033802" or os.environ.get("CI_COMMIT_REF_PROTECTED")!="true":
        raise RuntimeError("Restoration is restricted to the approved isolated CI checkout")
    if Path(os.environ["CI_PROJECT_DIR"]).resolve()!=root or not os.environ.get("CI_COMMIT_BRANCH","").startswith("execution/research-"):
        raise RuntimeError("Unexpected checkout location or branch")
    first=inspect(root,MANIFEST,MANIFEST_SHA);m=json.loads(first[1].decode("utf-8"))
    pins={RUNNER:m["script_sha256"],**m["model_source_hashes"],
        V4+"fixed_house_to_profile_map.csv":m["mapping_sha256"],
        V4+"household_profiles_2025_excel_35.csv":m["profiles_sha256"],
        GIS+"epm_network_relevant_sanitized.geojson":m["gis_geojson_sha256"],
        GIS+"houses_candidate_associations.csv":m["gis_house_sha256"]}
    if len(pins)!=11 or m["population_houses"]!=35 or m["2025_hours"]!=8760:raise ValueError("Signed input population changed")
    planned=[first]+[inspect(root,k,v) for k,v in pins.items()]
    # Complete validation of ALL files before any byte restoration.
    for path,want,record in planned:
        if record["changed"]:path.write_bytes(want)
        if sha(path.read_bytes())!=record["expected_sha256"]:raise ValueError("Post-restoration hash mismatch")
    report=dict(status="EXACT_SIGNED_CHECKOUT",execution_commit=os.environ["CI_COMMIT_SHA"],
        job_id=os.environ["CI_JOB_ID"],files=[r for _,_,r in planned],
        restored_count=sum(r["changed"] for _,_,r in planned),signed_files=len(planned),
        signed_receipts_changed_in_git=False,scientific_inputs_changed=False)
    (out/"SOURCE_BYTE_AUDIT.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("SOURCE_BYTE_AUDIT_JSON="+json.dumps(report,separators=(",",":")),flush=True)
    return report
