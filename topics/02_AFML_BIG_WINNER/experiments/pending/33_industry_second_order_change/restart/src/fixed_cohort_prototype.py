import sys,json
from pathlib import Path
import numpy as np,pandas as pd
EP=Path(__file__).resolve().parents[2];sys.path.insert(0,str(EP/'src'))
from pool_evaluation import sha
OUT=EP/'restart/p23';OUT.mkdir(exist_ok=True);assert not (OUT/'receipt.json').exists()
prior=EP/'restart/p22';checks=pd.read_parquet(prior/'selected_checks.parquet');rec=json.loads((prior/'receipt.json').read_text());identityfile=EP.parent/'32_industry_rotation_cycle_observation/extensions/v4_adaptive_6_18_months/outputs/audits/inputs.json';identity=json.loads(identityfile.read_text());release=Path(identity['price_release']);assign=Path('/home/xiaolv/.cache/a_share/ep32/extension_v2/products/assignments.parquet');j=pd.read_parquet(assign);j=j[j.level.eq('L3')];cal=pd.DatetimeIndex(pd.read_parquet(release/'inputs/inputs/baseline/normalized/calendar.parquet').date).sort_values();cache={};hashes={}
def price(sid):
 if sid not in cache:
  rel='normalized/prices_qfq/'+sid+'.parquet';p=release/rel;h=sha(p);assert h==identity['daily_read_files'][rel];hashes[str(p)]=h
  cache[sid]=pd.read_parquet(p).reindex(columns=['date','qfq_close','close_conflict','factor_chain_id','vendor_trade_status','execution_reason']).set_index('date')
 return cache[sid]
def valid(b):return b.qfq_close.gt(0)&b.close_conflict.eq(False)&b.factor_chain_id.notna()
reasons=[];outputs=[];summaries=[];prefix_checks=0
checks['month']=checks.date.dt.to_period('M')
for (era,code,month),group in checks.groupby(['era','industry_code','month']):
 cohort=j[j.era.eq(era)&j.industry_code.eq(code)&j.month.eq(month-1)];anchor=cal[cal.to_period('M')==month-1].max();days=cal[cal.to_period('M')==month];ix=pd.DatetimeIndex([anchor]).append(days);arrays=[];oks=[];instruments=[]
 for _,member in cohort.iterrows():
  b=price(member.security_id).reindex(ix);ok=valid(b)&b.factor_chain_id.eq(b.factor_chain_id.iloc[0]);ratios=(b.qfq_close/b.qfq_close.iloc[0]).where(ok);arrays.append(ratios.to_numpy());oks.append(bool(valid(b).iloc[0]));instruments.append(member.instrument)
  for _,case in group.iterrows():
   for date in [case.previous_date,case.date]:
    row=b.loc[date]
    if bool(ok.loc[date]):continue
    if date not in cache[member.security_id].index:reason='NO_ROW'
    elif pd.notna(row.close_conflict) and bool(row.close_conflict):reason='CLOSE_CONFLICT'
    elif pd.isna(row.qfq_close) or row.qfq_close<=0:reason='NO_VALID_ADJUSTED_PRICE'
    elif pd.isna(row.factor_chain_id):reason='NO_FACTOR_CHAIN'
    elif not bool(valid(b).iloc[0]):reason='INVALID_ANCHOR'
    else:reason='CHAIN_DIFFERS_FROM_ANCHOR'
    reasons.append(dict(era=era,industry_code=code,sample_date=case.date,date=date,instrument=member.instrument,reason=reason,vendor_trade_status=row.vendor_trade_status,execution_reason=row.execution_reason))
 arr=np.asarray(arrays).T;held=np.asarray(oks);den=len(cohort)+int(cohort.unresolved.max());anchor_coverage=held.sum()/den;eligible=len(cohort)>=5 and anchor_coverage>=.8
 fixed=np.mean(arr[:,held],axis=1) if held.any() else np.full(len(ix),np.nan)
 if not eligible:fixed[:]=np.nan
 count=np.isfinite(arr).sum(axis=1);old=np.divide(np.nansum(arr,axis=1),count,out=np.full(len(ix),np.nan),where=count>0);old[(count/den<.8)|(len(cohort)<5)]=np.nan
 # Prefix-only calculation cannot alter membership or prior NAV.
 for k in range(1,len(ix)+1):
  prefix=arr[:k];h=np.isfinite(prefix[0]);assert np.array_equal(h,held)
  value=np.mean(prefix[-1,h]) if eligible and h.any() else np.nan;assert np.isclose(value,fixed[k-1],equal_nan=True);prefix_checks+=1
 complete=bool(np.isfinite(arr[1:]).all());
 if complete and eligible:assert np.allclose(fixed[1:],old[1:])
 if eligible:assert np.array_equal(np.isnan(fixed),~np.isfinite(arr[:,held]).all(axis=1))
 for k,date in enumerate(ix[1:],start=1):outputs.append(dict(era=era,industry_code=code,date=date,anchor=anchor,held_members=int(held.sum()),anchor_coverage=anchor_coverage,old_relative_nav=old[k],fixed_relative_nav=fixed[k],unknown_held=int(np.sum(~np.isfinite(arr[k,held])))))
 summaries.append(dict(era=era,industry_code=code,month=str(month),days=len(days),members=len(cohort),held_members=int(held.sum()),anchor_coverage=anchor_coverage,anchor_eligible=eligible,old_known=int(np.isfinite(old[1:]).sum()),fixed_known=int(np.isfinite(fixed[1:]).sum()),complete_month=complete))
a=pd.DataFrame(outputs);a.to_parquet(OUT/'monthly_prototype.parquet',index=False);pd.DataFrame(reasons).drop_duplicates().to_csv(OUT/'missing_reasons.csv',index=False);s=pd.DataFrame(summaries);s.to_csv(OUT/'month_support.csv',index=False)
(OUT/'receipt.json').write_text(json.dumps(dict(status='PASS',inputs={str(p):sha(p) for p in [prior/'selected_checks.parquet',identityfile,assign,Path(__file__),EP/'restart/P23_fixed_cohort_plan.md']},price_reads=hashes,months=len(s),prefix_checks=prefix_checks,complete_months=int(s.complete_month.sum()),no_outcomes_read=True),indent=2)+'\n')
print(pd.DataFrame(reasons).drop_duplicates().groupby('reason').size().to_string());print(s[['days','old_known','fixed_known','complete_month']].sum().to_string());print(a[a.industry_code.eq('857652.SI')&a.date.eq('2023-04-27')].to_string(index=False))
