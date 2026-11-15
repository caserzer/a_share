"""Frozen monthly regime models on the existing daily onset research population."""
from common import *
import pandas as pd
from scipy.special import expit
from regime_core_r196 import arrays
from process_replay_r09 import cooldown_alerts

def run():
 out=ROOT/'outputs/r253';protocol=json.loads((ROOT/'protocols/r253.json').read_text())
 d=pd.read_parquet(ROOT/protocol['inputs'][0]);events=pd.read_csv(ROOT/protocol['inputs'][1],parse_dates=['date'])
 models=[m for m in json.loads((ROOT/protocol['inputs'][2]).read_text()) if m['family']=='core' and m['cohort']=='F' and m['method']=='F' and m['task']=='onset' and m['horizon']==20]
 assert len(models)==24 and all(m['converged'] for m in models)
 states=pd.read_parquet(ROOT/protocol['inputs'][4]).regime;d['regime']=d.date.map(states);assert d.regime.notna().all()
 cols=models[0]['columns'];rank=d.groupby(['era','level','date'])[cols].transform(centered_rank);parts=[]
 for m in models:
  g=d[d.era.eq(m['era'])&d.level.eq(m['level'])&d.year.eq(m['year'])].copy()
  x=(rank.loc[g.index,cols].to_numpy()-m['scaler_mean'])/m['scaler_scale'];x=arrays(x,g.regime)[m['variant']]
  z=x@np.asarray(m['coefficient']).ravel()+np.asarray(m['intercept']).item()
  g['score']=expit(z*np.asarray(m['calibration_coefficient']).item()+np.asarray(m['calibration_intercept']).item());g['variant']=m['variant'];parts.append(g)
 scored=pd.concat(parts,ignore_index=True);assert len(scored)==3*len(d)
 old=pd.read_parquet(ROOT/protocol['inputs'][3]);old=old[(old.family=='core')&(old.cohort=='F')&(old.method=='F')&(old.task=='onset')&(old.horizon==20)]
 match=old.merge(scored[KEY+['date','variant','score']],on=KEY+['date','variant'],how='left',validate='one_to_one');assert match.score.notna().all()
 err=float((match.prediction-match.score).abs().max());assert err<1e-10
 scored.to_parquet(out/'scores.parquet',index=False)
 calendar=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index
 ends=pd.Series(calendar,index=calendar).groupby(calendar.to_period('M')).max();ends=ends[[p.end_time.normalize()<=calendar.max() for p in ends.index]]
 allalerts=[];hits=[];rows=[]
 for variant,s in scored.groupby('variant'):
  eligible=s[s.eligible];raw=pd.concat([g.sort_values(['score','industry_code'],ascending=[False,True]).head(int(np.ceil(.2*len(g)))) for _,g in eligible.groupby(['era','level','date'])])
  for strategy,a in {'daily':raw,'monthly':raw[raw.date.isin(ends.values)],'daily_cooldown20':cooldown_alerts(raw)}.items():
   a=a.copy();a['strategy']=strategy;allalerts.append(a)
   look={k:g for k,g in a.groupby(KEY+['block'])};hh=[]
   for e in events.itertuples():
    g=look.get((e.era,e.level,e.industry_code,e.block));w=g[g.day_i.between(e.day_i-20,e.day_i-1)] if g is not None else pd.DataFrame()
    hit=bool(e.evaluable) and len(w)>0
    hh.append(dict(era=e.era,level=e.level,industry_code=e.industry_code,block=e.block,date=e.date,day_i=e.day_i,evaluable=e.evaluable,variant=variant,strategy=strategy,hit=hit,lead_sessions=e.day_i-w.day_i.min() if hit else np.nan))
   h=pd.DataFrame(hh);hits.append(h)
   for (era,level),g in a.groupby(['era','level']):
    v=h[h.era.eq(era)&h.level.eq(level)&h.evaluable];known=g[g.y.notna()]
    months=eligible[eligible.era.eq(era)&eligible.level.eq(level)].date.dt.to_period('M').nunique()
    unique=g.assign(month=g.date.dt.to_period('M')).drop_duplicates(['industry_code','month'])
    rows.append(dict(era=era,level=level,variant=variant,strategy=strategy,events=len(v),hit_events=int(v.hit.sum()),process_recall=v.hit.mean(),median_lead_sessions=v.loc[v.hit,'lead_sessions'].median(),alerts=len(g),alerts_per_month=len(g)/months,repeat_alerts=len(g)-len(unique),mature_alerts=len(known),unknown_outcomes=int(g.y.isna().sum()),fixed_horizon_precision=known.y.mean(),events_per100_alerts=100*v.hit.sum()/len(g)))
 pd.concat(allalerts,ignore_index=True).to_parquet(out/'alerts.parquet',index=False);pd.concat(hits,ignore_index=True).to_parquet(out/'event_hits.parquet',index=False)
 summary=pd.DataFrame(rows);summary.to_csv(out/'summary.csv',index=False)
 base=summary[summary.variant.eq('base')];cmp=summary[~summary.variant.eq('base')].merge(base,on=['era','level','strategy'],suffixes=('','_base'),validate='many_to_one')
 for c in ['process_recall','fixed_horizon_precision','median_lead_sessions','alerts','events_per100_alerts']:cmp[c+'_delta']=cmp[c]-cmp[c+'_base']
 assert cmp.events.eq(cmp.events_base).all();cmp.to_csv(out/'comparisons.csv',index=False)
 js(out/'receipt.json',dict(status='PASS',models=len(models),daily_rows=len(scored),monthly_rows=len(match),monthly_max_error=err,inputs={p:sha(ROOT/p) for p in protocol['inputs']},protocol_sha256=sha(ROOT/'protocols/r253.json'),code_sha256=sha(__file__),no_refit=True,adoption=False))
 print(summary.to_string(index=False),flush=True)
if __name__=='__main__':run()
