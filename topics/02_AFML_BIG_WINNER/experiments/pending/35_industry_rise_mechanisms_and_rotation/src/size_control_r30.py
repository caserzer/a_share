"""Construct local size control without accessing future returns."""
import pandas as pd
from common import *
from train_r02 import F

def run():
 out=ROOT/'outputs/r30';out.mkdir(exist_ok=True)
 paths=[CACHE/'extension_v2/products/panel.parquet',CACHE/'extension_v2/products/assignments.parquet',ROOT/'data/l1_assignments.parquet',ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'protocols/r30.json',Path(__file__),EP32/'extensions/v2_full_history_benchmark/src/core.py',EP32/'src/observe.py']
 stocks=pd.read_parquet(paths[0],columns=['date','security_id','raw_close','total_shares','share_effective_date','cap','listed'])
 assert not stocks.duplicated(['date','security_id']).any()
 assert np.allclose(stocks.cap,stocks.raw_close*stocks.total_shares,equal_nan=True)
 known=stocks.cap.notna();assert stocks.loc[known,'share_effective_date'].notna().all() and stocks.loc[known,'share_effective_date'].le(stocks.loc[known,'date']).all()
 valid=stocks.listed&stocks.cap.gt(0)&np.isfinite(stocks.cap)&stocks.raw_close.gt(0)&stocks.total_shares.gt(0)
 stocks['log_cap']=np.log(stocks.cap.where(valid));stocks=stocks[['date','security_id','log_cap']]
 cols=['month']+KEY+['security_id'];members=pd.concat([pd.read_parquet(x,columns=cols) for x in paths[1:3]],ignore_index=True)
 assert not members.duplicated(['month']+KEY+['security_id']).any()
 signal_cols=KEY+['date','members','price_ready']+F[:-1]+['breadth21','breadth63']
 panel=pd.concat([pd.read_parquet(x,columns=signal_cols) for x in paths[3:5]],ignore_index=True);panel['log_members']=np.log(panel.members)
 rows=[]
 for date in sorted(panel.date.unique()):
  date=pd.Timestamp(date);m=members[members.month.eq(date.to_period('M')-1)];z=m.merge(stocks[stocks.date.eq(date)],on='security_id',how='left',validate='many_to_one')
  q=z.groupby(KEY).agg(size_members=('security_id','size'),size_known=('log_cap','count'),size_median_log_cap=('log_cap','median')).reset_index();q['date']=date;q['membership_month']=date.to_period('M')-1
  q['size_coverage']=q.size_known/q.size_members;q['size_ready']=q.size_known.ge(5)&q.size_coverage.ge(.8);q['size_control']=q.size_median_log_cap.where(q.size_ready);rows.append(q)
 features=pd.concat(rows,ignore_index=True);dest=ROOT/'data/r30_size_control.parquet';features.to_parquet(dest,index=False)
 joined=panel.merge(features,on=KEY+['date'],how='left',validate='one_to_one');joined['price_complete']=joined.price_ready&joined[F].notna().all(axis=1);joined['diffusion_complete']=joined.price_complete&joined[['breadth21','breadth63']].notna().all(axis=1);joined['matched_size_diffusion']=joined.diffusion_complete&joined.size_control.notna()
 summary=joined.groupby(['era','level']).agg(panel_rows=('date','size'),price_complete=('price_complete','sum'),diffusion_complete=('diffusion_complete','sum'),matched_size_diffusion=('matched_size_diffusion','sum'),size_complete=('size_control','count')).reset_index();summary.to_csv(out/'coverage.csv',index=False)
 joined.groupby(['era','level',joined.date.dt.year]).agg(rows=('date','size'),matched=('matched_size_diffusion','sum')).to_csv(out/'annual_coverage.csv')
 js(out/'receipt.json',dict(reads={str(p):sha(p) for p in paths},feature_sha256=sha(dest),rows=len(features),stock_rows=len(stocks),stock_valid=int(valid.sum()),quality='Historical-proxy; no share known_at; not full style controls',no_outcomes_read=True))
 print(summary.to_string(index=False),flush=True)
if __name__=='__main__':run()
