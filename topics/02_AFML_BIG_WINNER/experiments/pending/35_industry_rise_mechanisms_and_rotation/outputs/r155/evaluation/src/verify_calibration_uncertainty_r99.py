import statistics
import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r99';rec=json.loads((out/'receipt.json').read_text())
 for p,h in rec['reads'].items():assert sha(p)==h,p
 p=pd.read_parquet(ROOT/'outputs/r97/predictions.parquet');calendar=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index).sort_values();dates=json.loads((out/'date_differences.json').read_text());lookup={k:g for k,g in p[p.y.notna()].groupby(['era','level','year','date'])};assert len(dates)==len(lookup);blocks={}
 for r in dates:
  key=r['era'],r['level'],r['year'],pd.Timestamp(r['date']);g=lookup[key];errors=[(x.daily_probability-x.y)**2-(x.monthly_probability-x.y)**2 for x in g.itertuples()];assert r['rows']==len(errors) and np.isclose(r['difference'],statistics.mean(errors),atol=1e-14);cal=calendar[calendar.year==r['year']];i=list(cal).index(pd.Timestamp(r['date']));assert r['session_index']==i and r['block']==i//21;blocks.setdefault(key[:3]+(r['block'],),[]).append(r['difference'])
 summaries=json.loads((out/'summary.json').read_text());ledger=json.loads((out/'calendar_blocks.json').read_text());assert len(summaries)==8 and len(ledger)==sum((len(calendar[calendar.year==s['year']])+20)//21 for s in summaries)
 for r in ledger:
  key=r['era'],r['level'],r['year'],r['block'];cal=calendar[calendar.year==r['year']];assert pd.Timestamp(r['calendar_start'])==cal[r['block']*21] and pd.Timestamp(r['calendar_end'])==cal[min((r['block']+1)*21,len(cal))-1];v=blocks.get(key,[]);assert r['observed_dates']==len(v);assert (not v and r['total'] is None) or np.isclose(r['total'],sum(v),atol=1e-14)
 draws=pd.read_parquet(out/'resamples.parquet');assert len(draws)==8*20000
 for s in summaries:
  key=s['era'],s['level'],s['year'];bb=sorted((k[-1],v) for k,v in blocks.items() if k[:3]==key);totals=[sum(v) for _,v in bb];counts=[len(v) for _,v in bb];point=sum(totals)/sum(counts);assert s['observed_blocks']==len(bb) and s['dates']==sum(counts) and s['minimum_dates_per_block']==min(counts) and s['maximum_dates_per_block']==max(counts);assert s['calendar_sessions']==len(calendar[calendar.year==s['year']]) and s['missing_dates']==s['calendar_sessions']-sum(counts);assert np.isclose(s['point'],point,atol=1e-14) and s['status']=='evaluated' and len(bb)>=8
  rng=np.random.default_rng(35099);sim=[]
  for _ in range(20000):
   ids=rng.integers(0,len(bb),size=len(bb));sim.append(sum(totals[i] for i in ids)/sum(counts[i] for i in ids))
  saved=draws[draws.era.eq(s['era'])&draws.level.eq(s['level'])&draws.year.eq(s['year'])].sort_values('replicate');assert list(saved.replicate)==list(range(20000)) and np.allclose(saved.difference,sim,rtol=1e-12,atol=1e-14)
  for k,q in [('low95',.025),('high95',.975),('low_family',.05/16),('high_family',1-.05/16)]:assert np.isclose(s[k],np.quantile(sim,q),atol=1e-14)
 js(out/'verification.json',dict(status='PASS',folds=8,date_rows=len(dates),calendar_blocks=len(ledger),resamples=len(draws),scope='all original paired row losses, daily means, actual exchange-calendar blocks including missing dates, independent per-replicate resampling and all interval quantiles',verifier_sha256=sha(Path(__file__))));print('R99 VERIFIED',len(dates),len(ledger),len(draws))
if __name__=='__main__':run()
