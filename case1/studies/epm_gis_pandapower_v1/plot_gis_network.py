"""Simple static GIS network map: EPM LV backbone, assumed service lines and houses."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from epm_topology import read_data,infer_assignments,build_territory

DIR=Path(__file__).resolve().parent
colors={'94022':'#287fba','106039':'#df842b','113699':'#bc3d74','85398':'#29915c','98380':'#d5a62a'}
houses,trafos,lv=read_data();ass=infer_assignments(houses,trafos,lv)
fig,ax=plt.subplots(figsize=(11.2,7.4))
for tid,col in colors.items():
    t=build_territory(tid,houses,trafos,lv,ass)
    for a,b,d in t.graph.edges(data=True):
        na=t.graph.nodes[a];nb=t.graph.nodes[b]
        ax.plot([na['x'],nb['x']],[na['y'],nb['y']],color=col,
                linestyle=':' if d['kind']=='assumed_service' else '-',
                linewidth=.8 if d['kind']=='assumed_service' else 2.5,
                alpha=.5 if d['kind']=='assumed_service' else .95)
    ax.scatter([trafos[tid]['x']],[trafos[tid]['y']],marker='*',s=170,color=col,edgecolor='black',linewidth=.7,zorder=6)
    for a in t.attachments:
        h=houses[a['house']];ax.scatter(h['x'],h['y'],s=40,color=col,edgecolor='white',lw=.6,zorder=5)
        ax.annotate(a['house'][1:],(h['x'],h['y']),xytext=(3,3),textcoords='offset points',fontsize=7)
# No fake 92395 lines: mark its physical location, houses not connected to mapped line.
t=trafos['92395'];ax.scatter([t['x']],[t['y']],marker='*',s=160,color='#8b5fc9',edgecolor='black',zorder=6)
for a in [x for x in ass if x['transformer']=='92395']:
    h=houses[a['house']];ax.scatter(h['x'],h['y'],s=50,color='#8b5fc9',edgecolor='white',linewidth=.5)
    ax.annotate(a['house'][1:],(h['x'],h['y']),xytext=(3,3),textcoords='offset points',fontsize=7)
handles=[Line2D([0],[0],color=c,lw=3,label=f'{tid}, {trafos[tid]["kva"]:g} kVA') for tid,c in colors.items()]
handles += [Line2D([0],[0],color='#8b5fc9',lw=3,label='92395, LV missing'),
            Line2D([0],[0],color='#555',linestyle='-',lw=2,label='Mapped EPM LV'),
            Line2D([0],[0],color='#555',linestyle=':',lw=1.4,label='Assumed service'),
            Line2D([0],[0],marker='*',linestyle='None',color='black',markersize=10,label='Transformer')]
ax.legend(handles=handles,loc='upper left',bbox_to_anchor=(1,1),fontsize=8.5,frameon=False)
ax.set_aspect('equal');ax.set_xticks([]);ax.set_yticks([])
for side in ax.spines.values():side.set_visible(False)
fig.tight_layout();d=DIR/'output_preview';d.mkdir(parents=True,exist_ok=True)
fig.savefig(d/'epm_lv_house_connections.png',dpi=220,bbox_inches='tight')
fig.savefig(d/'epm_lv_house_connections.svg',bbox_inches='tight')
print('Map exported')
