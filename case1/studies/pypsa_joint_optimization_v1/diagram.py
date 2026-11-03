"""Diagram of mathematical topology, NOT an as-built EPM feeder single-line."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

def fig():
    f,ax=plt.subplots(figsize=(12,5.4))
    ax.set_xlim(0,12);ax.set_ylim(0,5.4);ax.axis('off')
    def node(x,y,w,h,txt,fc='#eff5fa'):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.06',facecolor=fc,edgecolor='#284565',linewidth=1.3))
        ax.text(x+w/2,y+h/2,txt,ha='center',va='center',fontsize=10,fontweight='medium')
    def arrow(x1,y1,x2,y2,color='#2f546e',both=False,label=None,dy=0):
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='<->' if both else '->',
           mutation_scale=15,color=color,lw=1.5))
        if label:ax.text((x1+x2)/2,(y1+y2)/2+dy,label,fontsize=8,ha='center',va='bottom')
    node(.3,3.0,1.55,.85,'PV panels\n(integer count)','#fff5de')
    node(2.35,3.0,1.65,.85,'Common\nsolar DC bus')
    node(4.9,3.0,1.4,.85,'DC → AC\ninverter')
    node(7.05,3.0,1.45,.85,'AC bus\nwith loads')
    node(9.30,3.0,2.15,.85,'Existing transformer\nPCC 5 / assumed kVA','#eaf4ea')
    node(2.35,.72,1.65,.85,'BESS charge /\ndischarge Links','#f1edff')
    node(4.65,.72,1.65,.85,'Battery DC bus\n& cyclic Store','#f1edff')
    arrow(1.88,3.42,2.32,3.42)
    arrow(4.04,3.42,4.87,3.42)
    arrow(6.33,3.42,7.02,3.42)
    arrow(8.54,3.42,9.26,3.42,both=True,label='PCC P/Q/S',dy=.22)
    arrow(3.14,2.96,3.14,1.62,both=True)
    arrow(4.02,1.12,4.62,1.12,both=True)
    ax.text(3.45,2.13,'PV DC-side storage, no grid charging',fontsize=9,ha='left')
    ax.text(6.9,1.25,'Constraints: annual balance, DC losses, hourly grid limits\nObjectives solved separately: minimum cost / maximum self-sufficiency / hosting count',fontsize=9,ha='left')
    ax.text(6,.35,'Conceptual PyPSA optimization topology. Does not establish real LV cable routes, neutral currents or AC-feeder feasibility.',ha='center',fontsize=9,color='#555')
    ax.set_title('San Rafael: joint PV+BESS investment and 8,760-hour operation',fontsize=14,pad=12)
    out=Path(__file__).resolve().parent/'figures'
    out.mkdir(exist_ok=True)
    for ext in ['svg','png']:f.savefig(out/f'00_joint_optimization_topology.{ext}',dpi=180,bbox_inches='tight')
    plt.close(f)
if __name__=='__main__':fig()
