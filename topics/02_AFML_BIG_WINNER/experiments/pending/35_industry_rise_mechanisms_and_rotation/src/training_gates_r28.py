import pandas as pd
from common import *
from train_r02 import F


def run():
 cov=pd.read_parquet(ROOT/'data/r28_common_coverage.parquet');panel=pd.concat([pd.read_parquet(ROOT/'data/monthly_panel.parquet'),pd.read_parquet(ROOT/'data/l1_monthly_panel.parquet')],ignore_index=True);panel['log_members']=np.log(panel.members)
 q=cov.merge(panel[KEY+['date','price_ready','maturity20','maturity60','excess20','excess60']+F],on=KEY+['date'],validate='many_to_one');q=q[q.price_ready].dropna(subset=F)
 rows=[]
 for branch,known,strict in [('common_pair','common_known','common_strict'),('eps_only','eps_known','eps_strict')]:
  for key,v in q.groupby(['variant','era','level','fy_offset']):
   for population,mask in [('strict',v[strict]),('partial_diagnostic',v[known].ge(5)&~v[strict])]:
    g=v[mask];g=g[g.groupby('date').date.transform('size')>=2]
    for h in [20,60]:
     for year in range(2021,2027):
      tr=g[g.date.lt(pd.Timestamp(year,1,1))&g[f'maturity{h}'].lt(pd.Timestamp(year,1,1))&g[f'excess{h}'].notna()];te=g[g.date.dt.year.eq(year)]
      if te.empty:continue
      rows.append(dict(zip(['variant','era','level','fy_offset'],key),branch=branch,population=population,horizon=h,year=year,train_rows=len(tr),train_months=tr.date.nunique(),test_rows=len(te),passes=bool(len(tr)>=300 and tr.date.nunique()>=18)))
 result=pd.DataFrame(rows);result.to_csv(ROOT/'outputs/r28/training_gates.csv',index=False)
 print(result.groupby(['branch','variant','population']).agg(folds=('passes','size'),passes=('passes','sum')).to_string())
if __name__=='__main__':run()
