"""Single financing intensity proxy, no labels read."""
import pandas as pd
from common import *
from margin_inventory_r44 import SOURCE
from train_r02 import F

def inputs():
 detail=pd.read_parquet(SOURCE/'normalized_detail.parquet',columns=['date','snapshot_date','instrument','financing'])
 cols=['month']+KEY+['security_id','instrument'];members=pd.concat([pd.read_parquet(CACHE/'extension_v2/products/assignments.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_assignments.parquet',columns=cols)])
 stock=pd.read_parquet(CACHE/'extension_v2/products/panel.parquet',columns=['date','security_id','raw_close','total_shares','share_effective_date','listed'])
 assert not stock.duplicated(['date','security_id']).any()
 valid=stock.listed&stock.raw_close.gt(0)&stock.total_shares.gt(0)&stock.share_effective_date.le(stock.date)
 stock['denominator_cap']=(stock.raw_close*stock.total_shares).where(valid);stock.loc[~np.isfinite(stock.denominator_cap),'denominator_cap']=np.nan
 return detail,members,stock[['date','security_id','denominator_cap']]

def run():
 out=ROOT/'outputs/r45';out.mkdir(exist_ok=True);d,m,s=inputs()
 cols=KEY+['date','price_ready','members']+F[:-1]
 panel=pd.concat([pd.read_parquet(ROOT/'data/monthly_panel.parquet',columns=cols),pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet',columns=cols)],ignore_index=True);panel['log_members']=np.log(panel.members)
 signals=panel[panel.date.isin(d.date.unique())][KEY+['date']].copy();signals['month']=signals.date.dt.to_period('M')-1
 z=signals.merge(m,on=KEY+['month'],how='left',validate='one_to_many').merge(d,on=['date','instrument'],how='left',validate='many_to_one').merge(s,on=['date','security_id'],how='left',validate='many_to_one')
 z['company_ratio']=z.financing/z.denominator_cap;z.loc[~np.isfinite(z.company_ratio),'company_ratio']=np.nan
 q=z.groupby(KEY+['date']).agg(members=('security_id','count'),margin_known=('financing','count'),cap_known=('denominator_cap','count'),ratio_known=('company_ratio','count'),raw_median=('company_ratio','median'),snapshot_date=('snapshot_date','max')).reset_index()
 q['coverage']=q.ratio_known/q.members;q['ready']=q.ratio_known.ge(5)&q.coverage.ge(.8);q['financing_intensity']=q.raw_median.where(q.ready)
 q.to_parquet(ROOT/'data/r45_financing_intensity.parquet',index=False)
 base=panel.merge(q[KEY+['date','financing_intensity']],on=KEY+['date'],how='left',validate='one_to_one').merge(pd.read_parquet(ROOT/'data/r30_size_control.parquet',columns=KEY+['date','size_control']),on=KEY+['date'],how='left',validate='one_to_one')
 base['matched']=base.price_ready&base[F+['size_control','financing_intensity']].notna().all(axis=1)
 summary=base.groupby(['era','level']).agg(all_dates=('date','size'),factor_known=('financing_intensity','count'),matched=('matched','sum')).reset_index();js(out/'coverage_summary.json',summary.to_dict('records'))
 js(out/'annual_coverage.json',base.groupby(['era','level',base.date.dt.year]).agg(rows=('date','size'),matched=('matched','sum')).reset_index().rename(columns={'date':'year'}).to_dict('records'))
 paths=[SOURCE/'normalized_detail.parquet',CACHE/'extension_v2/products/assignments.parquet',CACHE/'extension_v2/products/panel.parquet',ROOT/'data/l1_assignments.parquet',ROOT/'data/monthly_panel.parquet',ROOT/'data/l1_monthly_panel.parquet',ROOT/'data/r30_size_control.parquet',ROOT/'protocols/r45.json',Path(__file__)]
 js(out/'receipt.json',dict(inputs={str(p):sha(p) for p in paths},industry_dates=len(q),factor_known=int(q.ready.sum()),matched=int(base.matched.sum()),company_rows=len(z),known_company_ratios=int(z.company_ratio.notna().sum()),missing_cap_with_financing=int((z.financing.notna()&z.denominator_cap.isna()).sum()),feature_sha256=sha(ROOT/'data/r45_financing_intensity.parquet'),outcomes_read=False,quality='Historical-proxy; financing revision history and share publication times unknown'))
 print(summary.to_string(index=False))

if __name__=='__main__':run()
