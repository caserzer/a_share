"""Reveal follow-up only after preserving prefix judgments; no success threshold."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/ep34-mpl-cache')
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from audit_local_inputs import EP,PRIOR,sha

out=EP/'outputs/r00_v2_cases/batch01'
if (out/'reveal_manifest.json').exists():raise FileExistsError('already revealed')
seal=json.loads((out/'prefix_review_seal.json').read_text())
for f,h in seal['files'].items():assert sha(Path(f))==h
font='/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc';font_manager.fontManager.addfont(font);plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name();plt.rcParams['axes.unicode_minus']=False
cases=pd.DataFrame(json.loads((out/'selected_cases.json').read_text()))
rawfile=PRIOR/'daily_industries.parquet';raw=pd.read_parquet(rawfile,columns=['date','day_i','era','industry_code','nav','block']);rows=[];paths=[]
for date,sample in cases.groupby('cutoff',sort=True):
 fig,axes=plt.subplots(3,2,figsize=(13,10))
 for ax,r in zip(axes.flat,sample.itertuples()):
  g=raw[raw.era.eq(r.era)&raw.industry_code.eq(r.industry_code)&raw.day_i.between(r.day_i-120,r.day_i+60)].set_index('day_i').reindex(range(r.day_i-120,r.day_i+61))
  g['relative_day']=g.index-r.day_i;g['case_id']=r.case_id;paths.append(g.reset_index())
  before=g[g.relative_day<=0];known=before.nav.notna()&before.nav.gt(0)&before.block.notna();base=before.loc[known,'nav'].iloc[-1] if known.any() else np.nan
  if np.isfinite(base):
   for _,part in g[g.nav.notna()&g.nav.gt(0)&g.block.notna()].groupby('block'):
    part=part.reindex(range(int(part.index.min()),int(part.index.max())+1));t=part.index-r.day_i
    ax.plot(t,part.nav/base*100,color='#aab5bd',linewidth=1)
    y=part.nav/base*100;ax.plot(t,y.where(t<=0),color='#23649b',linewidth=1.5);ax.plot(t,y.where(t>=0),color='#d77a19',linewidth=1.5)
   ax.set_ylabel('观察时最近可用价格=100')
  else:
   ax.text(.5,.5,'观察时价格不足\n不补零，不判断改善',ha='center',va='center',transform=ax.transAxes);ax.set_yticks([])
  ax.axvline(0,color='#777',linestyle='--');ax.set_xlim(-120,60);ax.set_title(f'{r.case_id} {r.industry_name}\n观察日 {date}');ax.grid(alpha=.2);ax.set_xlabel('距观察日的交易日')
  post=g[g.relative_day>=0];valid=post.nav.notna().all() and post.nav.gt(0).all() and post.block.notna().all() and post.block.nunique()==1
  v=post.nav.to_numpy();rows.append(dict(case_id=r.case_id,path_known=bool(valid),known_followup_rows=int(post.nav.notna().sum()),terminal_change=float(v[-1]/v[0]-1) if valid else None,peak_change=float(v.max()/v[0]-1) if valid else None,max_drawdown=float((v/np.maximum.accumulate(v)-1).min()) if valid else None))
 fig.suptitle('蓝：观察日前；橙：锁定初判后揭示的后续路径',fontsize=16);fig.tight_layout(rect=(0,0,1,.96));fig.savefig(out/f'revealed_{date}.png',dpi=125);plt.close(fig)
pd.concat(paths,ignore_index=True).to_parquet(out/'revealed_paths.parquet',index=False)
(out/'followup_descriptions.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
(out/'reveal_manifest.json').write_text(json.dumps(dict(scope='Descriptive follow-up only; not new labels or performance',prefix_review_seal_sha256=sha(out/'prefix_review_seal.json'),inputs={str(f):sha(f) for f in [rawfile,Path(__file__)]},artifacts={f.name:sha(f) for f in out.glob('revealed*')}),indent=2)+'\n')
print(json.dumps(rows,ensure_ascii=False))
