from common import *
import pandas as pd

def run():
 out=ROOT/'outputs/r296';p=pd.read_parquet(ROOT/'outputs/r295/predictions.parquet');d=pd.read_parquet(out/'date_differences.parquet');b=pd.read_parquet(out/'calendar_blocks.parquet');s=pd.read_csv(out/'summary.csv');samples=pd.read_parquet(out/'resamples.parquet');cal=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index.sort_values();maxerr=0.;daychecks=0
 for row in s.itertuples():
  mask=lambda f:f.era.eq(row.era)&f.level.eq(row.level)&f.year.eq(row.year)
  g=p[mask(p)];lhs=row.comparison.split('_daily')[0];a=g[g.variant.eq(lhs)].set_index(KEY+['date']);method='monthly_probability' if row.comparison.endswith('-monthly') else 'daily_probability';rhs=lhs if method=='monthly_probability' else 'base';bb=g[g.variant.eq(rhs)].set_index(KEY+['date']);pd.testing.assert_series_equal(a.y.sort_index(),bb.y.sort_index())
  loss=(a.daily_probability-a.y)**2-(bb[method]-bb.y)**2
  expected=loss.dropna().groupby('date').mean().sort_index();dd=d[mask(d)&d.comparison.eq(row.comparison)].set_index('date').sort_index();assert list(expected.index)==list(dd.index) and np.allclose(expected,dd.difference,atol=1e-14);daychecks+=len(dd)
  yearcal=cal[cal.year==row.year];positions=yearcal.get_indexer(dd.index);assert np.array_equal(positions,dd.session_index) and np.array_equal(positions//21,dd.block)
  blocks=b[mask(b)&b.comparison.eq(row.comparison)].sort_values('block');assert len(blocks)==(len(yearcal)+20)//21
  totals=[];counts=[]
  for x in blocks.itertuples():
   valid=expected[(positions>=x.block*21)&(positions<(x.block+1)*21)];assert len(valid)==x.dates
   assert x.start==yearcal[x.block*21] and x.end==yearcal[min((x.block+1)*21,len(yearcal))-1]
   if len(valid):assert np.isclose(valid.sum(),x.total);totals.append(valid.sum());counts.append(len(valid))
   else:assert pd.isna(x.total)
  assert len(totals)==row.observed_blocks and np.isclose(expected.mean(),row.point)
  if len(totals)<8:assert row.status=='insufficient_blocks';continue
  rng=np.random.default_rng(35099);indices=rng.integers(0,len(totals),size=(20000,len(totals)))
  multiplicities=np.array([np.bincount(ix,minlength=len(totals)) for ix in indices]);sim=(multiplicities@np.array(totals))/(multiplicities@np.array(counts));stored=samples[mask(samples)&samples.comparison.eq(row.comparison)].sort_values('replicate').difference.to_numpy();err=float(np.max(np.abs(sim-stored)));maxerr=max(maxerr,err);assert err<1e-12
  qs=np.quantile(sim,[.025,.975,.05/70,1-.05/70]);assert np.allclose(qs,[row.low95,row.high95,row.low_family,row.high_family],atol=1e-12)
  finding='lower_error' if qs[3]<0 else 'higher_error' if qs[2]>0 else 'uncertain';assert finding==row.finding
 assert len(s)==35
 js(out/'independent_verification.json',dict(status='PASS',comparisons=len(s),daily_checks=daychecks,resample_checks=len(samples),max_resample_error=maxerr,scope='Source loss, calendar blocks, count-matrix resampling and quantiles; not exact finite-sample coverage or forward certification',adoption=False))
 print('VERIFIED',len(s),daychecks,len(samples),maxerr)
if __name__=='__main__':run()
