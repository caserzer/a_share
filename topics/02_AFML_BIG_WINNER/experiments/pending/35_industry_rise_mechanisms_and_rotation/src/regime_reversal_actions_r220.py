from common import *
import pandas as pd
from portfolio_r04 import path_for
from followup_r10 import exit_economics
IDS=['source_round','family','era','level','cohort','method','horizon','objective','variant']
def run():
 out=ROOT/'outputs/r220';out.mkdir(exist_ok=True);parts=[];reads=[];coverage=[]
 for rnd in [196,199,200,201]:
  path=ROOT/f'outputs/r{rnd}/predictions.parquet';reads.append(path);p=pd.read_parquet(path);p=p[p.task.eq('reversal')].copy();coverage.append(dict(round=rnd,reversal_predictions=len(p)));p['source_round']=rnd
  if 'objective' not in p:p['objective']='reversal'
  parts.append(p)
 p=pd.concat(parts,ignore_index=True);p['alert']=False
 for _,g in p.groupby(IDS+['date']):
  chosen=g.sort_values(['prediction','industry_code'],ascending=[False,True]).head(int(np.ceil(len(g)*.2))).index;p.loc[chosen,'alert']=True
 pricepaths=[ROOT/'outputs/r129/daily_2026-10-21.parquet',ROOT/'data/l1_daily.parquet'];reads+=pricepaths;prices=pd.concat([pd.read_parquet(x) for x in pricepaths],ignore_index=True);marketpath=CACHE/'forecast_v5/CSI_ALL.parquet';reads.append(marketpath);market=pd.read_parquet(marketpath).close;cal=pd.DatetimeIndex(market.index);prices['day_i']=cal.get_indexer(prices.date);lookup={k:g.set_index('date') for k,g in prices.groupby(KEY)};outcomes=[]
 for row in p[KEY+['date','horizon']].drop_duplicates().to_dict('records'):
  rec=dict(row,status='unknown_path');ix=cal.get_indexer([row['date']])[0];h=row['horizon']
  if ix>=0 and ix+1+h<len(cal):
   dates=cal[ix+1:ix+h+2];key=tuple(row[c] for c in KEY);a=path_for(lookup[key],dates) if key in lookup else None;b=market.loc[dates].to_numpy()/market.loc[dates[0]]
   if a is not None:
    rel=a/b;rec.update(status='valid',entry=dates[0],exit=dates[-1],ret=a[-1]-1,market=b[-1]-1,rel_trough=rel.min()-1,drawdown=(a/np.maximum.accumulate(a)-1).min(),path_label=float(rel.min()-1<=(-.08 if h==20 else -.12)))
  outcomes.append(rec)
 o=pd.DataFrame(outcomes);o.to_parquet(out/'paths.parquet',index=False);p=p.merge(o,on=KEY+['date','horizon'],validate='many_to_one');known=p.status.eq('valid')&p.y.notna();assert p.loc[known,'y'].eq(p.loc[known,'path_label']).all();p.to_parquet(out/'actions.parquet',index=False);metrics=[]
 for key,g in p.groupby(IDS+['date']):
  identity=dict(zip(IDS+['date'],key));v=g[g.status.eq('valid')];a=v[v.alert];label=g[g.y.notna()];tp=int((label.alert&label.y.eq(1)).sum());positives=int(label.y.eq(1).sum());alert_known=int(label.alert.sum())
  for cost in [0,.002,.005]:
   cash,switch=exit_economics(v.ret,v.market,cost);r=dict(identity,cost=cost,eligible=len(g),alerts=int(g.alert.sum()),known_paths=len(v),known_alert_paths=len(a),known_labels=len(label),tp=tp,known_positives=positives,known_alert_labels=alert_known,precision=tp/alert_known if alert_known else np.nan,recall=tp/positives if positives else np.nan,cash_policy_gain=(cash*v.alert).mean(),market_policy_gain=(switch*v.alert).mean(),cash_alert_gain=cash[v.alert].mean(),market_alert_gain=switch[v.alert].mean(),wrong_absolute_exit=a.ret.gt(0).mean(),wrong_relative_exit=a.ret.gt(a.market).mean(),missed_positive=a.ret.clip(lower=0).mean(),avoided_negative=(-a.ret.clip(upper=0)).mean(),alert_drawdown=a.drawdown.mean());metrics.append(r)
 d=pd.DataFrame(metrics);d.to_csv(out/'date_metrics.csv',index=False);values=['cash_policy_gain','market_policy_gain','cash_alert_gain','market_alert_gain','precision','recall','wrong_absolute_exit','wrong_relative_exit','missed_positive','avoided_negative','alert_drawdown'];d.groupby(IDS+['cost'])[values].mean().reset_index().to_csv(out/'summary.csv',index=False);pairs=[]
 group=[x for x in IDS if x!='variant']+['cost']
 for key,g in d.groupby(group):
  for variant in ['state','interaction']:
   q=g[g.variant.eq(variant)].merge(g[g.variant.eq('base')],on='date',suffixes=('_new','_base'),validate='one_to_one');assert len(q)==len(g[g.variant.eq(variant)]);assert q.eligible_new.eq(q.eligible_base).all() and q.alerts_new.eq(q.alerts_base).all()
   r=dict(zip(group,key),comparison=variant+'-base',dates=len(q))
   for c in values:r['delta_'+c]=(q[c+'_new']-q[c+'_base']).mean()
   pairs.append(r)
 pd.DataFrame(pairs).to_csv(out/'comparisons.csv',index=False);js(out/'verification.json',dict(status='PASS',predictions=len(p),alerts=int(p.alert.sum()),unique_paths=len(o),valid_paths=int(o.status.eq('valid').sum()),known_label_checks=int(known.sum()),coverage=coverage,adoption=False,inputs={str(x):sha(x) for x in reads+[ROOT/'protocols/r220.json',Path(__file__),ROOT/'src/followup_r10.py']},outputs={x:sha(out/x) for x in ['paths.parquet','actions.parquet','date_metrics.csv','summary.csv','comparisons.csv']}));print(len(p),sum(p.alert),len(o));print(pd.DataFrame(pairs).query("horizon==20 and cost==.005").groupby(['source_round','comparison'])[['delta_market_policy_gain','delta_precision']].agg(['count','median',lambda x:sum(x>0)]).to_string())
if __name__=='__main__':run()
