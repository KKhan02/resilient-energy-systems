from pathlib import Path
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent
FIG=OUT/'figures'
FIG.mkdir(parents=True,exist_ok=True)
def load(name):
    with open(OUT/name,newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
annual=load('annual_reference_summary.csv')
placement=load('placement_sensitivity_pf090_far_end_heavy.csv')
for a in annual:
    for key in ['min_voltage_pu','hours_voltage_below_097','annual_hours_voltage_below_095','modelled_annual_feeder_losses_kwh']:
        a[key]=float(a[key])
    a['households']=int(a['households'])
for a in placement:
    a['households']=int(a['households'])
    a['min_voltage_pu']=float(a['min_voltage_pu'])
annual_map={r['households']:r for r in annual}
head_stress={r['households']:r for r in placement if r['siting']=='lv_head'}
H=list(range(5,16))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.titlesize':13,'axes.labelsize':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','savefig.facecolor':'white'})
BLUE='#3165A4'; ORANGE='#D07843'; RED='#C3434A'; GREEN='#308D74'; PURPLE='#8155B0'; GRAY='#777777'; DARK='#27303d'

def base_ax(ax):
    ax.set_xticks(H)
    ax.set_xlim(4.55,15.45)
    ax.grid(axis='y',color='#dfe3e8',linewidth=.75)
    ax.set_axisbelow(True)

def save(fig,name):
    fig.tight_layout(pad=1.6)
    fig.savefig(FIG/(name+'.png'),dpi=260,bbox_inches='tight')
    fig.savefig(FIG/(name+'.svg'),bbox_inches='tight')
    plt.close(fig)

def voltage(ax, title=True):
    base_ax(ax)
    ax.scatter(H,[r['min_voltage_pu'] for r in annual],s=72,c=BLUE,edgecolors='white',linewidths=1.1,zorder=5)
    ax.axhline(.97,ls='--',lw=1.2,c=ORANGE,label='0.97 pu screening')
    ax.axhline(.95,ls=':',lw=1.2,c=RED,label='0.95 pu reference')
    ax.set_ylim(.925,1.005)
    ax.set_xlabel('Number of households')
    ax.set_ylabel('Minimum LV voltage (pu)')
    if title:ax.set_title('Annual worst-case voltage')
    ax.legend(loc='lower left',fontsize=9,frameon=False)

def hours(ax,title=True):
    base_ax(ax)
    ax.scatter(H,[r['hours_voltage_below_097'] for r in annual],c=ORANGE,s=70,edgecolors='white',linewidths=1,zorder=5,label='Hours below 0.97 pu')
    ax.scatter(H,[r['annual_hours_voltage_below_095'] for r in annual],c=RED,s=35,marker='D',edgecolors='white',linewidths=1,zorder=6,label='Hours below 0.95 pu')
    ax.set_ylim(-25,725)
    ax.set_xlabel('Number of households')
    ax.set_ylabel('Annual violation hours')
    if title:ax.set_title('Annual low-voltage exposure')
    ax.legend(loc='upper left',frameon=False,fontsize=9)

def placement_fig(ax,title=True):
    base_ax(ax)
    styles=[('lv_head',BLUE,'o','LV head',-.18),('middle',GREEN,'s','Middle',0),('far_end',PURPLE,'^','Far end',.18)]
    for sit,col,marker,label,x_shift in styles:
        data=[r for r in placement if r['siting']==sit]
        ax.scatter([r['households']+x_shift for r in data],[r['min_voltage_pu'] for r in data],c=col,s=48,marker=marker,edgecolors='white',linewidth=.7,label=label,zorder=5)
    ax.axhline(.97,c=ORANGE,ls='--',lw=1.2)
    ax.axhline(.95,c=RED,ls=':',lw=1.2)
    ax.set_ylim(.920,1.0)
    ax.set_xlabel('Number of households')
    ax.set_ylabel('Critical-hour minimum voltage (pu)')
    if title:ax.set_title('Inverter location, PF 0.90, remote-heavy loads')
    ax.legend(loc='lower left',fontsize=9,ncol=3,frameon=False)

def trafo(ax,title=True):
    base_ax(ax)
    ax.scatter([h-.10 for h in H],[float(annual_map[h]['max_transformer_loading_pct']) for h in H],s=69,c=BLUE,marker='o',edgecolors='white',linewidth=1,label='Annual, PF 0.98, equal loads',zorder=5)
    ax.scatter([h+.10 for h in H],[float(head_stress[h]['peak_transformer_pct']) for h in H],s=69,c=RED,marker='D',edgecolors='white',linewidth=1,label='Critical, PF 0.90, remote-heavy',zorder=5)
    ax.axhline(100,c=ORANGE,ls='--',lw=1.2,label='Nominal transformer limit')
    ax.set_ylim(35,125)
    ax.set_xlabel('Number of households')
    ax.set_ylabel('Peak transformer loading (%)')
    if title:ax.set_title('Transformer loading sensitivity')
    ax.legend(loc='upper left',fontsize=8.6,frameon=False)

for name,f in [('01_annual_minimum_voltage',voltage),('02_annual_violation_hours',hours),('03_pv_bess_connection_position',placement_fig),('04_transformer_loading',trafo)]:
    fig,ax=plt.subplots(figsize=(9.5,5.4))
    f(ax); save(fig,name)
fig,axs=plt.subplots(2,2,figsize=(15.5,10.3))
for ax,f in zip(axs.ravel(),[voltage,hours,placement_fig,trafo]):f(ax)
fig.suptitle('Electrical feasibility of optimized PV–BESS communities',fontsize=18,fontweight='bold',y=1.015)
save(fig,'00_poster_composite_5_to_15')

fig,ax=plt.subplots(figsize=(9.5,5.4))
base_ax(ax)
ax.scatter(H,[r['modelled_annual_feeder_losses_kwh'] for r in annual],c=GREEN,s=75,edgecolors='white',linewidth=1)
ax.set_title('Annual feeder losses from AC power flow')
ax.set_xlabel('Number of households');ax.set_ylabel('Real-power network losses (kWh/year)')
save(fig,'05_annual_feeder_losses')

