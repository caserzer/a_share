"""Market exposure controls built without outcome columns."""
import pandas as pd
from common import *
from train_r02 import F

def features(g, market):
 g=g.sort_values('date').copy();calendar=market.index;pos=pd.Series(np.arange(len(calendar)),index=calendar);p=g.date.map(pos)
 consecutive=p.diff().eq(1);r=g.nav.where(g.nav.gt(0)).pct_change(fill_method=None).where(consecutive)
 m=g.date.map(market.pct_change(fill_method=None));m=m.where(consecutive)
 valid=r.notna()&m.notna();r=r.where(valid);m=m.where(valid)
 cov=r.rolling(126,min_periods=126).cov(m);vm=m.rolling(126,min_periods=126).var();vi=r.rolling(126,min_periods=126).var()
 g['market_beta126']=(cov/vm).where(vm.gt(0));g['residual_vol126']=np.sqrt((vi-cov**2/vm).clip(lower=0)*252).where(vm.gt(0));g['paired_returns126']=valid.rolling(126,min_periods=126).sum();return g

def run():
 out=ROOT/'outputs/r54';out.mkdir(exist_ok=True)
 paths=[CACHE/'forecast_v5/daily_industries.parquet',ROOT/'data/l1_daily.parquet',CACHE/'forecast_v5/CSI_ALL.parquet',ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'data/r30_size_control.parquet',ROOT/'protocols/r54.json',Path(__file__)]
 market=pd.read_parquet(paths[2],columns=['close']).close;assert market.index.is_unique and market.index.is_monotonic_increasing
 monthly=pd.concat([pd.read_parquet(p,columns=KEY+['date','price_ready','members']+F[:-1]) for p in paths[3:5]],ignore_index=True);monthly['log_members']=np.log(monthly.members)
 dates=set(monthly.date);parts=[]
 for p in paths[:2]:
  d=pd.read_parquet(p,columns=KEY+['date','block','nav'])
  for _,g in d.groupby(KEY+['block'],sort=False):
   x=features(g,market);parts.append(x[x.date.isin(dates)][KEY+['date','block','market_beta126','residual_vol126','paired_returns126']])
 f=pd.concat(parts,ignore_index=True);assert not f.duplicated(KEY+['date']).any()
 p=monthly.merge(f,on=KEY+['date'],how='left',validate='one_to_one').merge(pd.read_parquet(paths[5],columns=KEY+['date','size_control']),on=KEY+['date'],how='left',validate='one_to_one')
 p['price_complete']=p.price_ready&p[F].notna().all(axis=1);p['market_controls_complete']=p[['market_beta126','residual_vol126']].notna().all(axis=1);p['joint_complete']=p.price_complete&p.market_controls_complete&p.size_control.notna()
 dest=ROOT/'data/r54_market_controls.parquet';p.to_parquet(dest,index=False)
 summary=p.groupby(['era','level']).agg(rows=('date','size'),price_complete=('price_complete','sum'),size_known=('size_control','count'),market_controls_complete=('market_controls_complete','sum'),joint_complete=('joint_complete','sum')).reset_index();js(out/'coverage.json',summary.to_dict('records'))
 js(out/'receipt.json',dict(reads={str(x):sha(x) for x in paths},feature_sha256=sha(dest),rows=len(p),outcomes_read=False,strict_pit=False))
 print(summary.to_string(index=False))
if __name__=='__main__':run()
