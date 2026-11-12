import sys,json
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p34';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
base=Path('/home/xiaolv/.cache/a_share/ep32');current=base/'industry_v1/L3.parquet';legacy=base/'extension_v2/sources/legacy_catalog.parquet';source=EP/'restart/p30/training_panel.parquet';a=pd.concat([pd.read_parquet(current),pd.read_parquet(legacy)],ignore_index=True);a=a[a.level.eq('L3')][['src','index_code','parent_code']].drop_duplicates();a=a.rename(columns={'src':'era','index_code':'industry_code'});assert not a.duplicated(['era','industry_code']).any()
cols=['era','industry_code','date','eligible','rate5','rate20','rate60','history_proxy60'];p=pd.read_parquet(source,columns=cols);p=p[p.eligible].copy();p=p.merge(a,on=['era','industry_code'],how='left',validate='many_to_one');p['change']=p.rate5-p.rate20;p['uses_proxy']=p.history_proxy60.eq(1).astype(int)
for prefix,keys in [('peer',['era','parent_code','date']),('market',['era','date'])]:
 g=p.groupby(keys);n=g.rate20.transform('size')-1;p[prefix+'_count']=n
 for target,col in [('rate20','rate20'),('change','change'),('proxy_fraction','uses_proxy')]:
  p[prefix+'_'+target]=(g[col].transform('sum')-p[col])/n
 p.loc[n.lt(2),[prefix+'_rate20',prefix+'_change',prefix+'_proxy_fraction']]=np.nan
p['peer_supported']=p.peer_rate20.notna()&p.peer_change.notna();p['laggard_with_peer_positive']=p.peer_supported&p.rate20.le(0)&p.peer_rate20.gt(0)
p.to_parquet(OUT/'features.parquet',index=False)
p.groupby(p.date.dt.year).agg(price_rows=('date','size'),mapped=('parent_code','count'),peer_supported=('peer_supported','sum'),laggard_peer_positive=('laggard_with_peer_positive','sum')).to_csv(OUT/'coverage.csv')
p[p.peer_supported][['rate20','change','peer_rate20','peer_change','market_rate20','market_change']].corr().to_csv(OUT/'correlations.csv')
for _,r in p[p.peer_supported].sample(100,random_state=3334).iterrows():
 peers=p[p.era.eq(r.era)&p.date.eq(r.date)&p.parent_code.eq(r.parent_code)&p.industry_code.ne(r.industry_code)];assert len(peers)==r.peer_count and len(peers)>=2;assert np.isclose(peers.rate20.mean(),r.peer_rate20) and np.isclose(peers.change.mean(),r.peer_change)
 assert not peers.industry_code.eq(r.industry_code).any()
(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',inputs={str(f):sha(f) for f in [current,legacy,source,Path(__file__),EP/'restart/P34_sibling_feasibility_plan.md']},feature_sha256=sha(OUT/'features.parquet'),direct_leave_self_out_checks=100,no_future_label_columns_read=True,unmapped_codes=p.loc[p.parent_code.isna(),['era','industry_code']].drop_duplicates().to_dict('records')),indent=2)+'\n')
print(pd.read_csv(OUT/'coverage.csv').to_string(index=False));print(p.loc[p.peer_supported& p.date.ge('2023-01-01'),'peer_count'].describe().to_string())
