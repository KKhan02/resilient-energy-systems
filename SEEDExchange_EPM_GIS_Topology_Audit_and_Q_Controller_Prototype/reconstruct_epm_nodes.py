"""Inspect exact EPM line endpoint-node connectivity for six known transformer IDs.

Input: user's epm_gis.zip, no external downloads. No service drops inferred.
"""
from pathlib import Path
import zipfile,json,csv,networkx as nx
HERE=Path(__file__).parent
with zipfile.ZipFile(HERE.parent/'epm_gis.zip') as z:
    lv=json.loads(z.read('epm_gis/epm_kml_5km/secondary_lines_LV.geojson'))['features']
    tr=json.loads(z.read('epm_gis/epm_kml_5km/transformers.geojson'))['features']
seen={str(f['properties'].get('NRO_TRANSFORMADOR')):f for f in tr}
ids=['94022','106039','113699','85398','98380','92395']
rows=[]
for ident in ids:
 f=seen[ident];p=f['properties'];node=p['NODO_TRANSFORM_CONN'];root=str(p.get('NODO2_ID'))
 segs=[f for f in lv if str(f['properties'].get('NODO_TRANSFORM_CONN'))==str(node)]
 G=nx.Graph()
 for s in segs:
  a,b=s['properties'].get('NODO1_ID'),s['properties'].get('NODO2_ID'); b=f'END_{s["properties"].get("G3E_FID")}' if b in (0,None,'0') else str(b)
  a=str(a)
  G.add_edge(a,b,segment_id=s['properties'].get('G3E_FID'))
 rootsize=len(nx.node_connected_component(G,root)) if root in G else 0
 components=list(nx.connected_components(G))
 rows.append(dict(transformer=ident,trafo_lv_node=root,line_count=len(segs),graph_node_count=len(G),components=len(components),all_segments_root_reachable=(root in G and rootsize==len(G)),radial_graph=(nx.is_forest(G) if len(G) else None),unresolved_terminal_zero=sum(s['properties'].get('NODO2_ID') in (0,None,'0') for s in segs)))
 print(rows[-1])
with open(HERE/'epm_node_graph_validation.csv','w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
