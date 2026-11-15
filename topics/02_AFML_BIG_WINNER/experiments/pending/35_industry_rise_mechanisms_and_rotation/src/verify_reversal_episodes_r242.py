from common import *
import pandas as pd
from regime_reversal_actions_r220 import IDS

def run():
 out=ROOT/'outputs/r242';d=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet');market=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;cal=pd.DatetimeIndex(market.index)
 events=[];segments=[];source={}
 for key,g in d.groupby(KEY):
  g=g.sort_values('date').copy();g['i']=cal.get_indexer(g.date);g['r']=g.nav.to_numpy()/market.reindex(g.date).to_numpy()
  valid=np.isfinite(g.r)&g.r.gt(0)&g.block.notna()&g.i.ge(0)
  breaks=~valid|~valid.shift(fill_value=False)|g.block.ne(g.block.shift())|g.i.diff().ne(1)
  g['segraw']=breaks.cumsum();nseg=0
  source[key]=g
  for _,q in g[valid].groupby('segraw'):
   q=q.copy();start=int(q.i.iloc[0]);end=int(q.i.iloc[-1]);segments.append(dict(zip(KEY,key),segment=nseg,start_i=start,end_i=end,rows=len(q)))
   high=q.r.cummax();newhigh=q.r.ge(high.shift(fill_value=-np.inf));q['peakrun']=newhigh.cumsum()
   peaks=q.loc[newhigh,'i'].to_numpy();runs=list(q.groupby('peakrun'))
   for j,(_,a) in enumerate(runs):
    hits=a[a.r/a.r.iloc[0]<=.92]
    if len(hits):events.append(dict(zip(KEY,key),segment=nseg,peak_i=int(a.i.iloc[0]),breach_i=int(hits.i.iloc[0]),recovery_i=int(peaks[j+1]) if j+1<len(peaks) else np.nan,left_boundary=int(a.i.iloc[0])==start,right_censored=j+1==len(peaks)))
   nseg+=1
 expected=pd.DataFrame(events).sort_values(KEY+['breach_i']).reset_index(drop=True)
 actual=pd.read_parquet(out/'episodes.parquet');pd.testing.assert_frame_equal(expected,actual[expected.columns],check_dtype=False)
 es=pd.DataFrame(segments);saved=pd.read_parquet(out/'segments.parquet');pd.testing.assert_frame_equal(es,saved,check_dtype=False)
 origins=pd.read_parquet(out/'origin_matches.parquet');catalogue=actual[~actual.left_boundary];origin_checks=[]
 for row in origins.to_dict('records'):
  key=tuple(row[k] for k in KEY);i=cal.get_indexer([row['date']])[0];g=source[key];q=g[g.i.between(i+1,i+21)];valid=i>=0 and i+21<len(cal) and len(q)==21 and q.segraw.nunique()==1 and np.isfinite(q.r).all() and q.r.gt(0).all()
  assert valid==(row['status']=='valid')
  hits=catalogue
  for k,v in zip(KEY,key):hits=hits[hits[k].eq(v)]
  hits=hits[(hits.breach_i-(i+1)).between(1,20)] if valid else hits.iloc[:0]
  want=int(hits.episode_id.iloc[0]) if len(hits) else np.nan
  assert (pd.isna(want) and pd.isna(row['episode_id'])) or want==row['episode_id']
  if pd.notna(want):assert row['signal_lead']==int(hits.breach_i.iloc[0])-i
  origin_checks.append(valid)
 p=pd.read_parquet(ROOT/'outputs/r220/actions.parquet').merge(origins[KEY+['date','episode_id','signal_lead']],on=KEY+['date'],validate='many_to_one')
 metrics=pd.read_csv(out/'model_metrics.csv');matches=pd.read_parquet(out/'first_alerts.parquet');assert not matches.duplicated(IDS+['episode_id']).any();recomputed=[]
 for ident,g in p.groupby(IDS):
  r=metrics
  for k,v in zip(IDS,ident):r=r[r[k].eq(v)]
  assert len(r)==1;r=r.iloc[0];ep={int(x) for x in g.episode_id.dropna()};alerts=g[g.alert&g.episode_id.notna()];first={}
  for z in alerts.sort_values('date').to_dict('records'):first.setdefault(int(z['episode_id']),z)
  assert r.observable_episodes==len(ep) and r.detected_episodes==len(first) and r.duplicate_episode_alerts==len(alerts)-len(first)
  assert np.isclose(r.recall,len(first)/len(ep)) if ep else pd.isna(r.recall)
  for eid,z in first.items():recomputed.append(dict(zip(IDS,ident),episode_id=float(eid),date=z['date'],signal_lead=z['signal_lead']))
 exp=pd.DataFrame(recomputed).sort_values(IDS+['episode_id']).reset_index(drop=True);got=matches.sort_values(IDS+['episode_id']).reset_index(drop=True);pd.testing.assert_frame_equal(exp,got[exp.columns],check_dtype=False)
 pairs=pd.read_csv(out/'comparisons.csv');baseids=[k for k in IDS if k!='variant']
 for row in pairs.to_dict('records'):
  q=exp;mm=metrics
  for k in baseids:q=q[q[k].eq(row[k])];mm=mm[mm[k].eq(row[k])]
  v=row['comparison'].split('-')[0];a=q[q.variant.eq(v)].set_index('episode_id').signal_lead;b=q[q.variant.eq('base')].set_index('episode_id').signal_lead;delta=(a-b).dropna()
  assert row['jointly_detected']==len(delta) and row['earlier']==int((delta>0).sum()) and row['same']==int((delta==0).sum()) and row['later']==int((delta<0).sum())
  assert np.isclose(row['mean_paired_lead_delta'],delta.mean(),equal_nan=True)
  vals=mm.set_index('variant');assert np.isclose(row['delta_recall'],vals.loc[v,'recall']-vals.loc['base','recall'],equal_nan=True)
 receipt=json.loads((out/'verification.json').read_text())
 for f,h in receipt['inputs'].items():assert sha(Path(f))==h
 for f,h in receipt['outputs'].items():assert sha(out/f)==h
 js(out/'independent_verification.json',dict(status='PASS',episode_fields_checked=len(actual)*9,segments=len(es),origins=len(origins),model_groups=len(metrics),first_alert_records=len(exp),comparisons=len(pairs),code_sha256=sha(Path(__file__)),adoption=False))
 print('PASS',len(actual),len(origins),len(exp),len(pairs))
if __name__=='__main__':run()
