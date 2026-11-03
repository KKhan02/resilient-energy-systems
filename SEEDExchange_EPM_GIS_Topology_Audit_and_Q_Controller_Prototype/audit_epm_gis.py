#!/usr/bin/env python3
"""Reproducible, read-only audit of user-provided EPM public-network GeoJSON.

Requires shapely, pyproj, matplotlib for plotting. No network requests.
Note: Does not establish customer service drops, energized network or cable impedance.
"""
import zipfile,json,collections,csv,math,os
from pathlib import Path
from shapely.geometry import shape,Point,LineString,mapping
from shapely.ops import transform as sh_transform
from pyproj import Transformer
import pandas as pd

HERE=Path(__file__).parent
INPUT=HERE.parent/'epm_gis.zip'
PREFIX='epm_gis/epm_kml_5km/'
read=lambda f:list(csv.DictReader(open(HERE/f,encoding='utf-8-sig',newline='')))
trafo=read('transformers_evidence.csv');house=read('houses_candidate_associations.csv')
T={str(t['epm_node']):t for t in trafo if t['epm_node']!='UNCONFIRMED'}
P=Transformer.from_crs('EPSG:4326','EPSG:32618',always_xy=True).transform
getgeom=lambda f:sh_transform(P,shape(f['geometry']))
with zipfile.ZipFile(INPUT) as z:
 data={k:json.loads(z.read(PREFIX+k+'.geojson'))['features'] for k in ('transformers','secondary_lines_LV','primary_lines_MV','poles')}
for f in data['secondary_lines_LV']:
 f['_g']=getgeom(f)
for f in data['transformers']:
 f['_g']=getgeom(f)
TFeatures={str(f['properties'].get('NRO_TRANSFORMADOR')):f for f in data['transformers']}
line_geoms=[(f['_g'], f['properties']) for f in data['secondary_lines_LV']]
summary=[];selected=[]
for t in trafo:
 if t['epm_node']=='UNCONFIRMED':continue
 tid=t['transformer_number'];node=t['epm_node'];matches=[f for f in data['secondary_lines_LV'] if str(f['properties'].get('NODO_TRANSFORM_CONN'))==node]
 sel=TFeatures.get(tid)
 trpoint=Point(P(float(t['longitude']),float(t['latitude'])))
 min_any=min((f['_g'].distance(trpoint),f['properties'].get('NODO_TRANSFORM_CONN')) for f in data['secondary_lines_LV'])
 n_conduct=collections.Counter((str(f['properties'].get('MATERIAL')),str(f['properties'].get('CALIBRE'))) for f in matches)
 for f in matches:
  pr=f['properties'];selected.append(dict(transformer=tid, node=node, lv_segment_id=pr.get('G3E_FID'),start_node=pr.get('NODO1_ID'),end_node=pr.get('NODO2_ID'),length_epm_m=pr.get('LONGITUD_CONN'),length_geometry_m=round(f['_g'].length,2),material=pr.get('MATERIAL'),calibre=pr.get('CALIBRE'),type_line=pr.get('TIPO_LINEA_CONN'),status=pr.get('ESTADO')))
 summary.append(dict(transformer=tid,node=node,kva=t['kva'],houses=sum(h['transformer_number']==tid for h in house),gis_transformer_found=bool(sel),gis_transformer_lat=round(sel['geometry']['coordinates'][1],9) if sel else None,gis_transformer_lon=round(sel['geometry']['coordinates'][0],9) if sel else None,match_lv_segments=len(matches),epm_recorded_length_m=round(sum(float(f['properties'].get('LONGITUD_CONN') or 0) for f in matches),1),geometry_length_m=round(sum(f['_g'].length for f in matches),1),nearest_all_lv_m=round(min_any[0],1),nearest_all_lv_node=min_any[1],conductor_groups='; '.join(f'{m}/{cal}:{n}' for (m,cal),n in n_conduct.items())))

rows=[]
for h in house:
 pt=Point(P(float(h['longitude']),float(h['latitude'])));n=h['candidate_epm_node']
 assigned=[f for f in data['secondary_lines_LV'] if str(f['properties'].get('NODO_TRANSFORM_CONN'))==n]
 nearest_all=min(data['secondary_lines_LV'],key=lambda f:f['_g'].distance(pt))
 nearest_assigned=min(assigned,key=lambda f:f['_g'].distance(pt)) if assigned else None
 rows.append(dict(house=h['house_id'],assigned_transformer=h['transformer_number'],assigned_node=n,assignment_status=h['assignment_status'],distance_to_assigned_gis_lv_m=round(pt.distance(nearest_assigned['_g']),1) if nearest_assigned else None,distance_to_any_gis_lv_m=round(pt.distance(nearest_all['_g']),1),nearest_gis_lv_node=nearest_all['properties'].get('NODO_TRANSFORM_CONN'),nearest_gis_lv_segment=nearest_all['properties'].get('G3E_FID'),nearest_match=str(nearest_all['properties'].get('NODO_TRANSFORM_CONN'))==n))

