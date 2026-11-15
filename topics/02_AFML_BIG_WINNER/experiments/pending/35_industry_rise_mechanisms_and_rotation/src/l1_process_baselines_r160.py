"""Frozen L1 process baseline comparison on identical candidate days."""
import pandas as pd
from common import *
from process_replay_r09 import cooldown_alerts

def run():
 out=ROOT/'outputs/r160';out.mkdir(parents=True,exist_ok=True);prior=ROOT/'outputs/r159/evaluation';sp=prior/'data/r09_daily_scores.parquet';ep=prior/'outputs/r09/confirmation_events.csv';bp=CACHE/'forecast_v5/CSI_ALL.parquet';s=pd.read_parquet(sp);events=pd.read_csv(ep,parse_dates=['date']);calendar=pd.DatetimeIndex(pd.read_parquet(bp).index);ends=pd.Series(calendar,index=calendar).groupby(calendar.to_period('M')).max();ends=set(ends[[p.end_time.normalize()<=calendar.max() for p in ends.index]])
 ranks=s.groupby(['era','level','date'])[['mom20','mom60','vol20','dd60']].transform(centered_rank);s['F']=((ranks.mom20+ranks.mom60)/2-ranks.vol20+ranks.dd60)/3;s['momentum']=ranks.mom60;s['raw_logit']=s.score;s.to_parquet(out/'candidate_scores.parquet',index=False);eligible=s[s.eligible];parts=[]
 for method in ['raw_logit','F','momentum']:
  raw=pd.concat([g.sort_values([method,'industry_code'],ascending=[False,True]).head(int(np.ceil(.2*len(g)))) for _,g in eligible.groupby(['era','level','date'])]);sets={'daily':raw,'monthly':raw[raw.date.isin(ends)],'daily_cooldown20':cooldown_alerts(raw)}
  for strategy,g in sets.items():parts.append(g.assign(method=method,strategy=strategy))
 alerts=pd.concat(parts,ignore_index=True);alerts.to_parquet(out/'alerts.parquet',index=False);old=pd.read_parquet(prior/'outputs/r09/alerts.parquet');k=KEY+['date','strategy'];assert set(map(tuple,old[k].to_numpy()))==set(map(tuple,alerts[alerts.method.eq('raw_logit')][k].to_numpy()))
 lookup={key:g.sort_values('day_i') for key,g in alerts.groupby(['method','strategy']+KEY+['block'])};records=[]
 for method in ['raw_logit','F','momentum']:
  for strategy in ['daily','monthly','daily_cooldown20']:
   for e in events.to_dict('records'):
    g=lookup.get((method,strategy)+tuple(e[x] for x in KEY)+(e['block'],));q=g[g.day_i.between(e['day_i']-20,e['day_i']-1)] if g is not None else pd.DataFrame();hit=bool(e['evaluable'] and len(q));records.append(dict(**e,method=method,strategy=strategy,hit=hit,lead=e['day_i']-q.iloc[0].day_i if hit else np.nan))
 hits=pd.DataFrame(records);hits.to_parquet(out/'event_hits.parquet',index=False);rows=[]
 for (method,strategy),g in alerts.groupby(['method','strategy']):
  h=hits[hits.method.eq(method)&hits.strategy.eq(strategy)]
  for year in [0,2025,2026]:
   a=g if year==0 else g[g.date.dt.year.eq(year)];e=h if year==0 else h[h.date.dt.year.eq(year)];v=e[e.evaluable];known=a[a.y.notna()];unique=a.assign(month=a.date.dt.to_period('M')).drop_duplicates(['industry_code','month']);rows.append(dict(method=method,strategy=strategy,year=year,alerts=len(a),mature=len(known),unknown=int(a.y.isna().sum()),precision=known.y.mean(),known_successes=int(known.y.sum()),precision_lower=known.y.sum()/len(a),precision_upper=(known.y.sum()+a.y.isna().sum())/len(a),events=len(v),left_censored=int((~e.evaluable).sum()),hit_events=int(v.hit.sum()),recall=v.hit.mean(),median_lead=v.loc[v.hit,'lead'].median(),unique_industry_months=len(unique),repeat_alerts=len(a)-len(unique)))
 summary=pd.DataFrame(rows);summary.to_csv(out/'summary.csv',index=False);d=[]
 for baseline in ['F','momentum']:
  model=summary[summary.method.eq('raw_logit')];base=summary[summary.method.eq(baseline)];p=model.merge(base,on=['year','strategy'],suffixes=('_model','_baseline'),validate='one_to_one');p['baseline']=baseline
  for c in ['alerts','precision','recall','median_lead','repeat_alerts']:p['delta_'+c]=p[c+'_model']-p[c+'_baseline']
  d.append(p)
 pd.concat(d,ignore_index=True).to_csv(out/'comparisons.csv',index=False)
 js(out/'receipt.json',dict(status='PASS',reads={str(p):sha(p) for p in [sp,ep,bp,prior/'outputs/r09/alerts.parquet',ROOT/'outputs/r159/verification.json',ROOT/'protocols/r160.json',Path(__file__),ROOT/'src/process_replay_r09.py']},candidate_rows=len(s),eligible_rows=len(eligible),original_alerts_reproduced=True,acceptance='not_established; descriptive comparison'))
 print(summary.to_string(index=False))
if __name__=='__main__':run()
