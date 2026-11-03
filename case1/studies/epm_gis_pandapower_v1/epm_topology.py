"""EPM-LV node-graph reconstruction with explicitly assumed household service drops.

GIS line geometry and endpoint-node topology are user-supplied EPM records.
House-to-LV attachments are modelling assumptions and not customer verification.
"""
from pathlib import Path
import csv, json, math
from collections import defaultdict
from dataclasses import dataclass
import networkx as nx
from shapely.geometry import Point,LineString,shape
from shapely.ops import transform
from pyproj import Transformer

HERE=Path(__file__).resolve().parent
DATA=HERE/'data'
TO_M=Transformer.from_crs('EPSG:4326','EPSG:32618',always_xy=True).transform
FROM_M=Transformer.from_crs('EPSG:32618','EPSG:4326',always_xy=True).transform
MAIN_IDS=('94022','106039','113699','85398','98380','92395')

# Explicit illustrative conductor loop characteristics; NOT measured EPM electrical data.
# r is estimated one-way conductor Ohm/km, multiplied by 2 for phase/return loop.
# Ampacity is a screening estimate, not manufacturer/site validated.
CONDUCTOR={('AAC','1/0'):(.656,.160,180.),('AAC','2'):(1.05,.160,125.),
           ('AAC','4'):(1.65,.160,95.),('ACSR','2'):(1.12,.160,110.)}
FALLBACK=(1.65,.160,95.)

def read_csv(path):
    with open(path,encoding='utf-8-sig',newline='') as fh:return list(csv.DictReader(fh))

def read_data():
    hs=read_csv(DATA/'houses_candidate_associations.csv')
    ts=read_csv(DATA/'transformers_evidence.csv')
    f=json.loads((DATA/'epm_network_relevant_sanitized.geojson').read_text(encoding='utf-8'))['features']
    houses={h['house_id']:dict(h,x=TO_M(float(h['longitude']),float(h['latitude']))[0],
                            y=TO_M(float(h['longitude']),float(h['latitude']))[1]) for h in hs}
    raw_t={r['transformer_number']:r for r in ts}
    assets={str(p['properties'].get('NRO_TRANSFORMADOR')):p for p in f
            if p['properties'].get('layer')=='EPM transformer'}
    tr={}
    for t in MAIN_IDS:
        if t not in assets:raise ValueError('missing transformer '+t)
        v=assets[t];p=v['properties'];x,y=TO_M(*v['geometry']['coordinates'])
        tr[t]=dict(identifier=t,epm_node=str(p['NODO_TRANSFORM_CONN']),root=str(p['NODO2_ID']),
                   kva=float(p['CAPACIDAD_NOMINAL']),x=x,y=y,meta=raw_t.get(t))
    lv=[]
    for f0 in f:
        p=f0['properties']
        if p.get('layer')!='EPM LV':continue
        geom=transform(TO_M,shape(f0['geometry']))
        if geom.geom_type!='LineString':continue
        lv.append(dict(fid=str(p['G3E_FID']),node=str(p.get('NODO_TRANSFORM_CONN')),
             a=str(p.get('NODO1_ID')),b=str(p.get('NODO2_ID')),
             length=float(p.get('LONGITUD_CONN') or geom.length),geom=geom,
             material=str(p.get('MATERIAL','')),calibre=str(p.get('CALIBRE',''))))
    return houses,tr,lv

@dataclass
class Territory:
    trafo:dict
    graph:nx.Graph
    attachments:list
    label:str
    root:str
    line_count:int
    def metrics(self):
        t=self.trafo
        return dict(trafo=t['identifier'],epm_node=t['epm_node'],kva=t['kva'],
                    houses=len(self.attachments),gis_lines=self.line_count,
                    mapped_lv_m=round(sum(d['length_m'] for _,_,d in self.graph.edges(data=True) if d['kind']=='gis_lv'),2),
                    assumed_service_m=round(sum(a['service_length_m'] for a in self.attachments),2),
                    longest_service_m=round(max([a['service_length_m'] for a in self.attachments],default=0.),2),
                    graph_connected=nx.is_connected(self.graph),
                    tree=nx.is_tree(self.graph),assignment_policy=self.label)

def infer_assignments(houses,trafos,lv,policy='base'):
    if policy not in ('base','nearest_mapped'):raise ValueError('assignment must be base or nearest_mapped')
    valid={t['epm_node']:t['identifier'] for t in trafos.values() if t['identifier']!='92395'}
    lines=[s for s in lv if s['node'] in valid]
    outcomes=[]
    for hid,h in sorted(houses.items()):
        pt=Point(h['x'],h['y'])
        orig=h['transformer_number']
        if policy=='base':
            selected=[s for s in lines if valid[s['node']]==orig]
        else:selected=lines
        if selected:
            near=min(selected,key=lambda s:(pt.distance(s['geom']),s['fid']))
            target=valid[near['node']];dist=float(pt.distance(near['geom']))
            status='ASSUMED_NEAREST_EPM_SEGMENT'
        else:
            near=None;target=orig;dist=None;status='NO_MAPPED_LV_FOR_ASSIGNED_TRANSFORMER'
        outcomes.append(dict(house=hid,original=orig,transformer=target,
                             changed=(target!=orig),segment_id=near['fid'] if near else '',
                             gis_proximity_m=round(dist,2) if dist is not None else None,
                             status=status,source_status=h['assignment_status']))
    return outcomes

