"""Prepare model-independent case prefixes; never read old signals/outcomes."""
import os
os.environ.setdefault("MPLCONFIGDIR","/tmp/ep34-mpl-cache")
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from audit_local_inputs import EP,PRIOR,sha

out=EP/'outputs/r00_v2_cases/batch01';out.mkdir(parents=True,exist_ok=True)
if (out/'prefix_manifest.json').exists():raise FileExistsError('prefix packet already exists')
from matplotlib import font_manager
font_path='/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'
font_manager.fontManager.addfont(font_path)
plt.rcParams['font.family']=font_manager.FontProperties(fname=font_path).get_name();plt.rcParams['axes.unicode_minus']=False
catfile=EP/'outputs/r01/weekly_catalog.parquet';cat=pd.read_parquet(catfile,columns=['date','era','industry_code','industry_name'])
rawfile=PRIOR/'daily_industries.parquet';raw=pd.read_parquet(rawfile,columns=['date','day_i','era','industry_code','nav','block','stale_members','boundary_proxy'])
rfile=PRIOR/'receipt.json';calendarfile=Path(next(x for x in json.loads(rfile.read_text())['inputs'] if x.endswith('/calendar.parquet')));cal=pd.DatetimeIndex(pd.read_parquet(calendarfile).date).sort_values()
selected=[];allprefix=[];stats=[]
for date in ['2019-06-28','2023-06-30']:
 c=cat[cat.date.eq(date)].sort_values('industry_code');positions=np.floor(np.linspace(0,len(c)-1,6)).astype(int)
 sample=c.iloc[positions];fig,axes=plt.subplots(3,2,figsize=(13,10));end=cal.get_loc(pd.Timestamp(date))
 for ax,row in zip(axes.flat,sample.itertuples()):
  cid=f'B01-{len(selected)+1:02d}';identity=dict(case_id=cid,era=row.era,industry_code=row.industry_code,industry_name=row.industry_name,cutoff=date,day_i=int(end),catalog_position=int(positions[len(selected)%6]))
  selected.append(identity);g=raw[raw.era.eq(row.era)&raw.industry_code.eq(row.industry_code)&raw.day_i.between(end-120,end)].set_index('day_i').reindex(range(end-120,end+1))
  known=g.nav.notna()&g.nav.gt(0)&g.block.notna();last=g.loc[known,'nav'].iloc[-1] if known.any() else np.nan
  for _,part in g[known].groupby('block'):
   # Reindex within each block so missing observations break lines.
   part=part.reindex(range(int(part.index.min()),int(part.index.max())+1));ax.plot(part.index-end,part.nav/last*100,color='#23649b',linewidth=1.5)
  ax.axvline(0,color='#777',linestyle='--');ax.set_title(f'{cid} {row.industry_name} {row.industry_code}\n{date}｜有效价格 {int(known.sum())}/121')
  ax.set_xlabel('距观察日的交易日');ax.set_ylabel('最近可用价格=100');ax.grid(alpha=.2)
  item=dict(**identity,known_rows=int(known.sum()),current_known=bool(known.iloc[-1]),blocks=int(g.block.nunique()),proxy_rows=int((g.stale_members.gt(0)|g.boundary_proxy.eq(True)).sum()))
  for h in [5,20,60,120]:
   v=g.iloc[-h-1:];valid=v.nav.notna().all() and v.nav.gt(0).all() and v.block.notna().all() and v.block.nunique()==1
   item[f'descriptive_return_{h}']=float(v.nav.iloc[-1]/v.nav.iloc[0]-1) if valid else None
  stats.append(item);z=g.copy();z['case_id']=cid;z['relative_day']=z.index-end;allprefix.append(z.reset_index())
 fig.suptitle('仅展示观察日及以前的价格；未展示后续结果',fontsize=16);fig.tight_layout(rect=(0,0,1,.96));fig.savefig(out/f'prefix_{date}.png',dpi=125);plt.close(fig)
pd.concat(allprefix,ignore_index=True).to_parquet(out/'prefix_paths.parquet',index=False)
(out/'selected_cases.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2)+'\n')
(out/'prefix_facts.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
manifest=dict(scope='Prefix-only semantic review, not performance evaluation',cases=len(selected),inputs={str(f):sha(f) for f in [catfile,rawfile,rfile,calendarfile,EP/'protocols/r00_v2/case_batch01_plan.md',Path(__file__)]},artifacts={f.name:sha(f) for f in out.iterdir() if f.is_file()})
(out/'prefix_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(stats,ensure_ascii=False))
