#!/usr/bin/env python3
"""Optional EPM read-only bounded query; never fetches customer meters or PII.

Service schema availability does not establish available features, validity or territory.
"""
import argparse
import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen

HERE=Path(__file__).resolve().parent
BASE="https://podascens.epm.com.co/arcgis/rest/services/Disponibilidad2023/MapServer"
LAYERS={0:"transformer_availability",3:"lv_nodes",5:"transformers",6:"lv_sections",7:"mv_sections"}
KEEP={"OBJECTID","CODE","ELNODE","LVELNODE","FPARENT","PHNODE",
      "FROMNODE","TONODE","FNODE","TNODE","LENGTH","LEN","MATERIAL",
      "CONDUCTOR","FEEDER","CIRCUITO_ALIMENTADOR","CODIGO_TRANSFORMADOR",
      "CAPACIDAD_INSTALADA_TRAFO","CUSTOMERS","CANTIDAD_CLIENTES_DEL_TRAFO",
      "LATITUD","LONGITUD","LIM_POTENCIA_INYEC_KW","FASES_DEL_TRANSFORMADOR"}

def bbox_from_features(features,margin=0.01):
    coords=[f["geometry"]["coordinates"] for f in features]
    return [min(p[0] for p in coords)-margin,min(p[1] for p in coords)-margin,
            max(p[0] for p in coords)+margin,max(p[1] for p in coords)+margin]

def query(layer,bbox,offset,timeout):
    params={"f":"geojson","where":"1=1","outFields":"*","returnGeometry":"true",
            "geometryType":"esriGeometryEnvelope",
            "geometry":",".join(map(str,bbox)),"inSR":"4326","outSR":"4326",
            "spatialRel":"esriSpatialRelIntersects",
            "resultOffset":offset,"resultRecordCount":1000}
    url=BASE+"/"+str(layer)+"/query?"+urlencode(params)
    req=Request(url,headers={"User-Agent":"SEEDExchange-energy-research-gis/1.0"})
    with urlopen(req,timeout=timeout) as response:
        data=json.load(response)
    if "error" in data:raise RuntimeError(str(data["error"]))
    if data.get("type")!="FeatureCollection" or not isinstance(data.get("features"),list):
        raise RuntimeError("No GeoJSON FeatureCollection returned")
    return data

def sanitize(features):
    result=[]
    for f in features:
        geom=f.get("geometry")
        if not geom or geom.get("type") not in {"Point","LineString","MultiLineString"}:
            continue
        p=f.get("properties") or {}
        result.append({"type":"Feature","geometry":geom,
                       "properties":{k:v for k,v in p.items() if k.upper() in KEEP}})
    return result

def run(outdir,timeout):
    geo=json.loads((HERE/"house_points_provisional.geojson").read_text(encoding="utf-8"))
    bbox=bbox_from_features(geo["features"])
    outdir.mkdir(parents=True,exist_ok=True)
    status={"source":BASE,"query_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
            "bbox_wgs84":bbox,"complete_retrieval":False,"feature_records_confirmed":False,
            "customer_meter_layer_queried":False,"layers":{}}
    for lid,name in LAYERS.items():
        record={"layer_id":lid,"status":"not_available","features":0,"complete":False}
        try:
            features=[]
            for n in range(3):
                page=query(lid,bbox,n*1000,timeout)
                batch=page["features"];features.extend(batch)
                if len(batch)<1000 and not page.get("exceededTransferLimit",False):
                    record["complete"]=True
                    break
            cleaned=sanitize(features)
            (outdir/(name+".geojson")).write_text(
                json.dumps({"type":"FeatureCollection","features":cleaned},indent=2)+"\n",encoding="utf-8")
            record.update({"status":"queried","features":len(cleaned)})
            status["feature_records_confirmed"]|=len(cleaned)>0
        except Exception as exc:
            record["error"]=str(exc)[:220]
        status["layers"][name]=record
    status["complete_retrieval"]=all(x["complete"] for x in status["layers"].values())
    (outdir/"epm_query_status.json").write_text(json.dumps(status,indent=2)+"\n",encoding="utf-8")
    print("EPM_QUERY_RESULT="+json.dumps(status["layers"],separators=(",",":")))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--outdir",type=Path,default=HERE/"epm_probe")
    ap.add_argument("--timeout",type=int,default=9)
    args=ap.parse_args()
    run(args.outdir,args.timeout)
