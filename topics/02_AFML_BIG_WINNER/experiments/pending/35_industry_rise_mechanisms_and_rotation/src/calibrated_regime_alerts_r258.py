from common import *
import pandas as pd
from process_replay_r09 import cooldown_alerts

def run():
 out=ROOT/'outputs/r258';p=pd.read_parquet(ROOT/'outputs/r256/predictions.parquet');s=pd.read_parquet(ROOT/'outputs/r253/scores.parquet');key=KEY+['date','variant'];d=p.merge(s[key+['block','day_i']],on=key,validate='one_to_one');assert len(d)==len(p)
 calendar=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index;ends=pd.Series(calendar,index=calendar).groupby(calendar.to_period('M')).max();ends=ends[[m.end_time.normalize()<=calendar.max() for m in ends.index]]
 parts=[];rankchanges=[]
 for variant,g in d.groupby('variant'):
  for version in ['monthly','daily']:
   col=version+'_probability';selected=[]
   for _,frame in g.groupby(['era','level','date']):selected.append(frame.sort_values([col,'industry_code'],ascending=[False,True]).head(int(np.ceil(.2*len(frame)))))
   raw=pd.concat(selected)
   for strategy,a in {'daily':raw,'monthly':raw[raw.date.isin(ends.values)],'daily_cooldown20':cooldown_alerts(raw)}.items():parts.append(a.assign(version=version,strategy=strategy))
  for (era,level,year),frame in g.groupby(['era','level','year']):
   changed=0;days=0
   for _,z in frame.groupby('date'):
    order=lambda col:list(z.sort_values([col,'industry_code'],ascending=[False,True]).industry_code)
    changed+=order('monthly_probability')!=order('daily_probability');days+=1
   rankchanges.append(dict(era=era,level=level,year=year,variant=variant,dates=days,changed_order_dates=changed))
 a=pd.concat(parts,ignore_index=True);a.to_parquet(out/'alerts.parquet',index=False)
 ak=key+['strategy'];old=pd.read_parquet(ROOT/'outputs/r253/alerts.parquet');assert set(map(tuple,a[a.version.eq('monthly')][ak].to_numpy()))==set(map(tuple,old[ak].to_numpy()))
 changes=a[a.version.eq('monthly')][ak].merge(a[a.version.eq('daily')][ak],on=ak,how='outer',indicator=True,validate='one_to_one');changes.to_parquet(out/'alert_changes.parquet',index=False)
 folds=json.loads((ROOT/'outputs/r256/folds.json').read_text())
 for row in rankchanges:
  f=next(f for f in folds if all(f[k]==row[k] for k in ['era','level','year','variant']));row['monthly_slope']=f['base_model']['calibration_coefficient'][0][0];row['daily_slope']=f['coefficient'];row['sign_flip']=np.sign(row['monthly_slope'])!=np.sign(row['daily_slope'])
 pd.DataFrame(rankchanges).to_csv(out/'rank_changes.csv',index=False)
 events=pd.read_csv(ROOT/'outputs/r155/evaluation/outputs/r09/confirmation_events.csv',parse_dates=['date']);lookup={k:g for k,g in a.groupby(['variant','version','strategy']+KEY+['block'])};hits=[]
 for variant in ['base','state','interaction']:
  for version in ['monthly','daily']:
   for strategy in ['monthly','daily','daily_cooldown20']:
    for e in events.to_dict('records'):
     g=lookup.get((variant,version,strategy,e['era'],e['level'],e['industry_code'],e['block']));w=g[g.day_i.between(e['day_i']-20,e['day_i']-1)] if g is not None else pd.DataFrame();hit=e['evaluable'] and len(w)>0
     hits.append(dict(e,variant=variant,version=version,strategy=strategy,hit=hit,lead_sessions=e['day_i']-w.day_i.min() if hit else np.nan))
 h=pd.DataFrame(hits);h.to_parquet(out/'event_hits.parquet',index=False);rows=[]
 for scope in ['pooled','annual']:
  aa=a.assign(year=a.date.dt.year);hh=h.assign(year=h.date.dt.year);groups=['era','level','variant','version','strategy']+(['year'] if scope=='annual' else [])
  for keys,g in aa.groupby(groups):
   ev=hh
   for name,value in zip(groups,keys):ev=ev[ev[name].eq(value)]
   valid=ev[ev.evaluable];rows.append(dict(zip(groups,keys),scope=scope,alerts=len(g),known=int(g.y.notna().sum()),unknown=int(g.y.isna().sum()),precision=g.y.mean(),events=len(valid),left_censored=int((~ev.evaluable).sum()),hit_events=int(valid.hit.sum()),recall=valid.hit.mean(),median_lead=valid.loc[valid.hit,'lead_sessions'].median()))
 pd.DataFrame(rows).to_csv(out/'summary.csv',index=False)
 js(out/'receipt.json',dict(status='PASS',monthly_alerts_match_r253=True,alert_rows=len(a),event_rows=len(h),folds=len(rankchanges),inputs={f:sha(ROOT/f) for f in ['outputs/r256/predictions.parquet','outputs/r256/folds.json','outputs/r253/scores.parquet','outputs/r253/alerts.parquet','outputs/r155/evaluation/outputs/r09/confirmation_events.csv']},protocol_sha256=sha(ROOT/'protocols/r258.json'),code_sha256=sha(__file__),adoption=False))
 print(pd.DataFrame(rankchanges).to_string(index=False))
if __name__=='__main__':run()
