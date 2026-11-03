"""Deterministic geographic *candidate* LV topologies; no verified cables or customers.

All distances use a local WGS84 tangent-plane approximation (metres). The model
never labels these links as surveyed or as-built routes.
"""
from __future__ import annotations
import csv, math
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
EARTH = 6378137.0
# Original case study and nominal equipment; see README for assumptions.
TRAFO_ORDER = ['94022', '106039', '92395', '85398', '113699', '98380', 'NORTH_25KVA']
ALTERNATIVES = {
    'north': {'H01': 'NORTH_25KVA', 'H02': 'NORTH_25KVA'},
    'h10': {'H10': '106039'},
    'h29': {'H29': '92395'},
}


def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def read_evidence(houses_path=HERE/'houses_candidate_associations.csv', trafos_path=HERE/'transformers_evidence.csv'):
    hs=read_csv(houses_path); ts=read_csv(trafos_path)
    if len(hs)!=35 or len(set(h['house_id'] for h in hs))!=35:
        raise ValueError('Expected 35 unique houses')
    if len(ts)!=7 or len(set(t['transformer_number'] for t in ts))!=7:
        raise ValueError('Expected 7 distinct transformer records')
    t={d['transformer_number']:{**d, 'lat':float(d['latitude']), 'lon':float(d['longitude']), 'kva':float(d['kva'])} for d in ts}
    h={d['house_id']:{**d,'lat':float(d['latitude']),'lon':float(d['longitude']), 'trafo':d['transformer_number']} for d in hs}
    for name,d in h.items():
        if d['trafo'] not in t: raise ValueError(f'{name}: unknown transformer')
    return h,t


def choose_assignments(houses, selection='base'):
    updates={}
    if selection!='base':
        keys=['north','h10','h29'] if selection=='all_alternates' else [selection]
        for key in keys:
            if key not in ALTERNATIVES: raise ValueError('Unknown alternative: '+key)
            updates.update(ALTERNATIVES[key])
    out={h:dict(d) for h,d in houses.items()}
    for h,trafo in updates.items():out[h]['trafo']=trafo
    return out


def enu_m(lat,lon,lat0,lon0):
    return (EARTH*math.radians(lon-lon0)*math.cos(math.radians((lat+lat0)/2)),
            EARTH*math.radians(lat-lat0))


def hav_approx_m(a,b):
    x,y=enu_m(a['lat'],a['lon'],b['lat'],b['lon'])
    return math.hypot(x,y)


@dataclass
class Territory:
    transformer:dict
    houses:dict
    parent:dict
    lengths_m:dict
    root_dist_m:dict
    routing:str
    route_factor:float

    @property
    def name(self):return self.transformer['transformer_number']
    @property
    def total_m(self):return sum(self.lengths_m.values())
    @property
    def farthest(self):return max(self.houses,key=lambda k:self.root_dist_m[k]) if self.houses else None
    @property
    def max_m(self):return max(self.root_dist_m.values(),default=0.)

    def siting_house(self,where):
        if not self.houses:return None
        if where=='head':return None
        if where=='end':return self.farthest
        if where!='middle':raise ValueError('Unknown siting '+str(where))
        path=[];h=self.farthest
        while h!='TRAFO':
            path.append(h);h=self.parent[h]
        return min(path,key=lambda k:abs(self.root_dist_m[k]-self.max_m/2))


def territory(trafo, house_data, routing='mst', route_factor=1.3):
    if routing not in ('mst','star'):raise ValueError('Routing must be mst or star')
    if route_factor < 1:raise ValueError('Route detour factor cannot be less than 1')
    # A Prim tree yields one connected, radial candidate LV system; it is not
    # a representation of poles, roads, actual service drops or cable routes.
    done={'TRAFO'}; parent={}; lengths={}
    nodes={'TRAFO':trafo,**house_data}
    remaining=set(house_data)
    while remaining:
        candidates=done if routing=='mst' else {'TRAFO'}
        candidate=min(((hav_approx_m(nodes[par],nodes[h]),h,par)
                       for h in remaining for par in candidates), key=lambda x:(x[0],x[1],x[2]))
        d,h,par=candidate
        parent[h]=par;lengths[h]=d*route_factor
        remaining.remove(h);done.add(h)
    dist={}
    for h in parent:
        def walk(k):
            if k=='TRAFO':return 0.
            if k not in dist:dist[k]=lengths[k]+walk(parent[k])
            return dist[k]
        walk(h)
    return Territory(trafo,house_data,parent,lengths,dist,routing,route_factor)


def build_territories(assignment='base',routing='mst',route_factor=1.3):
    houses,trafos=read_evidence()
    houses=choose_assignments(houses,assignment)
    return [territory(trafos[tid],{h:d for h,d in houses.items() if d['trafo']==tid},routing,route_factor)
            for tid in TRAFO_ORDER]


def evidence_rows(territories,assignment):
    return [dict(assignment=assignment,transformer=t.name,epm_node=t.transformer['epm_node'],
                 kva=t.transformer['kva'],houses=len(t.houses),
                 house_ids=';'.join(sorted(t.houses)),route=t.routing,detour=t.route_factor,
                 total_candidate_lv_m=round(t.total_m,1),longest_candidate_path_m=round(t.max_m,1),
                 farthest_house=t.farthest or '',
                 connection_verification='CANDIDATE_ONLY_NOT_AS_BUILT') for t in territories]
