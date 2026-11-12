import sys
from pathlib import Path
import pandas as pd
p=Path('/home/xiaolv/code/a_share/topics/02_AFML_BIG_WINNER/experiments/pending/33_industry_second_order_change/restart/src')
sys.path.insert(0,str(p))
from financial_events import construct
cal=pd.bdate_range('2015-01-01','2022-01-01')
q=pd.period_range('2015Q1','2020Q4',freq='Q')
f=pd.DataFrame({'REPORT_DATE':q.end_time.normalize(),'NOTICE_DATE':q.end_time.normalize()+pd.Timedelta(days=30),'UPDATE_DATE':q.end_time.normalize()+pd.Timedelta(days=30),'TOTALOPERATEREVE':[100*x.quarter*(1+.05*(x.year-2015)) for x in q]})
a,_=construct(f,cal);target=a[a.period.eq('2020Q4')].iloc[0];assert target.kind=='NOTICE_ALIGNED_PROXY'
f.loc[f.REPORT_DATE.eq(pd.Timestamp('2019-09-30')),'UPDATE_DATE']=pd.Timestamp('2021-06-01')
b,_=construct(f,cal);target=b[b.period.eq('2020Q4')].iloc[0];assert target.kind=='DEPENDENCY_DELAYED' and target.known_date==pd.Timestamp('2021-06-02')
f.loc[f.REPORT_DATE.eq(pd.Timestamp('2019-09-30')),'UPDATE_DATE']=pd.NaT
c,_=construct(f,cal);assert c[c.period.eq('2020Q4')].iloc[0].status=='MISSING_AVAILABILITY'
print('PASS: aligned notice, delayed historical dependency and missing availability.')
