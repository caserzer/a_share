"""Isolated fixed L2 top10 replay, preserving original corrected top20 baseline."""
import shutil
import pandas as pd
from common import *
import portfolio_top10_engine_r169 as engine

def run():
 out=ROOT/'outputs/r169';root=out/'evaluation';cache=root/'cache/forecast_v5'
 for p in [cache,root/'outputs/r04',root/'data',root/'protocols']:p.mkdir(parents=True,exist_ok=True)
 dp=ROOT/'outputs/r129/daily_2026-10-21.parquet';mp=ROOT/'outputs/r130/monthly_panel.parquet';bp=CACHE/'forecast_v5/CSI_ALL.parquet'
 d=pd.read_parquet(dp);d=d[d.level.eq('L2')].copy();cal=pd.DatetimeIndex(pd.read_parquet(bp).index);d['day_i']=cal.get_indexer(d.date);assert d.day_i.ge(0).all();d.to_parquet(cache/'daily_industries.parquet',index=False)
 panel=pd.read_parquet(mp);panel[panel.level.eq('L2')].to_parquet(root/'data/monthly_panel.parquet',index=False)
 shutil.copyfile(bp,cache/'CSI_ALL.parquet');shutil.copyfile(ROOT/'protocols/r04.json',root/'protocols/r04.json');engine.ROOT=root;engine.CACHE=root/'cache';engine.run()
 old=pd.read_csv(ROOT/'outputs/r137/evaluation/outputs/r04/intervals.csv');old=old[old.level.eq('L2')];new=pd.read_csv(root/'outputs/r04/intervals.csv');keys=['era','level','method','origin'];pair=old.merge(new,on=keys,how='outer',suffixes=('_top20','_top10'),indicator=True,validate='one_to_one');assert pair._merge.eq('both').all();pair.to_csv(out/'interval_comparison.csv',index=False)
 equal=pair[pair.method.eq('equal')];assert equal.status_top20.eq(equal.status_top10).all()
 for col in ['selected','gross_return','turnover','net20','net50']:assert np.allclose(equal[col+'_top20'],equal[col+'_top10'],equal_nan=True)
 records=[]
 for (era,method),g in pair.groupby(['era','method']):
  q=g[g.status_top10.eq('valid')&g.status_top20.eq('valid')]
  rec=dict(era=era,method=method,scheduled=len(g),valid_top10=int(g.status_top10.eq('valid').sum()),valid_top20=int(g.status_top20.eq('valid').sum()),matched=len(q),changed_status=int(g.status_top10.ne(g.status_top20).sum()))
  for col in ['gross_return','net20','net50','turnover']:rec['mean_delta_'+col]=(q[col+'_top10']-q[col+'_top20']).mean()
  records.append(rec)
 pd.DataFrame(records).to_csv(out/'paired_summary.csv',index=False)
 reads=[dp,mp,bp,ROOT/'src/portfolio_r04.py',ROOT/'src/portfolio_top10_engine_r169.py',ROOT/'src/evaluate_r01.py',ROOT/'protocols/r169.json',ROOT/'protocols/r04.json',ROOT/'outputs/r137/evaluation/outputs/r04/intervals.csv',Path(__file__)]
 js(out/'summary.json',dict(reads={str(p):sha(p) for p in reads},intervals=len(new),equal_control_unchanged=True,adoption=False,quality='Historical-proxy L2 top10 simplified, not report replication'))
 print(pd.DataFrame(records).to_string(index=False))
if __name__=='__main__':run()