pd.DataFrame(summary).to_csv(HERE/'gis_transformer_lv_crosswalk.csv',index=False)
pd.DataFrame(selected).to_csv(HERE/'gis_matched_lv_segments.csv',index=False)
pd.DataFrame(rows).to_csv(HERE/'house_to_epm_line_proximity.csv',index=False)
print('GEOGRAPHY', len(data['transformers']),len(data['secondary_lines_LV']),len(data['primary_lines_MV']),len(data['poles']))
print(pd.DataFrame(summary)[['transformer','houses','match_lv_segments','epm_recorded_length_m','geometry_length_m','nearest_all_lv_m']].to_string(index=False))
print('\nHouse nearest distances')
print(pd.DataFrame(rows)[['house','assigned_transformer','distance_to_assigned_gis_lv_m','distance_to_any_gis_lv_m','nearest_gis_lv_node','nearest_match']].to_string(index=False))
print('Closest asset already assigned count',sum(x['nearest_match'] for x in rows),'/',len(rows))

# Utility data subset only; exclude all personal names, contracts and user fields.
slim=[]
for k in ('transformers','secondary_lines_LV','primary_lines_MV','poles'):
 for f in data[k]:
  props=f['properties'];geom=f['geometry'];loc=getgeom(f)
  # limit to network around enumerated houses/transformers within 500 m where possible
  group={'transformers':'EPM transformer','secondary_lines_LV':'EPM LV','primary_lines_MV':'EPM MV','poles':'EPM pole'}[k]
  keep=('NRO_TRANSFORMADOR','NODO_TRANSFORM_CONN','CAPACIDAD_NOMINAL','UNIDAD_MED_CAPACIDAD','NODO1_ID','NODO2_ID','G3E_FID','MATERIAL','CALIBRE','CALIBRE_NEUTRO','LONGITUD_CONN','ESTADO','TIPO_LINEA_CONN','CIRCUITO_CONN','FASES_CONN','TENSION_SECUNDARIA_CONN','TIPO_RED_CONN')
  pp={'layer':group,**{x:props.get(x) for x in keep if x in props and props.get(x) is not None}}
  # only locations < 650m from at least one house
  if min(loc.distance(Point(P(float(h['longitude']),float(h['latitude'])))) for h in house)>650:continue
  slim.append({'type':'Feature','properties':pp,'geometry':geom})
(HERE/'epm_network_relevant_sanitized.geojson').write_text(json.dumps({'type':'FeatureCollection','features':slim}),encoding='utf-8')

# Map all candidate homes and EPM LV lines, colour by associated node, not hypothetical lines.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
colors={'931076':'#1e88e5','923494':'#d95f02','923848':'#9243e0','900607':'#119962','823002':'#e45386','241054':'#e0a600'}
fig,ax=plt.subplots(figsize=(11.8,8.2))
for f in data['secondary_lines_LV']:
 g=f['_g'];x,y=g.xy
 node=str(f['properties'].get('NODO_TRANSFORM_CONN'))
 ax.plot(x,y,color=colors.get(node,'#adb5bd'),lw=2.2 if node in colors else .55,alpha=.95 if node in colors else .30,zorder=1)
for h in house:
 x,y=P(float(h['longitude']),float(h['latitude']))
 ax.scatter(x,y,s=62,facecolor=colors.get(h['candidate_epm_node'],'gray'),edgecolor='white',lw=.9,zorder=4)
 ax.annotate(h['house_id'][1:],(x,y),xytext=(3,3),textcoords='offset points',fontsize=7.2,weight='semibold',zorder=5)
for t in trafo:
 if t['epm_node']=='UNCONFIRMED':continue
 x,y=P(float(t['longitude']),float(t['latitude']))
 ax.scatter(x,y,s=160,marker='*',facecolor=colors[t['epm_node']],edgecolor='black',linewidth=.8,zorder=7)
 ax.annotate(t['transformer_number'],(x,y),xytext=(6,-14),textcoords='offset points',fontsize=9,weight='bold',bbox=dict(boxstyle='round,pad=.12',fc='white',alpha=.86,ec='none'),zorder=8)
 ax.set_aspect('equal');ax.set_xticks([]);ax.set_yticks([])
ax.set_title('EPM mapped LV segments and provisional household associations',fontsize=13,weight='bold',pad=10)
handles=[Line2D([0],[0],color=col,lw=3,label=f"{next(t['transformer_number'] for t in trafo if t['epm_node']==n)}  ({sum(h['candidate_epm_node']==n for h in house)} homes)") for n,col in colors.items()]
handles += [Line2D([0],[0],color='#adb5bd',lw=1.5,label='Other EPM LV records'),Line2D([0],[0],marker='*',color='none',markerfacecolor='grey',markersize=12,label='EPM transformer')]
ax.legend(handles=handles,loc='upper right',fontsize=8,framealpha=.93)
xy=[P(float(h['longitude']),float(h['latitude'])) for h in house]
ax.set_xlim(min(x for x,y in xy)-500,max(x for x,y in xy)+400);ax.set_ylim(min(y for x,y in xy)-430,max(y for x,y in xy)+250)
fig.tight_layout();fig.savefig(HERE/'epm_lv_lines_and_candidate_houses.png',dpi=200);fig.savefig(HERE/'epm_lv_lines_and_candidate_houses.svg');plt.close(fig)
