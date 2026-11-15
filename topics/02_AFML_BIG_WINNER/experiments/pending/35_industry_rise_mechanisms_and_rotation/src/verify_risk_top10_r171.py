"""Independent weighted-return risk, scalar path drift and output coverage checks."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r171';receipt=json.loads((out/'receipt.json').read_text())
 for p,h in receipt['reads'].items():assert sha(p)==h
 cal=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index);d=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet');d=d[d.level.eq('L2')];lookup={k:(g.set_index('date').reindex(cal).nav.to_numpy(),g.set_index('date').reindex(cal).block.to_numpy()) for k,g in d.groupby(KEY)}
 roots={'top10':ROOT/'outputs/r169/evaluation/outputs/r04','top20':ROOT/'outputs/r137/evaluation/outputs/r04'};hold={};intervals={};daily={}
 for v,p in roots.items():
  h=pd.read_parquet(p/'holdings.parquet');hold[v]={k:g for k,g in h[h.level.eq('L2')].groupby(['era','level','method','origin'])};intervals[v]=pd.read_csv(p/'intervals.csv',parse_dates=['origin','entry','exit']).set_index(['era','level','method','origin']);daily[v]=pd.read_parquet(p/'daily_returns.parquet')
 risk=pd.read_csv(out/'risk_by_origin.csv',parse_dates=['origin']);seen=set()
 for row in risk.to_dict('records'):
  v=row['variant'];key=(row['era'],row['level'],row['method'],row['origin']);seen.add((v,*key));h=hold[v][key];codes=h.industry_code.tolist();w=h.weight.to_numpy();ix=cal.get_loc(row['origin']);positions=list(range(max(0,ix-62),ix+1));vals=[];excluded=0
  for j in positions:
   line=[]
   for code in codes:
    prices,blocks=lookup[(row['era'],row['level'],code)];ret=prices[j]/prices[j-1]-1 if j>0 else np.nan;ok=j>0 and blocks[j]==blocks[ix] and blocks[j-1]==blocks[ix]
    if np.isfinite(ret) and not ok:excluded+=1
    line.append(ret if ok else np.nan)
   if np.isfinite(line).all():vals.append(line)
  assert row['prior_observations']==len(vals) and row['origin_block_exclusions']==excluded and row['selected']==len(codes)
  assert np.isclose(row['target_hhi'],sum(x*x for x in w))
  if len(vals)<42:assert pd.isna(row['prior_vol']) and pd.isna(row['prior_mean_correlation'])
  else:
   a=np.asarray(vals);portfolio=a@w;corr=np.corrcoef(a,rowvar=False);off=[corr[i,j] for i in range(len(codes)) for j in range(i+1,len(codes))]
   assert np.isclose(row['prior_vol'],np.std(portfolio,ddof=1)*np.sqrt(252),atol=1e-12);assert np.isclose(row['prior_mean_correlation'],np.mean(off),equal_nan=True,atol=1e-12)
  rec=intervals[v].loc[key];assert row['interval_status']==rec.status
  if rec.status=='valid':
   start=cal.get_loc(rec.entry);end=cal.get_loc(rec.exit);maxweight=0;maxhhi=0
   for j in range(start,end+1):
    amounts=[weight*lookup[(row['era'],row['level'],code)][0][j]/lookup[(row['era'],row['level'],code)][0][start] for code,weight in zip(codes,w)];weights=np.asarray(amounts)/sum(amounts);maxweight=max(maxweight,max(weights));maxhhi=max(maxhhi,sum(weights**2))
   assert np.isclose(row['max_drifted_industry_weight'],maxweight) and np.isclose(row['max_drifted_hhi'],maxhhi)
  else:assert pd.isna(row['max_drifted_industry_weight']) and pd.isna(row['max_drifted_hhi'])
 assert seen=={(v,*k) for v in hold for k in hold[v]}
 annual=pd.read_csv(out/'annual.csv');tails=pd.read_csv(out/'tail_risk.csv');expectedtails=set();expectedannual=set()
 for v,df in daily.items():
  for (era,level,method),g in df[df.level.eq('L2')].groupby(['era','level','method']):
   if not g.whole_path_valid.all():continue
   for cost in ['gross','net20','net50']:
    key=(v,era,method,cost);expectedtails.add(key);a=tails[tails.variant.eq(v)&tails.era.eq(era)&tails.method.eq(method)&tails.cost.eq(cost)].iloc[0];arr=g[cost].to_numpy();q=np.quantile(arr,.05)
    for name,value in [('days',len(g)),('daily_q05',q),('daily_bottom5_mean',np.mean(arr[arr<=q])),('min_day',min(arr)),('negative_market_days',g.benchmark.lt(0).sum()),('mean_on_negative_market_days',g.loc[g.benchmark.lt(0),cost].mean())]:assert np.isclose(a[name],value,equal_nan=True)
    for year,z in g.groupby(g.date.dt.year):
     expectedannual.add((*key,year));a=annual[annual.variant.eq(v)&annual.era.eq(era)&annual.method.eq(method)&annual.cost.eq(cost)&annual.year.eq(year)].iloc[0];assert a.days==len(z);assert np.isclose(a.return_value,np.prod(1+z[cost])-1) and np.isclose(a.market_return,np.prod(1+z.benchmark)-1)
 assert expectedtails==set(tails[['variant','era','method','cost']].itertuples(index=False,name=None));assert expectedannual==set(annual[['variant','era','method','cost','year']].itertuples(index=False,name=None))
 pairs=risk[risk.variant.eq('top10')].merge(risk[risk.variant.eq('top20')],on=['era','level','method','origin'],suffixes=('_top10','_top20'),validate='one_to_one')
 for row in pd.read_csv(out/'paired_summary.csv').to_dict('records'):
  g=pairs[pairs.era.eq(row['era'])&pairs.method.eq(row['method'])];metric=row['metric'];q=g.dropna(subset=[metric+'_top10',metric+'_top20']);assert row['origins']==len(g) and row['paired_known']==len(q) and row['unknown_pairs']==len(g)-len(q)
  for name,value in [('top10_mean',q[metric+'_top10'].mean()),('top20_mean',q[metric+'_top20'].mean()),('delta',(q[metric+'_top10']-q[metric+'_top20']).mean())]:assert np.isclose(row[name],value,equal_nan=True)
 js(out/'verification.json',dict(status='PASS',risk_rows=len(risk),annual_rows=len(annual),tail_rows=len(tails),independent_weighted_return_volatility=True,origin_block_isolation=True,adoption=False))
 print('PASS R171',len(risk),len(annual),len(tails))
if __name__=='__main__':run()
