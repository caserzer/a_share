import pandas as pd
from common import *
def run():
 out=ROOT/'outputs/r85';out.mkdir(exist_ok=True);fp=ROOT/'data/r24_source_exclusion_overlay.parquet';ap=ROOT/'outputs/r84/annual_actual_candidates.json';jp=ROOT/'outputs/r84/forecast_join.parquet';values=pd.read_parquet(fp)
 ep=ROOT.parent/'24_conditional_return_distribution_exploration/outputs/r19_eps_expectations';xp=ep/'validated_extractions.parquet';mp=ep/'selected_reports.parquet';receipt=json.loads((ROOT/'outputs/r11/receipt.json').read_text());assert sha(xp)==receipt['source_extraction_sha256'] and sha(mp)==receipt['source_metadata_sha256']
 reports=pd.read_parquet(xp,columns=['infoCode','stockCode','publishDate','available_date']).merge(pd.read_parquet(mp,columns=['infoCode','orgCode']),on='infoCode',validate='one_to_one').rename(columns={'stockCode':'stock_code','orgCode':'broker'});reports['publication_proxy_date']=pd.concat([pd.to_datetime(reports.publishDate),pd.to_datetime(reports.available_date)],axis=1).max(axis=1)
 reports=reports[['infoCode','stock_code','broker','publication_proxy_date']];reports.to_parquet(out/'report_roster.parquet',index=False)
 forecasts=values[values.basis.eq('profit_cny')].set_index(['infoCode','fiscal_year']);assert forecasts.index.is_unique
 roster={(a,b):g for (a,b),g in reports.groupby(['stock_code','broker'])};prior=pd.read_parquet(jp);brokers=[]
 for (code,year,broker),g in prior.dropna(subset=['broker']).groupby(['stock_code','fiscal_year','broker']):
  cutoff=pd.Timestamp(int(year),12,31);q=roster.get((code,broker),pd.DataFrame(columns=reports.columns));q=q[q.publication_proxy_date<cutoff];status='no_report_before_cutoff';ids=[];last=None;age=None;forecast=None
  if len(q):
   last=q.publication_proxy_date.max();age=(cutoff-last).days;latest=q[q.publication_proxy_date.eq(last)];ids=sorted(latest.infoCode);vv=[float(forecasts.loc[(info,int(year)),'value']) if (info,int(year)) in forecasts.index else np.nan for info in ids]
   if age>180:status='stale'
   elif not all(np.isfinite(vv)):status='latest_report_unknown'
   elif len(set(vv))!=1:status='same_day_conflict'
   else:status='valid';forecast=vv[0]
  brokers.append(dict(stock_code=code,fiscal_year=int(year),broker=broker,cutoff=cutoff,latest_publication=last,age_days=age,latest_report_ids=ids,status=status,forecast_profit_cny=forecast))
 js(out/'broker_snapshots.json',brokers);b=pd.DataFrame(brokers);actual=json.loads(ap.read_text());companies=[]
 for a in actual:
  g=b[b.stock_code.eq(a['stock_code'])&b.fiscal_year.eq(a['fiscal_year'])];good=g[g.status.eq('valid')];prediction=float(good.forecast_profit_cny.median()) if len(good) else None;real=a['actual_profit_cny'];den=abs(prediction)+abs(real) if prediction is not None and real is not None else None;err=(prediction-real)/den if den is not None and den>0 else None
  companies.append(dict(stock_code=a['stock_code'],fiscal_year=a['fiscal_year'],brokers=len(g),known_brokers=len(good),broker_coverage=len(good)/len(g) if len(g) else None,all_brokers_known=bool(len(g)>0 and len(g)==len(good)),forecast_profit_cny=prediction,actual_profit_cny=real,error=err,absolute_error=abs(err) if err is not None else None,overestimated=prediction>real if err is not None else None,sign_mismatch=bool(np.sign(prediction)!=np.sign(real)) if err is not None else None,actual_updated_after_notice=a['update_after_notice']))
 js(out/'company_years.json',companies);c=pd.DataFrame(companies);summary=[]
 for year,g in c.groupby('fiscal_year'):
  groups={'all':g,'all_brokers_known':g[g.all_brokers_known],'partial_brokers':g[~g.all_brokers_known],'actual_updated':g[g.actual_updated_after_notice],'actual_not_later_updated':g[~g.actual_updated_after_notice]}
  for label,q in groups.items():
   valid=q[q.error.notna()];summary.append(dict(fiscal_year=int(year),stratum=label,company_years=len(q),evaluable=len(valid),mean_symmetric_error=float(valid.error.mean()) if len(valid) else None,median_symmetric_error=float(valid.error.median()) if len(valid) else None,mean_absolute_symmetric_error=float(valid.absolute_error.mean()) if len(valid) else None,overestimated_share=float(valid.overestimated.mean()) if len(valid) else None,sign_mismatch_share=float(valid.sign_mismatch.mean()) if len(valid) else None))
 js(out/'summary.json',summary);js(out/'coverage.json',dict(broker_snapshots=len(b),broker_status_counts=b.status.value_counts().to_dict(),company_years=len(c),evaluable=int(c.error.notna().sum()),all_brokers_known=int(c.all_brokers_known.sum()),no_known_brokers=int(c.known_brokers.eq(0).sum())))
 inputs=[fp,ap,jp,xp,mp,ROOT/'outputs/r11/receipt.json',ROOT/'protocols/r85.json',Path(__file__)];js(out/'receipt.json',dict(reads={str(p):sha(p) for p in inputs},strict_PIT=False,selection_does_not_use_actual_values=True));print((out/'coverage.json').read_text());print(json.dumps([x for x in summary if x['stratum']=='all'],ensure_ascii=False))
if __name__=='__main__':run()
