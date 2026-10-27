"""Offline map overlay: user reviewed locations and transformer candidate groups."""
import json
from pathlib import Path
from math import cos,pi

HERE=Path(__file__).resolve().parent
BASE=HERE.parent

def render():
    html=(BASE/"map.html").read_text(encoding="utf-8")
    controls=json.loads((BASE/"georeferencing_diagnostics.json").read_text(encoding="utf-8"))
    review=json.loads((HERE/"houses_field_review.geojson").read_text(encoding="utf-8"))
    script=(HERE/"overlay_script.fragment.html").read_text(encoding="utf-8")
    style=(HERE/"overlay_style.fragment.html").read_text(encoding="utf-8")
    a,b,c=controls["east_coefficients"]
    d,e,f=controls["north_coefficients"]
    rad=pi/180
    def pixel(lon,lat):
        u=(lon-controls["local_origin_lon"])*rad*controls["R_m"]*cos(controls["local_origin_lat"]*rad)
        v=(lat-controls["local_origin_lat"])*rad*controls["R_m"]
        det=a*e-b*d
        return {"x":round(((u-c)*e-(v-f)*b)/det,2),
                "y":round(((v-f)*a-(u-c)*d)/det,2)}
    items=[]
    for feature in review["features"]:
        p=feature["properties"]
        lon,lat=feature["geometry"]["coordinates"]
        items.append({"id":p["house_id"],"candidates":p["candidate_epm_nodes"],
                      "p":[lon,lat],"pixel":pixel(lon,lat),
                      "orig":[p["image_x"],p["image_y"]],
                      "status":p["assignment_confidence"],
                      "position_source":p["position_source"]})
    if len(items)!=35:
        raise ValueError("Expected 35 numbered archived properties")
    transformers=[
       {"name":"94022 / node 931076","lon":-75.006208238,"lat":6.246949759,"capacity":"5 kVA, archived"},
       {"name":"Northern 25 kVA candidate","lon":-75.011914005,"lat":6.249940251,"capacity":"25 kVA, 2026 portal record"}]
    for t in transformers:
        t.update(pixel(t["lon"],t["lat"]))
    colors={"923494":"#d55e00","931076":"#0072b2","823002":"#7b4fa3",
            "900607":"#009e73","923848":"#cc79a7","241054":"#b58b00",
            "alternative":"#595f6b","unassigned":"#7e8790"}
    for token,data in (("__REVIEWED__",items),("__TRANSFORMERS__",transformers),("__PALETTE__",colors)):
        script=script.replace(token,json.dumps(data,separators=(",",":")))
    return html.replace("</head>",style+"</head>").replace("</body>",script+"</body>")

if __name__=="__main__":
    path=HERE/"satellite_epm_review_overlay.html"
    path.write_text(render(),encoding="utf-8")
    print("Created map overlay:",path)
