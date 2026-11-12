import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,sha
OUT=EP/'restart/p14';OUT.mkdir(exist_ok=True)
efile=EP/'restart/financial_events/stock_available_events.parquet';ev=pd.read_parquet(efile);ev=ev[ev.state_accepted&~ev.left_censored].copy();assert (ev.known_date>ev.available_date).all()
afile=Path('/home/xiaolv/.cache/a_share/ep32/extension_v2/products/assignments.parquet');a=pd.read_parquet(afile,columns=['month','era','level','industry_code','instrument','unresolved']);a=a[a.level.eq('L3')].drop_duplicates(['month','era','industry_code','instrument'])
pfile=EP/'restart/p11/selected_features.parquet';p=pd.read_parquet(pfile);mfile=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet');cal=pd.DatetimeIndex(pd.read_parquet(mfile).index)
stocks=a.instrument.unique();lookups={}
for name,part in [('any_proxy',ev),('near_notice',ev[ev.notice_to_available_days.le(7)])]:lookups[name]={stock:np.sort(g.known_date.to_numpy(dtype='datetime64[ns]')) for stock,g in part.groupby('instrument')}
rows=[];receipts=[]
for date,base in p.groupby('date'):
 cohort=a[a.month.eq(date.to_period('M')-1)].copy();assert not cohort.duplicated(['era','industry_code','instrument']).any();i=cal.get_loc(date);lo=cal[max(0,i-20)]
 for name,lookup in lookups.items():
  active={stock:bool(len(v) and np.searchsorted(v,date.to_datetime64(),side='right')>np.searchsorted(v,lo.to_datetime64(),side='left')) for stock,v in lookup.items()};cohort[name]=cohort.instrument.map(active).fillna(False).astype(bool)
 c=cohort.groupby(['era','industry_code']).agg(resolved_members=('instrument','nunique'),unresolved=('unresolved','max'),any_proxy=('any_proxy','sum'),near_notice=('near_notice','sum')).reset_index();c['denominator']=c.resolved_members+c.unresolved
 z=base[ID+['top20','candidate']].merge(c,on=['era','industry_code'],how='left',validate='many_to_one');rows.append(z);receipts.append(dict(date=date,cohort_month=str(date.to_period('M')-1),window_begin=lo,window_end=date,cohort_rows=len(cohort)))
r=pd.concat(rows,ignore_index=True);r.to_parquet(OUT/'industry_week_coverage.parquet',index=False);pd.DataFrame(receipts).to_csv(OUT/'cohort_windows.csv',index=False)
summary=[]
for scope,mask in [('all',r.date.notna()),('price_top20',r.top20),('nonup_candidate',r.candidate)]:
 for year,g in r[mask].groupby(r[mask].date.dt.year):
  for kind in ['any_proxy','near_notice']:
   summary.append(dict(scope=scope,year=int(year),timing=kind,industry_weeks=len(g),known_membership=int(g.denominator.notna().sum()),any_event=int(g[kind].ge(1).sum()),three_events=int(g[kind].ge(3).sum()),three_and_30pct=int((g[kind].ge(3)&g[kind].div(g.denominator).ge(.3)).sum()),any_fraction=g[kind].ge(1).mean(),coverage30_fraction=(g[kind].ge(3)&g[kind].div(g.denominator).ge(.3)).mean(),industries_with_event=g.loc[g[kind].ge(1),['era','industry_code']].drop_duplicates().shape[0]))
pd.DataFrame(summary).to_csv(OUT/'annual_coverage.csv',index=False)
ev.assign(year=ev.known_date.dt.year,near_notice=ev.notice_to_available_days.le(7)).groupby('year').agg(events=('instrument','size'),stocks=('instrument','nunique'),near_notice=('near_notice','sum'),median_notice_delay=('notice_to_available_days','median')).to_csv(OUT/'event_years.csv')
(OUT/'receipt.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [efile,afile,pfile,mfile,Path(__file__),EP/'restart/P14_event_inventory_plan.md']},output_sha256=sha(OUT/'industry_week_coverage.parquet'),no_outcome_access=True,accepted_events=len(ev)),indent=2)+'\n')
print(pd.DataFrame(summary).query('scope=="price_top20"').to_string(index=False))
