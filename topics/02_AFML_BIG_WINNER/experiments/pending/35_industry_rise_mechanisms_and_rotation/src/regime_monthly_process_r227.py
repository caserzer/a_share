from common import *
import pandas as pd
from regime_reversal_actions_r220 import IDS

def run():
 out=ROOT/'outputs/r227';out.mkdir(exist_ok=True)
 paths=[ROOT/'outputs/r221/actions.parquet',ROOT/'outputs/r155/evaluation/outputs/r09/confirmation_events.csv',ROOT/'outputs/r129/daily_2026-10-21.parquet',CACHE/'forecast_v5/CSI_ALL.parquet']
 a=pd.read_parquet(paths[0]);e=pd.read_csv(paths[1],parse_dates=['date']);d=pd.read_parquet(paths[2],columns=KEY+['date','block']);cal=pd.DatetimeIndex(pd.read_parquet(paths[3]).index)
 assert not d.duplicated(KEY+['date']).any();a=a.merge(d,on=KEY+['date'],how='left',validate='many_to_one');assert a.block.notna().all();a['day_i']=cal.get_indexer(a.date);assert a.day_i.ge(0).all();e['event_id']=np.arange(len(e));assert (cal.get_indexer(e.date)==e.day_i).all()
 # Frozen catalogue cluster spacing prevents one alert matching two events of one block.
 assert e.sort_values('day_i').groupby(KEY+['block']).day_i.diff().dropna().gt(20).all()
 rows=[];summary=[]
 for key,g in a.groupby(IDS):
  ident=dict(zip(IDS,key));events=e[e.era.eq(ident['era'])&e.level.eq(ident['level'])];schedule=np.sort(g.day_i.unique());lookup={k:z for k,z in g.groupby(['industry_code','block'])};records=[]
  for ev in events.to_dict('records'):
   dates=schedule[(schedule>=ev['day_i']-20)&(schedule<ev['day_i'])];v=lookup.get((ev['industry_code'],ev['block']));v=v[v.day_i.between(ev['day_i']-20,ev['day_i']-1)] if v is not None else pd.DataFrame();alerts=v[v.alert] if len(v) else v;status='left_censored' if not ev['evaluable'] else 'no_scheduled_origin' if len(dates)==0 else 'evaluable';hit=status=='evaluable' and len(alerts)>0
   rec=dict(ident,event_id=ev['event_id'],event_date=ev['date'],industry_code=ev['industry_code'],block=ev['block'],event_day_i=ev['day_i'],status=status,scheduled_origins=len(dates),candidate_origins=len(v),matched_alerts=len(alerts),hit=hit,signal_lead=np.nan,executable_lead=np.nan,first_alert=pd.NaT)
   if hit:
    first=alerts.sort_values('day_i').iloc[0];rec.update(first_alert=first.date,signal_lead=ev['day_i']-first.day_i,executable_lead=ev['day_i']-first.day_i-1)
   records.append(rec)
  z=pd.DataFrame(records);valid=z[z.status.eq('evaluable')];covered=valid[valid.candidate_origins.gt(0)];hits=valid[valid.hit];selected=g[g.alert]
  summary.append(dict(ident,reference_events=len(z),left_censored=int(z.status.eq('left_censored').sum()),no_schedule=int(z.status.eq('no_scheduled_origin').sum()),events=len(valid),candidate_covered=len(covered),zero_candidate=int(valid.candidate_origins.eq(0).sum()),hits=len(hits),recall=len(hits)/len(valid) if len(valid) else np.nan,covered_recall=len(hits)/len(covered) if len(covered) else np.nan,signal_lead=hits.signal_lead.median(),executable_lead=hits.executable_lead.median(),alerts=len(selected),signal_months=g.date.dt.to_period('M').nunique(),events_per100_alerts=100*len(hits)/len(selected) if len(selected) else np.nan))
  rows.extend(records)
 hits=pd.DataFrame(rows);s=pd.DataFrame(summary);hits.to_parquet(out/'event_matches.parquet',index=False);s.to_csv(out/'summary.csv',index=False);a[IDS+['industry_code','date','day_i','block','alert']].to_parquet(out/'signal_inventory.parquet',index=False);pairs=[]
 for key,g in s.groupby([x for x in IDS if x!='variant']):
  base=g[g.variant.eq('base')].iloc[0]
  for variant in ['state','interaction']:
   v=g[g.variant.eq(variant)].iloc[0]
   for c in ['events','candidate_covered','alerts','signal_months']:assert v[c]==base[c]
   rec={x:base[x] for x in IDS if x!='variant'};rec['comparison']=variant+'-base'
   for c in ['recall','covered_recall','hits','signal_lead','executable_lead','events_per100_alerts']:rec['delta_'+c]=v[c]-base[c]
   pairs.append(rec)
 pd.DataFrame(pairs).to_csv(out/'comparisons.csv',index=False)
 js(out/'verification.json',dict(status='PASS',groups=len(s),reference_events=len(e),event_records=len(hits),inputs={str(p):sha(p) for p in paths+[ROOT/'protocols/r227.json',Path(__file__)]},outputs={x:sha(out/x) for x in ['event_matches.parquet','summary.csv','signal_inventory.parquet','comparisons.csv']},adoption=False,scope='Monthly process detection conditional on frozen R155 reference event catalogue; not economic phase or daily prediction'))
 print(pd.DataFrame(pairs).groupby('comparison').delta_recall.agg(['count','median',lambda x:sum(x>0)]).to_string())
if __name__=='__main__':run()
