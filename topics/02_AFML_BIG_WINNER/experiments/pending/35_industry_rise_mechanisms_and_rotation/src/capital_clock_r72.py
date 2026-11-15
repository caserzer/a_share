import pandas as pd
from common import *
FIELDS={'cashflow_vip':['c_pay_acq_const_fiolta','n_cashflow_act'],'income_vip':['n_income_attr_p']}
def select(raw,date):
 g=raw[raw.timing_valid & raw.proxy_available_date.le(date) & raw.api.isin(FIELDS)].copy();keys=['api','ts_code','end_date'];g=g[g.proxy_available_date.eq(g.groupby(keys).proxy_available_date.transform('max'))];parts=[]
 for api,fields in FIELDS.items():
  q=g[g.api.eq(api)]
  for field in fields:
   a=q.groupby(['ts_code','end_date']).agg(value=(field,'first'),distinct=(field,lambda x:x.nunique(dropna=False)),available_at=('proxy_available_date','max'))
   types=q.assign(type_ok=q.report_type.eq('1')&q.comp_type.eq('1')).groupby(['ts_code','end_date']).type_ok.all()
   a['status']='available';a.loc[a.value.isna(),'status']='missing';a.loc[a.distinct.gt(1),'status']='conflict'
   if api=='income_vip':a.loc[a.status.eq('available')&~types,'status']='incompatible_statement_type'
   if field=='c_pay_acq_const_fiolta':a.loc[a.status.eq('available')&a.value.lt(0),'status']='invalid_sign'
   a.loc[~a.status.eq('available'),'value']=np.nan;a['field']=field;a['asof']=date;parts.append(a.reset_index())
 return pd.concat(parts,ignore_index=True)
def run():
 out=ROOT/'outputs/r72';out.mkdir(exist_ok=True);source=ROOT/'data/financial_archive_all_market.parquet';raw=pd.read_parquet(source);protocol=json.loads((ROOT/'protocols/r72.json').read_text());selected=[];pairs=[];archive=[]
 for date in map(pd.Timestamp,protocol['dates']):
  f=select(raw,date);selected.append(f);v=f.pivot(index=['ts_code','end_date'],columns='field',values='value');v=v.reindex(columns=sum(FIELDS.values(),[]));v['all_known']=v.notna().all(axis=1);v=v.reset_index();v=v[v.ts_code.str.fullmatch(r'[0-9]{6}\.(SH|SZ|BJ)')]
  current=v[v.end_date.dt.year.eq(2026)].copy();prior=v[v.end_date.dt.year.eq(2025)].copy();prior['end_date']=prior.end_date+pd.DateOffset(years=1);q=current.merge(prior,on=['ts_code','end_date'],how='outer',suffixes=('_current','_prior'),validate='one_to_one');q['asof']=date;q['joint_known']=q.all_known_current.eq(True)&q.all_known_prior.eq(True);pairs.append(q)
  cutoff=date.tz_localize('Asia/Shanghai')+pd.Timedelta(days=1);archive.append(dict(asof=date,archived_rows_before_snapshot=int((raw.archived_available_at<cutoff).sum())))
 s=pd.concat(selected,ignore_index=True);p=pd.concat(pairs,ignore_index=True);s.to_parquet(out/'selected_fields.parquet',index=False);p.to_parquet(out/'company_pairs.parquet',index=False);js(out/'archive_clock.json',archive)
 end=p[p['asof'].eq(pd.Timestamp(protocol['dates'][-1]))&p.joint_known];rows=[];cols=[f'{field}_{period}' for field in sum(FIELDS.values(),[]) for period in ['current','prior']]
 for date in map(pd.Timestamp,protocol['dates']):
  now=p[p['asof'].eq(date)];m=end.merge(now,on=['ts_code','end_date'],how='left',suffixes=('_september','_then'),validate='one_to_one')
  for period,g in m.groupby('end_date'):
   known=g.joint_known_then.eq(True);changed=(g[[c+'_september' for c in cols]].to_numpy()!=g[[c+'_then' for c in cols]].to_numpy()).any(axis=1)&known.to_numpy()
   rows.append(dict(asof=date,period=period,september_joint_known=len(g),known_then=int(known.sum()),not_joint_known_then=int((~known).sum()),known_but_value_changed=int(changed.sum()),all_source_joint_known=int((now.end_date.eq(period)&now.joint_known).sum())))
 js(out/'coverage.json',rows);js(out/'receipt.json',dict(reads={str(x):sha(x) for x in [source,ROOT/'protocols/r72.json',Path(__file__)]},selected_fields=len(s),pair_rows=len(p),strict_pit=False));print(pd.DataFrame(rows).to_string(index=False))
if __name__=='__main__':run()