def build_territory(ident,houses,trafos,lv,assignments,service_factor=1.0):
    if service_factor<1:raise ValueError('service length factor must be >= 1')
    t=trafos[ident];ss=sorted([s for s in lv if s['node']==t['epm_node']],key=lambda z:z['fid'])
    target=[a for a in assignments if a['transformer']==ident]
    if not ss:return None
    g=nx.Graph();root='N'+t['root'];g.add_node(root,x=t['x'],y=t['y'],type='root')
    # Arrange multiple house taps along each EPM segment. Split EPM length proportionally
    # to the line geometry, so the original EPM segment total length is conserved.
    grouped=defaultdict(list)
    seen={s['fid']:s for s in ss}
    for ass in target:
        if ass['segment_id'] not in seen:raise ValueError(f"{ass['house']} cannot attach to {ident}")
        h=houses[ass['house']];s=seen[ass['segment_id']]
        pt=Point(h['x'],h['y']);projection=s['geom'].project(pt)
        tap=s['geom'].interpolate(projection)
        grouped[s['fid']].append((projection,ass,h,tap))
    attachments=[]
    for s in ss:
        a='N'+s['a'];b='N'+s['b'] if s['b'] not in ('0','None','') else 'END_'+s['fid']
        g.add_node(a,x=s['geom'].coords[0][0],y=s['geom'].coords[0][1],type='EPM_node')
        if b not in g:g.add_node(b,x=s['geom'].coords[-1][0],y=s['geom'].coords[-1][1],type='EPM_node')
        taps=sorted(grouped[s['fid']],key=lambda row:(row[0],row[1]['house']))
        last=a;pos=0.
        chain=[]
        for i,(proj,ass,h,tap) in enumerate(taps):
            key='T_'+s['fid']+'_'+str(i)
            g.add_node(key,x=tap.x,y=tap.y,type='assumed_tap');chain.append((key,proj))
            service_m=max(.25,Point(h['x'],h['y']).distance(tap)*service_factor)
            hd='HOUSE_'+ass['house'];g.add_node(hd,x=h['x'],y=h['y'],type='house',house=ass['house'])
            g.add_edge(key,hd,length_m=service_m,kind='assumed_service',source_fid=s['fid'],
                       material='ASSUMED_AAC',calibre='4',r_loop=.0)
            attachments.append(dict(house=ass['house'],trafo=ident,segment=s['fid'],
                service_euclidean_m=round(Point(h['x'],h['y']).distance(tap),3),
                service_length_m=round(service_m,3),assumed=True,
                changed=ass['changed'],source_status=ass['source_status']))
        # avoid zero-length numerical branches for taps at exact same coordinate
        sequence=[(a,0.)]+chain+[(b,s['geom'].length)]
        chunks=[max(0.,sequence[i+1][1]-sequence[i][1]) for i in range(len(sequence)-1)]
        denom=sum(chunks)
        if denom<=0:raise ValueError('zero-length EPM segment '+s['fid'])
        for i,(u,_) in enumerate(sequence[:-1]):
            v=sequence[i+1][0]
            length=max(0.001,s['length']*chunks[i]/denom)
            g.add_edge(u,v,length_m=length,kind='gis_lv',source_fid=s['fid'],
                    material=s['material'],calibre=s['calibre'])
    if not nx.is_connected(g):
        # Root is an EPM LV endpoint ID. Do not silently bridge disconnected data.
        disconnected=[list(component)[:3] for component in nx.connected_components(g)]
        raise ValueError(f'{ident}: EPM GIS node graph disconnected from LV root {root}: {disconnected}')
    if not nx.is_tree(g):raise ValueError(f'{ident}: GIS LV topology not radial')
    return Territory(t,g,attachments,policy_label(assignments),root,len(ss))

def policy_label(assignments):
    return 'includes_nearest_mapped' if any(x['changed'] for x in assignments) else 'provisional_base'

def conductor_params(material,calibre):
    r,x,amp=CONDUCTOR.get((material,calibre),FALLBACK)
    return 2*r,x,amp/1000.,(material,calibre) in CONDUCTOR

def farthest_house(territory):
    lengths=nx.single_source_dijkstra_path_length(territory.graph,territory.root,weight='length_m')
    return max((k for k in lengths if k.startswith('HOUSE_')),key=lambda k:lengths[k])

def middle_on_path(graph,root,end):
    """Find exact halfway distance along weighted path from root to farthest house."""
    path=nx.shortest_path(graph,root,end,weight='length_m')
    length=sum(graph[a][b]['length_m'] for a,b in zip(path,path[1:]))
    target=length/2.;sofar=0.
    for a,b in zip(path,path[1:]):
        width=graph[a][b]['length_m']
        if sofar+width>=target-1e-7:return a,b,max(0.,min(1.,(target-sofar)/width))
        sofar+=width
    raise ValueError('missing midpoint')

def split_for_middle(g,root,end):
    a,b,frac=middle_on_path(g,root,end)
    if frac<1e-7:return a
    if frac>1-1e-7:return b
    d=dict(g[a][b]);g.remove_edge(a,b)
    key='PV_BESS_MIDPOINT';x=g.nodes[a]['x']*(1-frac)+g.nodes[b]['x']*frac
    y=g.nodes[a]['y']*(1-frac)+g.nodes[b]['y']*frac
    g.add_node(key,x=x,y=y,type='inverter_middle')
    g.add_edge(a,key,**{**d,'length_m':d['length_m']*frac})
    g.add_edge(key,b,**{**d,'length_m':d['length_m']*(1-frac)})
    return key
