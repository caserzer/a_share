"""Independent full-origin outcome and exit-accounting verification."""
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r136';base=out/'evaluation';p=pd.read_parquet(base/'data/r57_exit_origins.parquet');d=pd.read_csv(base/'outputs/r57/date_metrics.csv',parse_dates=['date']);keys=['era','level','horizon','method','date'];look=d.set_index(keys+['cost']);count=0
 for path,h in json.loads((out/'summary.json').read_text())['reads'].items():assert sha(path)==h
 cols=KEY+['date','return20','market_return20','return60','market_return60'];panel=pd.concat([pd.read_parquet(ROOT/'outputs/r130/monthly_panel.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet',columns=cols)]).set_index(KEY+['date']);q=panel.loc[pd.MultiIndex.from_frame(p[KEY+['date']])]
 for c in cols[len(KEY)+1:]:assert np.allclose(q[c],p[c],equal_nan=True)
 for key,g in p.groupby(keys):
  selected=g.sort_values(['prediction','industry_code'],ascending=[False,True]).head(int(np.ceil(len(g)/5)));assert set(g[g.alert].industry_code)==set(selected.industry_code);h=key[2];r=g[f'return{h}'];b=g[f'market_return{h}'];known=r.notna()&b.notna();valid=known&g.alert
  assert np.allclose(g.excess,r-b,equal_nan=True)
  for c in [0,.002,.005]:
   row=look.loc[key+(c,)];assert row.origins==len(g) and row.alerts==len(selected) and row.complete==known.sum() and row.alert_complete==valid.sum() and row.policy_complete==known.all()
   hold=(1+r)*(1-c);cash=(1-c)-hold;switch=(1-c)**3*(1+b)-hold
   values={'alert_cash':cash[valid].mean(),'alert_market':switch[valid].mean(),'wrong_absolute':r[valid].gt(0).mean(),'wrong_relative':(r[valid]-b[valid]).gt(0).mean(),'missed_upside':r[valid].clip(lower=0).mean(),'avoided_loss':-r[valid].clip(upper=0).mean(),'precision':g.loc[valid,'y'].mean(),'policy_cash':cash[g.alert].sum()/len(g) if known.all() else np.nan,'policy_market':switch[g.alert].sum()/len(g) if known.all() else np.nan}
   for col,v in values.items():assert np.isclose(row[col],v,equal_nan=True),(key,c,col)
   count+=1
 pairs=pd.read_csv(base/'outputs/r57/paired_policy.csv')
 for row in pairs.to_dict('records'):
  z=d.copy()
  for k in ['era','level','horizon','cost']:z=z[z[k].eq(row[k])]
  w=z.pivot(index='date',columns='method',values=row['metric']);delta=w.FSMD-w.FSM;assert row['months']==delta.count() and np.isclose(row['mean_delta'],delta.mean(),equal_nan=True)
 js(out/'verification.json',dict(status='PASS',origin_outcomes=len(p),date_cost_checks=count,paired_policies=len(pairs),verifier_sha256=sha(__file__),boundary='All outcome fields match R130 independently price-verified labels; no claim of actual execution'))
 print('EXIT VERIFIED',len(p),count,len(pairs),flush=True)
if __name__=='__main__':run()
