"""Descriptive strata of frozen standalone observations, no new signal policy."""
import json,itertools
from pathlib import Path
import numpy as np
import pandas as pd
from audit_local_inputs import EP,PRIOR,CACHE,sha

def sign(v,prefix):return prefix+'_UNKNOWN' if pd.isna(v) else prefix+'_DOWN' if v<0 else prefix+'_UP' if v>0 else prefix+'_FLAT'
def quant(g,col,q):return None if g[col].dropna().empty else float(g[col].quantile(q))

def main():
 out=EP/'outputs/v2_s06_business_strata'
 if out.exists():raise FileExistsError('Preserve strata')
 out.mkdir();evalroot=EP/'outputs/evaluation_versions/s05_20261021';follow=EP/'outputs/followup_versions/s04_20261021/all_new_paths.parquet'
 parfile=EP/'outputs/r00_v2_path_probe03_symmetric_calendar_corrected/processes.parquet';rawfile=PRIOR/'daily_industries.parquet';marketfile=CACHE/'forecast_v5/CSI_ALL.parquet'
 rec=json.loads((PRIOR/'receipt.json').read_text());calfile=Path(next(k for k in rec['inputs'] if k.endswith('/calendar.parquet')))
 paths=[parfile,rawfile,marketfile,calfile,follow,EP/'protocols/v2_s06/plan.md',Path(__file__)]
 raw=pd.read_parquet(rawfile,columns=['date','day_i','era','industry_code','block','nav']);cal=pd.DatetimeIndex(pd.read_parquet(calfile).date)
 raw=raw.sort_values(['era','industry_code','day_i']);raw['calendar_week']=raw.date.dt.to_period('W-SUN')
 expected=pd.Series(cal).groupby(cal.to_period('W-SUN')).size()
 valid=raw[raw.nav.gt(0)&raw.block.notna()].copy();valid['lognav']=np.log(valid.nav)
 w=valid.groupby(['era','industry_code','block','calendar_week']).agg(y=('lognav','median'),days=('date','nunique')).reset_index()
 w['complete']=w.days.eq(w.calendar_week.map(expected));w=w[w.complete]
 wm=w.set_index(['era','industry_code','block','calendar_week']).y.to_dict()
 ps=pd.read_parquet(parfile);ps=ps[ps.status.eq('CONFIRMED')&~ps.left_context_unknown].copy();assert len(ps)==5759
 prior=[]
 for p in ps.itertuples():
  week=pd.Timestamp(p.start_date).to_period('W-SUN');vals=[wm.get((p.era,p.industry_code,p.block,week-j),np.nan) for j in range(9)]
  value=vals[0]-vals[8] if np.isfinite(vals).all() else np.nan
  prior.append(value)
 ps['prior8_log_change']=prior;ps['prior_state']=ps.prior8_log_change.map(lambda x:sign(x,'PRIOR8'))
 market=pd.read_parquet(marketfile).close.reindex(cal);mr=market/market.shift(60)-1
 def marketstate(d):
  v=pd.to_datetime(d).map(mr);return np.where(v.isna(),'MARKET_UNKNOWN',np.where(v>0,'MARKET_PRIOR60_POSITIVE','MARKET_PRIOR60_NONPOSITIVE'))
 ps['market_state']=marketstate(ps.start_date);ps['year']=pd.to_datetime(ps.start_date).dt.year;ps['visible_week']=pd.to_datetime(ps.visible_date).dt.to_period('W-SUN').astype(str)
 ps.to_parquet(out/'parent_strata.parquet',index=False)
 returns={}
 for key,g in raw.groupby(['era','industry_code']):
  good=g.nav.gt(0)&g.nav.shift().gt(0)&g.block.notna()&g.block.eq(g.block.shift())&g.day_i.diff().eq(1)
  returns[key]=pd.Series((g.nav/g.nav.shift()-1).where(good).values,index=g.date)
 fullfollow=pd.read_parquet(follow);parent_stats=[];newstats=[];pathstats=[];clusters=[];corrrows=[]
 for arm in ['A','B']:
  pcfile=evalroot/'runs'/arm/'parent_coverage.parquet';qfile=evalroot/'runs'/arm/'event_quality.parquet';evfile=EP/'outputs/v2_s01'/arm/'events.parquet';delivery=EP/'outputs/refresh/s02_chain_safe_v2_20261112/delivery'/arm/'all_observations.parquet'
  paths += [pcfile,qfile,evfile,delivery]
  pc=pd.read_parquet(pcfile).merge(ps[['process_id','prior_state','market_state','year','visible_week']],on='process_id',validate='one_to_one')
  for dims in [['prior_state'],['market_state'],['era','year'],['prior_state','market_state']]:
   for keys,g in pc.groupby(dims,dropna=False):
    keys=keys if isinstance(keys,tuple) else (keys,);hit=g[g.covered]
    parent_stats.append(dict(arm=arm,stratification='|'.join(dims),stratum='|'.join(map(str,keys)),processes=len(g),covered=int(g.covered.sum()),missed=int((~g.covered).sum()),timely=int(g.timing.eq('TIMELY').sum()),late=int(g.timing.eq('LATE').sum()),coverage=float(g.covered.mean()),new_source=int(g.source.eq('NEW').sum()),update_source=int(g.source.eq('UPDATE').sum()),lag_p50=quant(hit,'lag_days',.5),lag_p90=quant(hit,'lag_days',.9),pre_gain_p50=quant(hit,'pre_gain',.5),pre_gain_p90=quant(hit,'pre_gain',.9)))
  for week,g in pc.groupby('visible_week'):
   clusters.append(dict(arm=arm,visible_week=week,processes=len(g),covered=int(g.covered.sum()),timely=int(g.timing.eq('TIMELY').sum())))
  ev=pd.read_parquet(evfile);ev=ev[ev.kind.eq('NEW')].copy();q=pd.read_parquet(qfile);q=q[q.kind.eq('NEW')]
  z=ev[['event_id','date','era','industry_code']].merge(q[['event_id','status']],on='event_id',validate='one_to_one')
  # 40-day context recomputed from daily valid chains; no process-label assignment of alert strata.
  rawidx=raw.set_index(['era','industry_code','date']);r40=[]
  for r in z.itertuples():
   row=rawidx.loc[(r.era,r.industry_code,r.date)];j=cal.get_loc(r.date);past=rawidx.loc[(r.era,r.industry_code,cal[j-40])] if j>=40 and (r.era,r.industry_code,cal[j-40]) in rawidx.index else None
   r40.append(row.nav/past.nav-1 if past is not None and row.nav>0 and past.nav>0 and row.block==past.block else np.nan)
  z['prior40_return']=r40;z['alert_prior_state']=z.prior40_return.map(lambda x:sign(x,'ALERT40'));z['market_state']=marketstate(z.date);z['year']=z.date.dt.year
  z.to_parquet(out/f'{arm}_new_strata.parquet',index=False)
  f=fullfollow[fullfollow.arm.eq(arm)&fullfollow.horizon.isin([20,60])].merge(z[['event_id','market_state','alert_prior_state','year']],on='event_id',validate='many_to_one')
  for dims in [['market_state'],['alert_prior_state'],['era','year']]:
   for keys,g in z.groupby(dims,dropna=False):
    keys=keys if isinstance(keys,tuple) else (keys,);unknown=g.status.str.contains('UNKNOWN');effective=g.status.eq('COVERED');known=int((~unknown).sum())
    newstats.append(dict(arm=arm,stratification='|'.join(dims),stratum='|'.join(map(str,keys)),new=len(g),unknown=int(unknown.sum()),evaluable=known,effective=int(effective.sum()),effectiveness=float(effective.sum()/known) if known else None,repeat=int(g.status.eq('REPEAT').sum())))
   for keys,g in f.groupby(['horizon']+dims,dropna=False):
    h,*rest=keys;m=g[g.status.eq('MATURE')]
    pathstats.append(dict(arm=arm,horizon=int(h),stratification='|'.join(dims),stratum='|'.join(map(str,rest)),new=len(g),mature=len(m),immature=int(g.status.eq('IMMATURE').sum()),gap=int(g.status.eq('DATA_OR_CLASSIFICATION_GAP').sum()),positive=int(m.absolute_return.gt(0).sum()),positive_fraction=float(m.absolute_return.gt(0).mean()),return_p50=quant(m,'absolute_return',.5),drawdown_p50=quant(m,'max_drawdown',.5),relative_known=int(m.relative_return.notna().sum()),relative_p50=quant(m,'relative_return',.5)))
  for date,g in ev.groupby('date'):
   j=cal.get_loc(date);dates=cal[max(0,j-59):j+1];pairs=[];unknown=0
   for a,b in itertools.combinations(g.itertuples(),2):
    x=returns[(a.era,a.industry_code)].reindex(dates);y=returns[(b.era,b.industry_code)].reindex(dates);good=x.notna()&y.notna()
    corr=x[good].corr(y[good]) if good.sum()>=40 else np.nan
    if pd.isna(corr):unknown+=1
    else:pairs.append(float(corr))
   corrrows.append(dict(arm=arm,date=date,new=len(g),possible_pairs=len(g)*(len(g)-1)//2,known_pairs=len(pairs),unknown_pairs=unknown,mean_correlation=float(np.mean(pairs)) if pairs else None))
 pd.DataFrame(parent_stats).to_csv(out/'parent_strata_summary.csv',index=False);pd.DataFrame(newstats).to_csv(out/'new_strata_summary.csv',index=False);pd.DataFrame(pathstats).to_csv(out/'followup_strata_summary.csv',index=False);pd.DataFrame(clusters).to_csv(out/'process_week_clusters.csv',index=False);pd.DataFrame(corrrows).to_csv(out/'new_week_correlations.csv',index=False)
 for arm in ['A','B']:
  a=pd.DataFrame(parent_stats);a=a[a.arm.eq(arm)];assert (a.groupby('stratification').processes.sum()==5759).all()
  b=pd.DataFrame(newstats);b=b[b.arm.eq(arm)];assert (b.groupby('stratification').new.sum()==(1459 if arm=='A' else 1451)).all()
 summary=dict(parent_prior_state=ps.prior_state.value_counts().to_dict(),parent_market=ps.market_state.value_counts().to_dict(),limits=['descriptive strata do not change labels or imply causal selection skill','prior-state parent boundary is retrospective; not a signal input','same-week pair correlations are not independent observations'])
 (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(out/'receipt.json').write_text(json.dumps(dict(inputs={str(x):sha(x) for x in paths},artifacts={x.name:sha(x) for x in out.iterdir() if x.is_file()}),indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
