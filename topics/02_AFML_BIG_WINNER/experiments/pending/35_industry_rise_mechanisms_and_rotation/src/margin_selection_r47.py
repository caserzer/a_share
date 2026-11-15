"""Describe coverage selection on same dates, without outcome-based matching."""
import pandas as pd
from common import *
from train_r02 import F

def run():
 out=ROOT/'outputs/r47';cols=KEY+['date','price_ready','members']+F[:-1]
 p=pd.concat([pd.read_parquet(ROOT/'data/monthly_panel.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet',columns=cols)]);p['log_members']=np.log(p.members)
 p=p.merge(pd.read_parquet(ROOT/'data/r30_size_control.parquet',columns=KEY+['date','size_control']),on=KEY+['date'],how='left',validate='one_to_one')
 coverage=pd.read_parquet(ROOT/'data/r45_financing_intensity.parquet',columns=KEY+['date','financing_intensity'])
 p=p[p.price_ready&p[F+['size_control']].notna().all(axis=1)&p.date.isin(coverage.date.unique())].merge(coverage,on=KEY+['date'],how='left',validate='one_to_one');p['selected']=p.financing_intensity.notna()
 p['size_percentile']=p.groupby(['era','level','date']).size_control.rank(pct=True);rows=[]
 for key,g in p.groupby(['era','level','date']):
  a=g[g.selected];b=g[~g.selected]
  if a.empty or b.empty:continue
  rows.append(dict(zip(['era','level','date'],key),selected=len(a),other=len(b),selected_mean_size_rank=float(a.size_percentile.mean()),other_mean_size_rank=float(b.size_percentile.mean()),size_rank_gap=float(a.size_percentile.mean()-b.size_percentile.mean())))
 z=pd.DataFrame(rows);z.to_parquet(out/'selection_by_date.parquet',index=False);summary=z.groupby(['era','level']).agg(dates=('date','size'),selected_mean_size_rank=('selected_mean_size_rank','mean'),other_mean_size_rank=('other_mean_size_rank','mean'),mean_rank_gap=('size_rank_gap','mean')).reset_index();js(out/'selection_summary.json',summary.to_dict('records'))
 paths=[ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'data/r30_size_control.parquet',ROOT/'data/r45_financing_intensity.parquet',ROOT/'protocols/r47.json',Path(__file__)]
 js(out/'selection_receipt.json',dict(inputs={str(x):sha(x) for x in paths},base_rows=len(p),selected_rows=int(p.selected.sum()),paired_dates=len(z),outcomes_read=False,meaning='same-date descriptive size selection, not corrected selection bias or causal estimate'))
 print(summary.to_string(index=False))

if __name__=='__main__':run()
