import pandas as pd
from common import *
from process_replay_r09 import cooldown_alerts

def run():
 out=ROOT/'outputs/r98';out.mkdir(exist_ok=True);pp=ROOT/'outputs/r97/predictions.parquet';sp=ROOT/'data/r09_daily_scores.parquet';ep=ROOT/'outputs/r09/confirmation_events.csv';bp=CACHE/'forecast_v5/CSI_ALL.parquet';p=pd.read_parquet(pp);s=pd.read_parquet(sp);d=p.merge(s[KEY+['date','block','day_i','mom20','return20','excess20']],on=KEY+['date'],validate='one_to_one');calendar=pd.DatetimeIndex(pd.read_parquet(bp).index);end=pd.Series(calendar,index=calendar).groupby(calendar.to_period('M')).max();ends=set(end[[m.end_time.normalize()<=calendar.max() for m in end.index]]);alerts=[]
 for version,col in [('monthly_calibration','monthly_probability'),('daily_calibration','daily_probability')]:
  selected=[]
  for _,g in d.groupby(['era','level','date']):selected.append(g.sort_values([col,'industry_code'],ascending=[False,True]).head(int(np.ceil(.2*len(g)))))
  raw=pd.concat(selected);sets={'daily':raw,'monthly':raw[raw.date.isin(ends)],'daily_cooldown20':cooldown_alerts(raw)}
  for strategy,g in sets.items():q=g.copy();q['version']=version;q['strategy']=strategy;q['selected_score']=q[col];alerts.append(q)
 a=pd.concat(alerts,ignore_index=True);a.to_parquet(out/'alerts.parquet',index=False);old=pd.read_parquet(ROOT/'outputs/r09/alerts.parquet');ak=KEY+['date','strategy'];assert set(map(tuple,a[a.version.eq('monthly_calibration')][ak].to_numpy()))==set(map(tuple,old[ak].to_numpy()));events=pd.read_csv(ep,parse_dates=['date']);lookup={k:g.sort_values('day_i') for k,g in a.groupby(['version','strategy']+KEY+['block'])};hits=[]
 for version in ['monthly_calibration','daily_calibration']:
  for strategy in ['daily','monthly','daily_cooldown20']:
   for x in events.to_dict('records'):
    key=(version,strategy)+tuple(x[k] for k in KEY)+(x['block'],);g=lookup.get(key);q=g[g.day_i.between(x['day_i']-20,x['day_i']-1)] if g is not None else pd.DataFrame();hit=bool(x['evaluable'] and len(q));r=dict(**x,version=version,strategy=strategy,hit=hit,matched_alerts=len(q),first_alert=q.iloc[0].date if hit else None,lead_sessions=x['day_i']-q.iloc[0].day_i if hit else None);hits.append(r)
 h=pd.DataFrame(hits);h.to_parquet(out/'event_hits.parquet',index=False);a['year']=a.date.dt.year;h['year']=h.date.dt.year;summary=[]
 for key,g in a.groupby(['era','level','year','strategy','version']):
  z=h
  for k,v in zip(['era','level','year','strategy','version'],key):z=z[z[k].eq(v)]
  ev=z[z.evaluable];v=g[g.y.notna()];unique=g.assign(month=g.date.dt.to_period('M')).drop_duplicates(['industry_code','month']);summary.append(dict(zip(['era','level','year','strategy','version'],key),alerts=len(g),mature=len(v),unknown=len(g)-len(v),precision=v.y.mean(),unique_industry_months=len(unique),repeat_alerts=len(g)-len(unique),events=len(ev),left_censored=int((~z.evaluable).sum()),hit_events=int(ev.hit.sum()),recall=ev.hit.mean(),median_lead=ev.loc[ev.hit,'lead_sessions'].median(),hits_per100alerts=100*ev.hit.sum()/len(g)))
 js(out/'summary.json',summary);oldset=a[a.version.eq('monthly_calibration')][ak];newset=a[a.version.eq('daily_calibration')][ak];changes=oldset.merge(newset,on=ak,how='outer',indicator=True,validate='one_to_one');changes.to_parquet(out/'alert_identity_changes.parquet',index=False);paths=[pp,sp,ep,bp,ROOT/'outputs/r09/alerts.parquet',ROOT/'outputs/r97/verification.json',ROOT/'protocols/r98.json',Path(__file__),ROOT/'src/process_replay_r09.py'];js(out/'receipt.json',dict(reads={str(x):sha(x) for x in paths},alert_rows=len(a),event_hit_rows=len(h),baseline_reproduced=True));print(changes.groupby([changes.date.dt.year,'strategy','_merge'],observed=True).size().to_string());print(json.dumps([x for x in summary if x['year']==2021 and x['strategy']=='daily_cooldown20'],default=str))
if __name__=='__main__':run()
