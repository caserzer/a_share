import pandas as pd
from common import *
BASE=Path('/home/xiaolv/.cache/a_share/ep30_d2/releases/aca398170eea902b76749609bd0b8147b8f644fcf55a6a457b3005d58e3931bf/proxy/financials')
def run():
 out=ROOT/'outputs/r84';out.mkdir(exist_ok=True);fp=ROOT/'data/r24_source_exclusion_overlay.parquet';allf=pd.read_parquet(fp);f=allf[(allf.basis=='profit_cny')&allf.fiscal_year.between(2020,2025)].copy();f=f[f.publication_proxy_date<=pd.to_datetime(f.fiscal_year.astype(str)+'-12-31')]
 rows=[];reads={};missing=[]
 for code,g in f.groupby('stock_code'):
  paths=sorted(BASE.glob(f'{code}.*.parquet'));parts=[]
  for p in paths:
   reads[str(p)]=sha(p);x=pd.read_parquet(p);assert x.SECURITY_CODE.astype(str).eq(str(code)).all() and x.SECUCODE.eq(p.stem).all();x=x.copy();x['source_row']=np.arange(len(x));x['source_path']=str(p);parts.append(x)
  raw=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
  if not paths:missing.append(str(code))
  for year in sorted(g.fiscal_year.unique()):
   q=raw[pd.to_datetime(raw.REPORT_DATE).eq(pd.Timestamp(int(year),12,31))] if len(raw) else raw
   status='no_local_company_partition' if not paths else 'annual_period_absent' if q.empty else 'candidate'
   value=None
   if len(q):
    vals=pd.to_numeric(q.PARENTNETPROFIT,errors='coerce')
    if not (q.REPORT_TYPE.eq('年报')&q.CURRENCY.eq('CNY')).all():status='basis_mismatch'
    elif vals.isna().any() or not np.isfinite(vals).all():status='annual_value_missing'
    elif vals.nunique()!=1:status='annual_value_conflict'
    else:value=float(vals.iloc[0])
   refs=[]
   for x in q.to_dict('records'):refs.append({k:x[k] for k in ['source_path','source_row','SECUCODE','REPORT_DATE','REPORT_TYPE','CURRENCY','PARENTNETPROFIT','NOTICE_DATE','UPDATE_DATE']})
   notices=pd.to_datetime(q.NOTICE_DATE,errors='coerce') if len(q) else pd.Series([],dtype='datetime64[ns]');updates=pd.to_datetime(q.UPDATE_DATE,errors='coerce') if len(q) else pd.Series([],dtype='datetime64[ns]')
   rows.append(dict(stock_code=code,fiscal_year=int(year),status=status,actual_profit_cny=value,source_rows=refs,update_after_notice=bool((updates>notices).any()),notice_missing=bool(notices.isna().any()) if len(q) else None,update_missing=bool(updates.isna().any()) if len(q) else None,partition_count=len(paths)))
 a=pd.DataFrame(rows);joined=f.merge(a.drop(columns=['source_rows']),on=['stock_code','fiscal_year'],validate='many_to_one');joined.to_parquet(out/'forecast_join.parquet',index=False);js(out/'annual_actual_candidates.json',rows)
 summary=dict(eligible_forecast_rows=len(f),finite_forecast_rows=int(np.isfinite(f.value).sum()),company_years=len(a),companies=f.stock_code.nunique(),actual_candidate_company_years=int(a.status.eq('candidate').sum()),status_company_years=a.status.value_counts().to_dict(),status_forecast_rows=joined.status.value_counts().to_dict(),candidate_updated_after_notice=int((a.status.eq('candidate')&a.update_after_notice).sum()),source_partitions=len(reads),strict_PIT=False,realization_evaluation_performed=False)
 js(out/'summary.json',summary)
 for p in [fp,ROOT/'protocols/r84.json',Path(__file__)]:reads[str(p)]=sha(p)
 js(out/'receipt.json',dict(reads=reads,missing_company_codes=missing,source_snapshot=str(BASE),limitation='final vendor-cache actual candidates, not first reported actuals'))
 print(json.dumps(clean(summary),ensure_ascii=False))
if __name__=='__main__':run()
