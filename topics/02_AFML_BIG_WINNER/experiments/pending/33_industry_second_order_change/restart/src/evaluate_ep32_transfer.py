import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,KEY,sha,calendar_dates
from probability_pool import block_interval
OUT=EP/'restart/p02'
a=json.loads((OUT/'transfer_audit.json').read_text())
assert all(sha(p)==s for p,s in a['source_hashes'].items())
assert sha(OUT/'common_features.parquet')==a['common_features_sha256']
p=pd.read_parquet(OUT/'common_features.parquet').sort_values(KEY+['date']).reset_index(drop=True)
cal=pd.DatetimeIndex(pd.read_parquet('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet').index)
dates=calendar_dates();dates=dates[(dates>=p.date.min())&(dates<=p.date.max())]
rank=p.sort_values(['date','rel63','industry_code'],ascending=[True,False,True]);top=rank.groupby('date').cumcount().lt(np.ceil(rank.groupby('date').date.transform('size')*.2))
p['all']=True;p['momentum20']=False;p.loc[rank.index,'momentum20']=top
p['early']=p.state_eligible.eq(1);p['early_market']=p.early&p.market_up
p['dual_no_market']=p.early&p.risk_score.ge(.11)&p.diffusion_tree.ge(.11)
p['dual_market']=p.dual_no_market&p.market_up
methods=['all','momentum20','early','early_market','dual_no_market','dual_market']
for method in methods:
 p['entry_'+method]=False
 for _,g in p[p[method]].groupby(KEY):
  release=pd.Timestamp.min
  for i,r in g.sort_values('date').iterrows():
   if r.date<release:continue
   p.loc[i,'entry_'+method]=True
   end=cal.searchsorted(r.date,side='right')+126
   release=cal[end] if end<len(cal) else pd.Timestamp.max
p.to_parquet(OUT/'selected_features.parquet',index=False)
(OUT/'selection_seal.json').write_text(json.dumps({'features_sha256':sha(OUT/'selected_features.parquet'),'plan_sha256':sha(EP/'restart/P02_transfer_plan.md'),'source_sha256':sha(Path(__file__))},indent=2)+'\n')
l=pd.read_parquet(EP/'outputs/r09/evaluation_panel.parquet')
p=p.merge(l[ID+[f'{x}{h}' for h in [63,126,252] for x in ['win','status']]],on=ID,validate='one_to_one')
rows=[];annual=[]
for method in methods:
 z=p[p['entry_'+method]];counts=z.groupby('date').size()
 ranked=p.sort_values(['date','rel63','industry_code'],ascending=[True,False,True]);mom=ranked[ranked.groupby('date').cumcount().lt(ranked.date.map(counts).fillna(0))]
 for h in [63,126,252]:
  col=f'win{h}';base=p.groupby('date')[col].mean();mref=mom.groupby('date')[col].mean();k=z[z[col].notna()].copy();k['delta']=k[col]-k.date.map(base)
  lo,hi=block_interval(k,dates,26 if h==126 else round(h/5))
  rows.append(dict(method=method,horizon=h,entries=len(z),known=len(k),unknown=len(z)-len(k),win_rate=k[col].mean(),uplift=k.delta.mean(),lo=lo,hi=hi,momentum_delta=(k[col]-k.date.map(mref)).mean(),state_success_week_coverage=p.loc[p[method],col].sum()/p[col].sum(),median_prior63_return=np.expm1(z.abs63).median()))
  for year,g in k.groupby(k.date.dt.year):annual.append(dict(method=method,horizon=h,year=int(year),known=len(g),win_rate=g[col].mean(),uplift=g.delta.mean()))
p.to_parquet(OUT/'evaluated_panel.parquet',index=False)
pd.DataFrame(rows).to_csv(OUT/'summary.csv',index=False);pd.DataFrame(annual).to_csv(OUT/'annual.csv',index=False)
print(pd.DataFrame(rows).query('horizon==126').to_string(index=False))
