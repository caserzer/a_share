import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r82';out.mkdir(exist_ok=True);ap=ROOT/'outputs/r77/stock_interval_audit.parquet';ip=ROOT/'outputs/r77/intervals.json';rp=ROOT/'outputs/r77/receipt.json'
 d=pd.read_parquet(ap);ivs=json.loads(ip.read_text());iv={(x['method'],pd.Timestamp(x['origin'])):x for x in ivs};rec=json.loads(rp.read_text());paths={Path(p).stem:Path(p) for p in rec['price_partitions']};d['endpoint_valued']=d.price_valid&d.chain_stable;reads={}
 for sid,g in d[~d.endpoint_valued].groupby('security_id'):
  p=paths[sid];assert sha(p)==rec['price_partitions'][str(p)];reads[str(p)]=sha(p);f=pd.read_parquet(p).set_index('date')
  for ix,x in g.iterrows():
   v=iv[x['method'],x['origin']];ends=f.reindex(pd.to_datetime([v['entry'],v['exit']]))
   good=bool(ends.qfq_close.gt(0).all() and ends.close_conflict.eq(False).all() and ends.factor_chain_id.notna().all() and ends.factor_chain_id.nunique()==1)
   d.loc[ix,'endpoint_valued']=good
   if good:assert np.isclose(x.entry_price,float(ends.qfq_close.iloc[0])) and np.isclose(x.exit_price,float(ends.qfq_close.iloc[1]))
 rows=[]
 for (method,origin),g in d.groupby(['method','origin']):
  v=iv[method,origin];ready=bool(v['unknown_weight']<1e-12 and g.endpoint_valued.all() and np.isclose(g.weight.sum(),1));ret=float((g.weight*g.exit_price/g.entry_price).sum()-1) if ready else None
  rows.append(dict(method=method,origin=origin,unknown_weight=v['unknown_weight'],endpoint_valued=ready,full_path_valued=v['full_path_valued'],unvalued_stock_count=int((~g.endpoint_valued).sum()),unvalued_known_weight=float(g.loc[~g.endpoint_valued,'weight'].sum()),fixed_stock_gross=ret,r17_gross=v['r17_gross'],difference=ret-v['r17_gross'] if ready and v['r17_gross'] is not None else None))
 d.to_parquet(out/'stock_audit.parquet',index=False);js(out/'intervals.json',rows);summary=[]
 for method in sorted(d.method.unique()):
  rr=[x for x in rows if x['method']==method];good=[x for x in rr if x['endpoint_valued']];delta=[x['difference'] for x in good if x['difference'] is not None]
  summary.append(dict(method=method,planned=len(rr),endpoint_valued=len(good),full_path_valued=sum(x['full_path_valued'] for x in rr),whole_monthly_path=len(good)==len(rr),mean_difference=float(np.mean(delta)) if delta else None,min_difference=min(delta) if delta else None,max_difference=max(delta) if delta else None))
 js(out/'summary.json',summary)
 for p in [ap,ip,rp,ROOT/'protocols/r82.json',Path(__file__)]:reads[str(p)]=sha(p)
 js(out/'receipt.json',dict(reads=reads,inherits_R77_full_path_pass=True,no_net_curve=True));print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':run()
