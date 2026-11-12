import sys,json
from pathlib import Path
import pandas as pd,numpy as np
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import ID,sha
OUT=EP/'restart/p15';OUT.mkdir(exist_ok=True)
root=Path('/home/xiaolv/.cache/a_share/ep30_d2/backfill_v2/normalized');cp=root/'corporate_actions.parquet';rp=root/'rights_issues.parquet';c=pd.read_parquet(cp);rights=pd.read_parquet(rp)
mfile=Path('/home/xiaolv/.cache/a_share/ep32/forecast_v5/CSI_ALL.parquet');cal=pd.DatetimeIndex(pd.read_parquet(mfile).index);pfile=EP/'restart/p11/selected_features.parquet';p=pd.read_parquet(pfile)
afile=Path('/home/xiaolv/.cache/a_share/ep32/extension_v2/products/assignments.parquet');a=pd.read_parquet(afile,columns=['month','era','level','industry_code','instrument','unresolved']);a=a[a.level.eq('L3')].drop_duplicates(['month','era','industry_code','instrument'])
flags=dict(distribution_rows=len(c),rights_rows=len(rights),distribution_exact_duplicate_rows=int(c.duplicated().sum()),rights_exact_duplicate_rows=int(rights.duplicated().sum()),distribution_identity_duplicate_rows=int(c.duplicated(['instrument','report_period','plan_notice_date']).sum()),plan_after_notice=int(c.plan_notice_date.gt(c.notice_date).sum()),notice_after_ex=int(c.notice_date.gt(c.ex_date).sum()),rights_notice_after_ex=int(rights.notice_date.gt(rights.ex_date).sum()),distribution_known_at=int(c.known_at.notna().sum()),rights_known_at=int(rights.known_at.notna().sum()),distribution_status=c.ASSIGN_PROGRESS.value_counts().to_dict())
# Occurrence-only ledger: no cash amounts or final status used as features.
parts=[];annual=[]
for kind,frame,col in [('distribution_plan',c,'plan_notice_date'),('distribution_notice',c,'notice_date'),('rights_notice',rights,'notice_date')]:
 x=frame[['instrument',col]].dropna().rename(columns={col:'source_date'}).drop_duplicates();x['kind']=kind;idx=cal.searchsorted(x.source_date,side='right');x['known_date']=pd.NaT;ok=(idx>0)&(idx<len(cal));x.loc[ok,'known_date']=cal[idx[ok]].to_numpy();x['calendar_status']=np.where(idx==0,'LEFT_CENSORED',np.where(idx>=len(cal),'AFTER_CALENDAR','IN_CALENDAR'));parts.append(x)
 for year,g in x.groupby(x.source_date.dt.year):annual.append(dict(kind=kind,year=int(year),issuer_dates=len(g),issuers=g.instrument.nunique(),in_calendar=int(g.calendar_status.eq('IN_CALENDAR').sum())))
e=pd.concat(parts,ignore_index=True);e.to_parquet(OUT/'occurrence_ledger.parquet',index=False);pd.DataFrame(annual).to_csv(OUT/'occurrence_years.csv',index=False)
lookups={kind:{stock:np.sort(z.known_date.to_numpy(dtype='datetime64[ns]')) for stock,z in g.groupby('instrument')} for kind,g in e[e.calendar_status.eq('IN_CALENDAR')].groupby('kind')}
rows=[]
for date,base in p.groupby('date'):
 cohort=a[a.month.eq(date.to_period('M')-1)].copy();lo=cal[cal.get_loc(date)-20]
 for kind,lookup in lookups.items():
  active={stock:np.searchsorted(v,date.to_datetime64(),side='right')>np.searchsorted(v,lo.to_datetime64(),side='left') for stock,v in lookup.items()};cohort[kind]=cohort.instrument.map(active).eq(True)
 g=cohort.groupby(['era','industry_code']).agg(resolved=('instrument','nunique'),unresolved=('unresolved','max'),**{k:(k,'sum') for k in lookups}).reset_index();g['denominator']=g.resolved+g.unresolved;rows.append(base[ID+['top20','candidate']].merge(g,on=['era','industry_code'],how='left',validate='many_to_one'))
r=pd.concat(rows,ignore_index=True);r.to_parquet(OUT/'coverage.parquet',index=False);summ=[]
for scope,mask in [('all',r.date.notna()),('top20',r.top20),('nonup',r.candidate)]:
 for year,g in r[mask].groupby(r[mask].date.dt.year):
  for kind in lookups:summ.append(dict(scope=scope,year=int(year),kind=kind,industry_weeks=len(g),known_membership=int(g.denominator.notna().sum()),any_event=int(g[kind].ge(1).sum()),three_events=int(g[kind].ge(3).sum()),any_fraction=g[kind].ge(1).mean(),three_fraction=g[kind].ge(3).mean()))
pd.DataFrame(summ).to_csv(OUT/'annual_coverage.csv',index=False);(OUT/'inventory.json').write_text(json.dumps(flags,ensure_ascii=False,indent=2)+'\n');(OUT/'receipt.json').write_text(json.dumps(dict(inputs={str(f):sha(f) for f in [cp,rp,afile,mfile,pfile,Path(__file__),EP/'restart/P15_corporate_action_plan.md']},occurrence_sha256=sha(OUT/'occurrence_ledger.parquet'),coverage_sha256=sha(OUT/'coverage.parquet'),no_outcome_access=True),indent=2)+'\n')
print(json.dumps(flags,ensure_ascii=False));print(pd.DataFrame(summ).query('scope=="top20"').to_string(index=False))
