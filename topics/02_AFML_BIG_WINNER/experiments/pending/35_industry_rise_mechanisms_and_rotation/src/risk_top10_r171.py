"""Frozen L2 risk diagnostics with explicit origin-block history."""
import pandas as pd
from common import *

def run():
 out=ROOT/'outputs/r171';dp=ROOT/'outputs/r129/daily_2026-10-21.parquet';bp=CACHE/'forecast_v5/CSI_ALL.parquet';cal=pd.DatetimeIndex(pd.read_parquet(bp).index)
 d=pd.read_parquet(dp);d=d[d.level.eq('L2')];lookup={key:g.set_index('date').reindex(cal) for key,g in d.groupby(KEY)}
 roots={'top10':ROOT/'outputs/r169/evaluation/outputs/r04','top20':ROOT/'outputs/r137/evaluation/outputs/r04'};reads=[dp,bp,ROOT/'protocols/r171.json',ROOT/'protocols/r17.json',Path(__file__)];risk=[];annual=[];tails=[]
 for variant,root in roots.items():
  hp=root/'holdings.parquet';ip=root/'intervals.csv';pp=root/'daily_returns.parquet';reads += [hp,ip,pp]
  hold=pd.read_parquet(hp);hold=hold[hold.level.eq('L2')];intervals=pd.read_csv(ip,parse_dates=['origin','entry','exit']).set_index(['era','level','method','origin'])
  for key,h in hold.groupby(['era','level','method','origin']):
   era,level,method,origin=key;codes=h.industry_code.tolist();w=h.set_index('industry_code').weight.reindex(codes).to_numpy();vectors=[];reset_excluded=0
   days=cal[max(0,cal.get_loc(origin)-62):cal.get_loc(origin)+1]
   for code in codes:
    g=lookup[(era,level,code)];current=g.loc[origin,'block'];ret=g.nav/g.nav.shift(1)-1;valid=g.block.eq(current)&g.block.shift(1).eq(current);reset_excluded+=int((ret.loc[days].notna()&~valid.loc[days]).sum());vectors.append(ret.where(valid).loc[days].rename(code))
   past=pd.concat(vectors,axis=1).dropna();n=len(past);rec=intervals.loc[key]
   row=dict(variant=variant,era=era,level=level,method=method,origin=origin,selected=len(codes),target_hhi=float(w@w),prior_observations=n,origin_block_exclusions=reset_excluded,prior_vol=np.nan,prior_mean_correlation=np.nan,interval_status=rec.status,max_drifted_industry_weight=np.nan,max_drifted_hhi=np.nan)
   if n>=42:
    corr=past.corr().to_numpy();row.update(prior_vol=np.sqrt(w@past.cov().to_numpy()@w*252),prior_mean_correlation=np.mean(corr[np.triu_indices(len(codes),1)]))
   if rec.status=='valid':
    dates=cal[(cal>=rec.entry)&(cal<=rec.exit)];values=[]
    for code in codes:
     g=lookup[(era,level,code)].loc[dates];assert g.nav.notna().all() and g.block.nunique()==1;values.append(g.nav.to_numpy()/g.nav.iloc[0])
    value=np.column_stack(values)*w;drift=value/value.sum(axis=1)[:,None];row.update(max_drifted_industry_weight=drift.max(),max_drifted_hhi=(drift**2).sum(axis=1).max())
   risk.append(row)
  daily=pd.read_parquet(pp);daily=daily[daily.level.eq('L2')]
  for (era,method),g in daily.groupby(['era','method']):
   if not g.whole_path_valid.all():continue
   for cost in ['gross','net20','net50']:
    q=g[cost].quantile(.05);tails.append(dict(variant=variant,era=era,method=method,cost=cost,days=len(g),start=g.date.min(),end=g.date.max(),daily_q05=q,daily_bottom5_mean=g.loc[g[cost].le(q),cost].mean(),min_day=g[cost].min(),negative_market_days=int(g.benchmark.lt(0).sum()),mean_on_negative_market_days=g.loc[g.benchmark.lt(0),cost].mean()))
    for year,v in g.groupby(g.date.dt.year):annual.append(dict(variant=variant,era=era,method=method,cost=cost,year=year,days=len(v),start=v.date.min(),end=v.date.max(),return_value=(1+v[cost]).prod()-1,market_return=(1+v.benchmark).prod()-1))
 risk=pd.DataFrame(risk);risk.to_csv(out/'risk_by_origin.csv',index=False);pd.DataFrame(annual).to_csv(out/'annual.csv',index=False);pd.DataFrame(tails).to_csv(out/'tail_risk.csv',index=False)
 keys=['era','level','method','origin'];pair=risk[risk.variant.eq('top10')].merge(risk[risk.variant.eq('top20')],on=keys,how='outer',suffixes=('_top10','_top20'),indicator=True,validate='one_to_one');assert pair._merge.eq('both').all();pair.to_csv(out/'risk_pairs.csv',index=False);summary=[]
 for (era,method),g in pair.groupby(['era','method']):
  for metric in ['target_hhi','prior_vol','prior_mean_correlation','max_drifted_industry_weight','max_drifted_hhi']:
   q=g.dropna(subset=[metric+'_top10',metric+'_top20']);summary.append(dict(era=era,method=method,metric=metric,origins=len(g),paired_known=len(q),unknown_pairs=len(g)-len(q),top10_mean=q[metric+'_top10'].mean(),top20_mean=q[metric+'_top20'].mean(),delta=(q[metric+'_top10']-q[metric+'_top20']).mean()))
 pd.DataFrame(summary).to_csv(out/'paired_summary.csv',index=False);js(out/'receipt.json',dict(status='PASS',reads={str(p):sha(p) for p in reads},risk_rows=len(risk),annual_rows=len(annual),tail_rows=len(tails),adoption=False))
 print('R171',len(risk),len(annual),len(tails))
if __name__=='__main__':run()
