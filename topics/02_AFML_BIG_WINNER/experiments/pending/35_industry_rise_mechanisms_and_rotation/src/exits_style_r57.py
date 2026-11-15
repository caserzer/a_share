import pandas as pd
from common import *
from followup_r10 import exit_economics

def run():
 out=ROOT/'outputs/r57';out.mkdir(exist_ok=True)
 paths=[ROOT/'outputs/r56/predictions.parquet',ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'protocols/r57.json',ROOT/'src/followup_r10.py',Path(__file__)]
 p=pd.read_parquet(paths[0]);p=p[p.task.eq('reversal')].copy();cols=KEY+['date','return20','market_return20','return60','market_return60']
 panel=pd.concat([pd.read_parquet(x,columns=cols) for x in paths[1:3]],ignore_index=True);p=p.merge(panel,on=KEY+['date'],validate='many_to_one');p['alert']=False
 keys=['era','level','horizon','method','date'];records=[]
 for key,g in p.groupby(keys):
  selected=g.sort_values(['prediction','industry_code'],ascending=[False,True]).head(int(np.ceil(len(g)*.2))).index;p.loc[selected,'alert']=True;g=g.copy();g['alert']=g.index.isin(selected);h=key[2];r=g[f'return{h}'];b=g[f'market_return{h}'];known=r.notna()&b.notna();assert np.allclose(g.excess,r-b,equal_nan=True)
  for c in [0,.002,.005]:
   cash,switch=exit_economics(r,b,c);alert=g.alert;valid=alert&known;complete=bool(known.all())
   rec=dict(zip(keys,key),cost=c,origins=len(g),alerts=int(alert.sum()),complete=int(known.sum()),alert_complete=int(valid.sum()),policy_complete=complete,
    alert_cash=cash[valid].mean(),alert_market=switch[valid].mean(),wrong_absolute=r[valid].gt(0).mean(),wrong_relative=(r[valid]-b[valid]).gt(0).mean(),missed_upside=r[valid].clip(lower=0).mean(),avoided_loss=(-r[valid].clip(upper=0)).mean(),precision=g.loc[valid,'y'].mean(),
    policy_cash=cash.where(alert,0).mean() if complete else np.nan,policy_market=switch.where(alert,0).mean() if complete else np.nan)
   records.append(rec)
 p.to_parquet(ROOT/'data/r57_exit_origins.parquet',index=False);d=pd.DataFrame(records);d.to_csv(out/'date_metrics.csv',index=False)
 metrics=['alert_cash','alert_market','wrong_absolute','wrong_relative','missed_upside','avoided_loss','precision','policy_cash','policy_market'];group=keys[:-1]+['cost']
 d.groupby(group)[metrics].mean().to_csv(out/'summary.csv');d.assign(year=d.date.dt.year).groupby(group+['year'])[metrics].mean().to_csv(out/'annual.csv')
 pairs=[]
 for key,g in d.groupby(['era','level','horizon','cost']):
  for metric in ['policy_cash','policy_market']:
   w=g.pivot(index='date',columns='method',values=metric)
   for name,a,b in [('diffusion_with_market_controls','FSMD','FSM')]:
    delta=w[a]-w[b];pairs.append(dict(zip(['era','level','horizon','cost'],key),metric=metric,comparison=name,months=int(delta.count()),mean_delta=delta.mean()))
 pd.DataFrame(pairs).to_csv(out/'paired_policy.csv',index=False)
 js(out/'receipt.json',dict(reads={str(x):sha(x) for x in paths},origin_rows=len(p),date_rows=len(d),origin_sha256=sha(ROOT/'data/r57_exit_origins.parquet'),status='historical diagnostic only'))
 print(d[d.cost.eq(.002)].groupby(['era','level','method'])[['alert_cash','alert_market','policy_cash','policy_market']].mean().to_string())
if __name__=='__main__':run()
