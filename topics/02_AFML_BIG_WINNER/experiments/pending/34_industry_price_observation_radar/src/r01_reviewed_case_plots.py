import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
p=Path('/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/34_industry_price_observation_radar/outputs/r01_cases')
c=json.loads((p/'casebook.json').read_text());paths=pd.read_parquet(p/'case_paths.parquet')
for era in ['SW2014','SW2021']:
 fig,axes=plt.subplots(3,2,figsize=(13,11),constrained_layout=True)
 for ax,r in zip(axes.flat,[x for x in c['cases'] if x['era']==era]):
  g=paths[paths.alert_id.eq(r['alert_id'])];ax.plot(g.relative_day,g.nav_return*100,color='#2563eb')
  ax.axvline(0,color='black');ax.axhline(0,color='gray',lw=.5)
  if r['origin_day'] is not None:ax.axvline(r['origin_day']-r['day'],color='#d97706',ls='--')
  ax.axvspan(0,60,color='#dbeafe',alpha=.25);ax.axhline(5,color='green',ls=':',lw=.7);ax.axhline(-5,color='red',ls=':',lw=.7)
  label=r['category']
  if label=='SHORT_REBOUND' and era=='SW2021':label='TERMINAL_THRESHOLD_FAILURE'
  ax.set_title(f"{label}\n{r['industry_code']} {r['date']}",fontsize=10);ax.set_xlim(-65,65);ax.set_xticks([-60,-40,-20,0,20,40,60]);ax.grid(alpha=.2)
  ax.set_xlabel('Trading sessions from alert');ax.set_ylabel('NAV return from alert (%)')
 fig.suptitle(f'{era}: reviewed cases; no change to registered labels');fig.savefig(p/f'{era}_reviewed.png',dpi=140);plt.close(fig)
