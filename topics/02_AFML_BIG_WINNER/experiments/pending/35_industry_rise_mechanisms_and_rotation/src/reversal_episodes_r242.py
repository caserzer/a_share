from common import *
import pandas as pd
from regime_reversal_actions_r220 import IDS

def prepare():
 d=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet').sort_values(KEY+['date']).reset_index(drop=True)
 m=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close
 cal=pd.DatetimeIndex(m.index);d['day_i']=cal.get_indexer(d.date)
 d['relative']=d.nav.to_numpy()/m.reindex(d.date).to_numpy()
 d['valid']=np.isfinite(d.relative)&d.relative.gt(0)&d.block.notna()&d.day_i.ge(0)
 return d,cal

def catalogue(d):
 events=[];segments=[]
 for key,g in d.groupby(KEY):
  prev=None;segment=-1;peak=None;active=None
  for row in g.itertuples():
   boundary=prev is None or not row.valid or not prev.valid or row.block!=prev.block or row.day_i!=prev.day_i+1
   if boundary:
    if active is not None:events.append(active);active=None
    peak=None
   if not row.valid:prev=row;continue
   if peak is None:
    segment+=1;start=row.day_i;peak=row.relative;peak_i=row.day_i
    segments.append(dict(zip(KEY,key),segment=segment,start_i=start,end_i=start,rows=1))
   else:
    segments[-1]['end_i']=row.day_i;segments[-1]['rows']+=1
    if active is not None:
     if row.relative>=peak:
      active['recovery_i']=row.day_i;active['right_censored']=False;events.append(active);active=None;peak=row.relative;peak_i=row.day_i
    elif row.relative>=peak:peak=row.relative;peak_i=row.day_i
    elif row.relative/peak<=.92:
     active=dict(zip(KEY,key),segment=segment,peak_i=peak_i,breach_i=row.day_i,recovery_i=np.nan,left_boundary=peak_i==start,right_censored=True)
   prev=row
  if active is not None:events.append(active)
 e=pd.DataFrame(events,columns=KEY+['segment','peak_i','breach_i','recovery_i','left_boundary','right_censored']).sort_values(KEY+['breach_i']).reset_index(drop=True);e['episode_id']=np.arange(len(e))
 return e,pd.DataFrame(segments)

def run():
 out=ROOT/'outputs/r242';out.mkdir(exist_ok=True);d,cal=prepare();e,s=catalogue(d)
 for col in ['peak','breach','recovery']:
  e[col+'_date']=[cal[int(i)] if pd.notna(i) else pd.NaT for i in e[col+'_i']]
 e.to_parquet(out/'episodes.parquet',index=False);s.to_parquet(out/'segments.parquet',index=False)
 p=pd.read_parquet(ROOT/'outputs/r220/actions.parquet');assert p.horizon.eq(20).all()
 origins=p[KEY+['date','status']].drop_duplicates();assert not origins.duplicated(KEY+['date']).any()
 lookup={k:g for k,g in e[~e.left_boundary].groupby(KEY)};rows=[]
 for row in origins.to_dict('records'):
  i=cal.get_indexer([row['date']])[0];row.update(episode_id=np.nan,signal_lead=np.nan)
  if row['status']=='valid' and i>=0:
   pool=lookup.get(tuple(row[k] for k in KEY))
   if pool is not None:
    match=pool[pool.breach_i.between(i+2,i+21)]
    if len(match):hit=match.iloc[0];row.update(episode_id=int(hit.episode_id),signal_lead=int(hit.breach_i-i))
  rows.append(row)
 origins=pd.DataFrame(rows);origins.to_parquet(out/'origin_matches.parquet',index=False)
 p=p.merge(origins.drop(columns='status'),on=KEY+['date'],validate='many_to_one');metrics=[];matches=[]
 for key,g in p.groupby(IDS):
  ident=dict(zip(IDS,key));eligible=g[g.episode_id.notna()];alerts=eligible[eligible.alert]
  detected=alerts.sort_values('date').drop_duplicates('episode_id');observable=eligible.episode_id.nunique()
  metrics.append(dict(ident,candidates=len(g),alerts=int(g.alert.sum()),unknown_path=int(g.status.ne('valid').sum()),observable_episodes=observable,detected_episodes=len(detected),duplicate_episode_alerts=len(alerts)-len(detected),matched_alerts=len(alerts),unmatched_known_alerts=int((g.alert&g.status.eq('valid')&g.episode_id.isna()).sum()),recall=len(detected)/observable if observable else np.nan))
  for row in detected[['episode_id','date','signal_lead']].to_dict('records'):matches.append(dict(ident,**row))
 metrics=pd.DataFrame(metrics);matches=pd.DataFrame(matches);metrics.to_csv(out/'model_metrics.csv',index=False);matches.to_parquet(out/'first_alerts.parquet',index=False)
 pairs=[];baseids=[x for x in IDS if x!='variant']
 for key,g in metrics.groupby(baseids):
  ident=dict(zip(baseids,key));base=g[g.variant.eq('base')].iloc[0];mg=matches
  for k,v in ident.items():mg=mg[mg[k].eq(v)]
  for variant in ['state','interaction']:
   new=g[g.variant.eq(variant)].iloc[0];assert new.observable_episodes==base.observable_episodes
   q=mg[mg.variant.eq(variant)].merge(mg[mg.variant.eq('base')],on='episode_id',suffixes=('_new','_base'),validate='one_to_one');delta=q.signal_lead_new-q.signal_lead_base
   pairs.append(dict(ident,comparison=variant+'-base',observable_episodes=int(base.observable_episodes),delta_recall=new.recall-base.recall,delta_detected=int(new.detected_episodes-base.detected_episodes),jointly_detected=len(q),earlier=int((delta>0).sum()),same=int((delta==0).sum()),later=int((delta<0).sum()),mean_paired_lead_delta=delta.mean()))
 pairs=pd.DataFrame(pairs);pairs.to_csv(out/'comparisons.csv',index=False)
 coverage=e.groupby(['era','level']).agg(episodes=('episode_id','size'),left_boundary=('left_boundary','sum'),right_censored=('right_censored','sum')).reset_index();coverage.to_csv(out/'catalogue_coverage.csv',index=False)
 inputs=[ROOT/'outputs/r129/daily_2026-10-21.parquet',CACHE/'forecast_v5/CSI_ALL.parquet',ROOT/'outputs/r220/actions.parquet',ROOT/'protocols/r242.json',Path(__file__)]
 result=dict(status='PASS',daily_rows=len(d),segments=len(s),catalogue_episodes=len(e),left_boundary=int(e.left_boundary.sum()),right_censored=int(e.right_censored.sum()),origins=len(origins),matched_origins=int(origins.episode_id.notna().sum()),unique_matched_episodes=int(origins.episode_id.nunique()),model_groups=len(metrics),comparisons=len(pairs),adoption=False,inputs={str(f):sha(f) for f in inputs},outputs={f.name:sha(f) for f in out.iterdir() if f.suffix in ['.parquet','.csv']})
 js(out/'verification.json',result);print({k:v for k,v in result.items() if k not in ['inputs','outputs']});print(pairs.groupby('comparison')[['delta_recall','earlier','same','later','mean_paired_lead_delta']].agg(['median','sum']).to_string())
if __name__=='__main__':run()
