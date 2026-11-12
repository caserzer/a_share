from pathlib import Path
import pandas as pd
r=Path(__file__).resolve().parents[1];d=pd.read_parquet('/home/xiaolv/.cache/a_share/ep32/forecast_v5/daily_industries.parquet');d=d[d.level.eq('L3')].sort_values(['era','industry_code','block','date']);key=['era','industry_code','block'];chunks=[]
for _,g in d.groupby(key):
 g=g.copy();g['coverage_changed']=g.date.dt.to_period('M').eq(g.date.shift().dt.to_period('M'))&g.coverage.sub(g.coverage.shift()).abs().gt(1e-12)
 for w in [60,126]:g[f'touched{w}']=g.coverage_changed.rolling(w,min_periods=w).max()
 chunks.append(g[key+['date','touched60','touched126']])
a=pd.concat(chunks);q=pd.read_parquet(r/'p21/selected_features.parquet').merge(a,on=key+['date'],validate='one_to_one');rows=[]
for name,mask in [('all',pd.Series(True,index=q.index)),('top20_state',q.top20),('top20_edge',q.top20_edge),('nonup_edge',q.nonup_edge)]:
 z=q[mask]
 for w in [60,126]:rows.append(dict(scope=name,window=w,rows=len(z),known=int(z[f'touched{w}'].notna().sum()),with_coverage_change=int(z[f'touched{w}'].eq(1).sum()),fraction=float(z[f'touched{w}'].mean())))
pd.DataFrame(rows).to_csv(r/'p22/feature_exposure.csv',index=False)
