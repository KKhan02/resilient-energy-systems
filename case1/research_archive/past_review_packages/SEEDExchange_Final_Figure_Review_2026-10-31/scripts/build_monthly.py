#!/usr/bin/env python3
"""Create one clean, unconnected monthly summary from a shortened-hourly archive."""
import argparse,csv,io,zipfile
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--houses',type=int,default=12)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 prefix={7:'seven',9:'nine',12:'twelve'}[a.houses]
 with zipfile.ZipFile(a.archive) as z:
  name=next(k for k in z.namelist() if f'\\{prefix}_best_fixedPV_' in k and k.endswith('monthly_energy_balance.csv'))
  records=list(csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig'))))
 if len(records)!=12:raise ValueError(f'Expected 12 months, got {len(records)}')
 x=list(range(1,13)); ss=[float(r['self_sufficiency_pct']) for r in records]; imp=[float(r['grid_import_kwh']) for r in records]
 fig,ax=plt.subplots(figsize=(10.5,5.6),layout='constrained')
 dots=ax.scatter(x,ss,c=imp,cmap='viridis_r',s=105,edgecolor='#263541',linewidth=.4,zorder=3)
 ax.set_title(f'{a.houses} households | monthly operation in 2025',loc='left',pad=13)
 ax.set_xticks(x,[r['month'][-2:] for r in records])
 ax.set_xticklabels(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
 ax.set_xlim(.25,12.75);ax.set_ylim(0,101)
 ax.set_xlabel('Month');ax.set_ylabel('Monthly self-sufficiency (%)');ax.grid(alpha=.2)
 cb=fig.colorbar(dots,ax=ax,pad=.02,shrink=.92);cb.set_label('Monthly grid imports (kWh)')
 cb.ax.yaxis.set_major_formatter(FuncFormatter(lambda x,_:f'{x:,.0f}'))
 fn=f'{a.houses:02d}_homes_monthly_SS_colored_by_grid_import'
 for ext in ['png','svg']:fig.savefig(a.out/f'{fn}.{ext}',dpi=175)
 plt.close(fig)
 print('Generated:',fn)
if __name__=='__main__':main()
