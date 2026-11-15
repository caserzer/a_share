"""Original R04 replay with repaired inputs in isolated roots."""
import shutil
import pandas as pd
from common import *
import portfolio_r04

def run():
 out=ROOT/'outputs/r137';sandbox=out/'evaluation';cache=sandbox/'cache/forecast_v5';cache.mkdir(parents=True,exist_ok=True);(sandbox/'outputs/r04').mkdir(parents=True,exist_ok=True);(sandbox/'data').mkdir(exist_ok=True);(sandbox/'protocols').mkdir(exist_ok=True)
 dp=ROOT/'outputs/r129/daily_2026-10-21.parquet';mp=ROOT/'outputs/r130/monthly_panel.parquet';bp=CACHE/'forecast_v5/CSI_ALL.parquet';d=pd.read_parquet(dp);calendar=pd.DatetimeIndex(pd.read_parquet(bp).index);positions=calendar.get_indexer(d.date);assert (positions>=0).all();d['day_i']=positions;d.to_parquet(cache/'daily_industries.parquet',index=False)
 shutil.copyfile(bp,cache/'CSI_ALL.parquet');shutil.copyfile(mp,sandbox/'data/monthly_panel.parquet');shutil.copyfile(ROOT/'protocols/r04.json',sandbox/'protocols/r04.json');portfolio_r04.ROOT=sandbox;portfolio_r04.CACHE=sandbox/'cache';portfolio_r04.run()
 keys=['era','level','method','origin'];old=pd.read_csv(ROOT/'outputs/r04/intervals.csv');new=pd.read_csv(sandbox/'outputs/r04/intervals.csv');pair=old.merge(new,on=keys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');pair.to_csv(out/'interval_comparison.csv',index=False)
 hkeys=keys+['industry_code'];a=pd.read_parquet(ROOT/'outputs/r04/holdings.parquet');b=pd.read_parquet(sandbox/'outputs/r04/holdings.parquet');hp=a.merge(b,on=hkeys,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');hp.to_parquet(out/'holding_comparison.parquet',index=False)
 sk=['era','level','method','cost'];a=pd.read_csv(ROOT/'outputs/r04/summary.csv');b=pd.read_csv(sandbox/'outputs/r04/summary.csv');sp=a.merge(b,on=sk,how='outer',suffixes=('_old','_new'),indicator=True,validate='one_to_one');sp.to_csv(out/'summary_comparison.csv',index=False)
 shared=pair[pair._merge.eq('both')];changed=shared.status_old.ne(shared.status_new);hc=hp[hp._merge.eq('both')];sc=sp[sp._merge.eq('both')]
 reads=[dp,mp,bp,ROOT/'protocols/r04.json',ROOT/'protocols/r137.json',ROOT/'src/portfolio_r04.py',ROOT/'src/evaluate_r01.py',Path(__file__)]
 js(out/'summary.json',dict(reads={str(p):sha(p) for p in reads},daily_rows=len(d),intervals_old=len(old),intervals_new=len(new),interval_status_changes=int(changed.sum()),new_intervals=int(pair._merge.eq('right_only').sum()),removed_intervals=int(pair._merge.eq('left_only').sum()),holding_added=int(hp._merge.eq('right_only').sum()),holding_removed=int(hp._merge.eq('left_only').sum()),holding_weight_changes=int((hc.weight_old-hc.weight_new).abs().gt(1e-12).sum()),whole_path_changes=int(sc.whole_path_valid_old.ne(sc.whole_path_valid_new).sum()),complete_strategy_cost_rows_old=int(a.whole_path_valid.sum()),complete_strategy_cost_rows_new=int(b.whole_path_valid.sum()),quality='Historical-proxy synthetic baskets; no fills or production adoption'))
 print('PORTFOLIO REPLAY',len(new),'status changes',int(changed.sum()),flush=True)
if __name__=='__main__':run()
