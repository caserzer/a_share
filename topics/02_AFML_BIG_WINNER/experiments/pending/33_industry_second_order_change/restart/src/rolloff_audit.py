import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p41';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
nf=EP/'restart/p29/daily_industries.parquet';pf=EP/'restart/p30/training_panel.parquet';mf=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet');d=pd.read_parquet(nf,columns=['era','industry_code','date','day_i','block','nav']);m=pd.read_parquet(mf).close.sort_index();ids=['era','industry_code','date'];parts=[];groups={}
for key,g in d[d.nav.notna()].groupby(['era','industry_code','block']):
 g=g.sort_values('date').copy();x=np.log(g.nav/g.date.map(m));g['incoming']=x-x.shift(5);g['outgoing']=x.shift(20)-x.shift(25);r=(x-x.shift(20))/4;g['rate_change']=r-r.shift(5);g['recomputed_rate20']=r
 valid=g.day_i.diff(25).eq(25);g.loc[~valid,['incoming','outgoing','rate_change','recomputed_rate20']]=np.nan
 parts.append(g[ids+['incoming','outgoing','rate_change','recomputed_rate20']]);groups[key]=g
p=pd.read_parquet(pf,columns=ids+['block','eligible','rate5','rate20','history_proxy60']);p=p[p.eligible];q=p.merge(pd.concat(parts,ignore_index=True),on=ids,validate='one_to_one')
assert q.rate_change.notna().all();assert np.allclose(q.rate_change,(q.incoming-q.outgoing)/4,atol=1e-12);assert np.allclose(q.rate5,q.incoming,atol=1e-12) and np.allclose(q.rate20,q.recomputed_rate20,atol=1e-12)
q['improving']=q.rate_change.gt(0);q['slowdown']=q.improving&q.rate20.lt(0);q['kind']=np.select([~q.improving,q.incoming.le(0),q.outgoing.lt(0)],['NOT_IMPROVING','STILL_NONPOSITIVE','BOTH_NEW_GAIN_AND_OLD_LOSS_EXIT'],default='NEW_GAIN_EXCEEDS_OLD_GAIN');q['quality']=np.where(q.history_proxy60.eq(0),'NO_HISTORY_PROXY','HISTORY_PROXY')
q.to_parquet(OUT/'features.parquet',index=False);rows=[]
for period,z in [('ALL',q),('2023+',q[q.date.ge('2023-01-01')])]+[(str(y),b) for y,b in q.groupby(q.date.dt.year)]:
 for scope,mask in [('improving','improving'),('slowdown','slowdown')]:
  a=z[z[mask]]
  for kind,b in a.groupby('kind'):rows.append(dict(period=period,scope=scope,kind=kind,rows=len(b),fraction=len(b)/len(a),dates=b.date.nunique(),proxy_rows=int(b.history_proxy60.eq(1).sum())))
pd.DataFrame(rows).to_csv(OUT/'composition.csv',index=False)
for _,r in q.sample(120,random_state=3341).iterrows():
 g=groups[(r.era,r.industry_code,r.block)];w=g[g.date.le(r.date)].tail(26);assert len(w)==26 and w.day_i.diff().iloc[1:].eq(1).all();x=np.log(w.nav.to_numpy()/m.reindex(w.date).to_numpy());inc=x[-1]-x[-6];out=x[-21]-x[-26];assert np.isclose(inc,r.incoming) and np.isclose(out,r.outgoing) and np.isclose((inc-out)/4,r.rate_change)
inputs=[nf,pf,mf,Path(__file__),EP/'restart/P41_rolloff_audit_plan.md',EP/'src/onset_replay.py'];(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',identity_rows=len(q),direct_window_checks=120,no_future_labels_read=True,inputs={str(p):sha(p) for p in inputs},artifacts={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}),indent=2)+'\n');print(pd.DataFrame(rows).query('period=="2023+"').to_string(index=False))
