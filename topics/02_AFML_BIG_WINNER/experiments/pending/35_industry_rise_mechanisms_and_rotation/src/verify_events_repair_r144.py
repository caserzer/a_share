"""Independent positional windows and complete-control checks for corrected events."""
import pandas as pd
from common import *
import verify_horizon_prices_r91

def run():
 out=ROOT/'outputs/r144';root=out/'evaluation';cache=root/'cache';rec=json.loads((out/'summary.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 verify_horizon_prices_r91.ROOT=root;verify_horizon_prices_r91.CACHE=cache;verify_horizon_prices_r91.run()
 daily=pd.read_parquet(cache/'forecast_v5/daily_industries.parquet');market=pd.read_parquet(cache/'forecast_v5/CSI_ALL.parquet').close
 context=pd.read_parquet(root/'data/r26_non_event_context.parquet');events=pd.read_parquet(root/'data/r26_industry_events.parquet');metrics=['pre20','pre60','reaction','post20','post60'];expected=[]
 dates=set(context.date)
 for _,g in daily.groupby(KEY+['block'],sort=False):
  g=g.sort_values('date').reset_index(drop=True);ci=market.index.get_indexer(g.date);assert (ci>=0).all() and (np.diff(ci)==1).all();ix=np.flatnonzero(g.date.isin(dates));q=g.iloc[ix][KEY+['date','block']].copy();nav=g.nav.to_numpy();bench=market.reindex(g.date).to_numpy()
  for metric,a,b in [('pre20',-21,-1),('pre60',-61,-1),('reaction',-1,0),('post20',1,21),('post60',1,61)]:
   valid=(ix+a>=0)&(ix+b<len(g));v=np.full(len(ix),np.nan);j=ix[valid];v[valid]=nav[j+b]/nav[j+a]-bench[j+b]/bench[j+a];q[metric]=v
  for field,offset in [('entry_date',1),('maturity20',21),('maturity60',61)]:
   v=np.full(len(ix),np.datetime64('NaT'),dtype='datetime64[ns]');valid=ix+offset<len(g);v[valid]=g.date.to_numpy()[ix[valid]+offset];q[field]=v
  expected.append(q)
 exp=pd.concat(expected,ignore_index=True);p=context.merge(exp,on=KEY+['date','block'],suffixes=('_actual','_expected'),validate='one_to_one');assert len(p)==len(context)==len(exp)
 for c in metrics:assert np.allclose(p[c+'_actual'],p[c+'_expected'],rtol=1e-10,atol=1e-12,equal_nan=True),c
 for c in ['entry_date','maturity20','maturity60']:assert (p[c+'_actual'].eq(p[c+'_expected'])|(p[c+'_actual'].isna()&p[c+'_expected'].isna())).all(),c
 eventkeys=set(map(tuple,events[KEY+['signal_date']].to_numpy()));assert context.is_event.tolist()==[tuple(x) in eventkeys for x in context[KEY+['date']].to_numpy()]
 for _,g in context.groupby(['era','level','date']):
  ready=g.pre20.notna();v=pd.Series(np.nan,index=g.index)
  if ready.sum()>=20:v.loc[ready]=np.ceil(g.loc[ready,'pre20'].rank(method='average',pct=True)*5)
  assert np.allclose(v,g.quintile,equal_nan=True)
 controls={k:g for k,g in context[~context.is_event&context.quintile.notna()].groupby(['era','level','date','quintile'])};checks=0
 for k,g in events.groupby(['era','level','signal_date','quintile'],dropna=False):
  ctr=controls.get(k)
  for c in metrics:
   val=ctr[c].mean() if ctr is not None and len(ctr)>=3 and ctr[c].notna().all() else np.nan
   assert np.allclose(g['control_'+c],val,equal_nan=True);assert np.allclose(g['matched_'+c],g[c]-val,equal_nan=True);checks+=len(g)
 summary=pd.read_csv(root/'outputs/r26/summary.csv');n=0
 for x in summary.to_dict('records'):
  g=events[(events.era==x['era'])&(events.level==x['level'])&(events.direction==x['direction'])];v=g[x['metric']];means=g.groupby('signal_date')[x['metric']].mean()
  for c,value in dict(event_rows=len(g),known=v.notna().sum(),unknown=v.isna().sum(),dates=g.signal_date.nunique(),known_dates=means.notna().sum(),industry_count=g.industry_code.nunique(),event_mean=v.mean(),date_mean=means.mean()).items():assert np.allclose(x[c],value,equal_nan=True), (c,x,value)
  n+=1
 conservative=pd.read_parquet(root/'data/r26_unknown_control_sensitivity.parquet');old14=pd.read_parquet(ROOT/'data/r14_industry_events.parquet');ek=KEY+['signal_date'];lost=set(map(tuple,old14[ek].to_numpy()))-set(map(tuple,events[ek].to_numpy()));available=context[~context.is_event&context.quintile.notna()].copy();available=available[[tuple(x) not in lost for x in available[KEY+['date']].to_numpy()]];cg={k:g for k,g in available.groupby(['era','level','date','quintile'])}
 for k,g in conservative.groupby(['era','level','signal_date','quintile'],dropna=False):
  ctr=cg.get(k)
  for c in metrics:
   val=ctr[c].mean() if ctr is not None and len(ctr)>=3 and ctr[c].notna().all() else np.nan
   assert np.allclose(g['control_'+c],val,equal_nan=True);assert np.allclose(g['matched_'+c],g[c]-val,equal_nan=True)
 comparisons=[]
 for rel,keys in [('outputs/r26/summary.csv',['era','level','direction','metric']),('outputs/r26/unknown_control_summary.csv',['era','level','direction','metric'])]:
  a=pd.read_csv(ROOT/rel);b=pd.read_csv(root/rel);pair=a.merge(b,on=keys,suffixes=('_old','_new'),validate='one_to_one');pair.to_csv(out/('comparison_'+Path(rel).name),index=False)
  for c in ['known','event_mean','date_mean']:
   x=pair[c+'_old'];y=pair[c+'_new'];comparisons.append(dict(source=rel,metric=c,changed=int((~np.isclose(x,y,equal_nan=True,atol=1e-12,rtol=1e-10)).sum()),sign_flips=int(((x*y)<0).sum()) if c!='known' else 0,max_abs=float((x-y).abs().max())))
 a=json.loads((ROOT/'outputs/r91/summary.json').read_text());b=json.loads((root/'outputs/r91/summary.json').read_text());assert a==b
 js(out/'impact.json',dict(comparisons=comparisons,horizon_summary_exactly_unchanged=True,quarantined_contexts=len(lost),conservative_events=len(conservative)))
 js(out/'verification.json',dict(status='PASS',context_rows=len(context),direct_context_windows=len(context)*5,matched_event_windows=checks,event_summaries=n,r91_verification_sha256=sha(root/'outputs/r91/verification.json'),summary_sha256=sha(out/'summary.json'),verifier_sha256=sha(__file__)))
 print('VERIFIED',len(context)*5,checks,n)
if __name__=='__main__':run()
