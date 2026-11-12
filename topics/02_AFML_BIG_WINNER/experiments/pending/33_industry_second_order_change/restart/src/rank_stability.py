import json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
R=Path(__file__).resolve().parents[1]
O=R/'p55';O.mkdir(exist_ok=True)
assert not (O/'receipt.json').exists()
f=R/'p30/training_panel.parquet'
cols=['era','industry_code','level','date','day_i','block','eligible','rate5','history_proxy60']
p=pd.read_parquet(f,columns=cols)
assert not p.duplicated(['era','industry_code','date']).any()
rows=[];checks=0
for (era,level),g in p.groupby(['era','level']):
 dates=sorted(g.date.unique())
 for prev,cur in zip(dates,dates[1:]):
  a=g[g.date.eq(prev)];b=g[g.date.eq(cur)]
  assert a.day_i.nunique()==b.day_i.nunique()==1
  gap=int(b.day_i.iloc[0]-a.day_i.iloc[0])
  a=a[a.eligible & a.rate5.notna()];b=b[b.eligible & b.rate5.notna()]
  c=a.merge(b,on='industry_code',suffixes=('_a','_b'))
  c=c[c.block_a.eq(c.block_b)]
  assert c[['history_proxy60_a','history_proxy60_b']].isin([0,1]).all().all()
  reason='OK' if gap==5 and len(c)>=30 else ('NON_FIVE_SESSION_GAP' if gap!=5 else 'TOO_FEW_COMMON')
  rho=np.nan
  if reason=='OK':
   rho=c.rate5_a.corr(c.rate5_b,method='spearman')
   other=spearmanr(c.rate5_a,c.rate5_b).statistic
   assert np.isclose(rho,other,equal_nan=True)
   checks+=1
  rows.append(dict(era=era,level=level,date=cur,previous_date=prev,gap=gap,common=len(c),previous_eligible=len(a),current_eligible=len(b),common_fraction=len(c)/max(len(a),len(b)) if max(len(a),len(b)) else np.nan,proxy_fraction=(c.history_proxy60_a.eq(1)|c.history_proxy60_b.eq(1)).mean(),status=reason,rho=rho))
d=pd.DataFrame(rows);d.to_csv(O/'daily.csv',index=False)
v=d[d.status.eq('OK')].copy();v['year']=v.date.dt.year;v['quarter']=v.date.dt.to_period('Q').astype(str)
for period in ['year','quarter']:
 v.groupby(['era','level',period]).agg(dates=('rho','count'),mean_rho=('rho','mean'),median_rho=('rho','median'),negative_fraction=('rho',lambda x:(x<0).mean()),mean_common=('common','mean'),min_common_fraction=('common_fraction','min'),mean_proxy_fraction=('proxy_fraction','mean')).to_csv(O/f'{period}.csv')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
(O/'receipt.json').write_text(json.dumps(dict(status='PASS',future_labels_read=False,columns_read=cols,correlation_checks=checks,status_counts=d.status.value_counts().to_dict(),inputs={str(x):sha(x) for x in [f,Path(__file__),R/'P55_rank_stability_plan.md']},outputs={x.name:sha(x) for x in O.glob('*.csv')}),indent=2)+'\n')
print(pd.read_csv(O/'year.csv').to_string(index=False));print(d.status.value_counts().to_string())
